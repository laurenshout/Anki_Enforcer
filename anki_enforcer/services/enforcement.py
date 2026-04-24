from __future__ import annotations

import logging
import time
from typing import Any

from aqt.qt import QApplication, QEvent, QObject, QTimer, Qt, QWidget

from ..config import ConfigStore
from ..ui.popup import PopupManager
from .fallback import FallbackController
from .progress import ProgressTracker

logger = logging.getLogger(__name__)


class _MainWindowEventFilter(QObject):
    def __init__(self, parent: Any, controller: "FocusEnforcer") -> None:
        super().__init__(parent)
        self._controller = controller

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        return self._controller.handle_event(obj, event)


class FocusEnforcer:
    def __init__(
        self,
        mw: Any,
        config_store: ConfigStore,
        fallback: FallbackController,
        popup: PopupManager,
        progress: ProgressTracker,
    ) -> None:
        self.mw = mw
        self.config_store = config_store
        self.fallback = fallback
        self.popup = popup
        self.progress = progress
        self._event_filter = _MainWindowEventFilter(mw, self)
        self._installed = False
        self._last_popup_time = 0.0
        self._cooldown_seconds = 1.5
        self._focus_loss_confirmation_delay_ms = 200
        self._last_focus_loss_check_time = 0.0
        self._suppress_focus_loss_until = 0.0
        self._enforce_full_size_pending = False
        self._focus_reclaim_pending = False
        self._focus_reclaim_interval_ms = 150
        self._window_topmost_enabled = False
        self._forced_full_screen_active = False

    def install(self) -> None:
        if self._installed:
            return
        self.mw.installEventFilter(self._event_filter)
        self._installed = True
        logger.info("Focus enforcer event filter installed.")
        QTimer.singleShot(0, self._ensure_full_size_if_incomplete)

    def handle_event(self, _obj: QObject, event: QEvent) -> bool:
        config = self.config_store.load()
        if not config.get("enabled", False) or self.fallback.is_active():
            self._release_window_lock()
            return False

        status = self.progress.get_status(self.mw, config)
        if status.complete:
            self._release_window_lock()
        else:
            self._apply_window_lock(status)

        event_type = event.type()

        if event_type == QEvent.Type.Close:
            if not status.complete:
                logger.info("Blocked close attempt: %s", status.reason)
                event.ignore()
                self._show_popup("You cannot close Anki until the required decks are complete.")
                return True
            return False

        if event_type == QEvent.Type.WindowStateChange:
            return self._handle_window_state_change(event, status)

        if event_type == QEvent.Type.Resize:
            self._handle_move_or_resize(status, "resize")
            return False

        move_event = getattr(QEvent.Type, "Move", None)
        if move_event is not None and event_type == move_event:
            self._handle_move_or_resize(status, "move")
            return False

        if event_type == QEvent.Type.WindowDeactivate:
            self._schedule_focus_loss_check()
            return False

        return False

    def _handle_window_state_change(self, event: QEvent, status: Any) -> bool:
        if status.complete:
            return False

        if self._is_new_minimize_state(event):
            logger.info("Blocked minimize attempt while incomplete: %s", status.reason)
            if hasattr(event, "ignore"):
                event.ignore()
            self._show_popup("No minimizing. Finish the required decks first.")
            self._enforce_full_size_window()
            return True

        if self._should_force_full_size():
            logger.info("Restoring locked full-size window while incomplete: %s", status.reason)
            if hasattr(event, "ignore"):
                event.ignore()
            self._show_popup("Anki stays full screen until the required decks are complete.")
            self._enforce_full_size_window()
            return True

        return False

    def _is_new_minimize_state(self, event: QEvent) -> bool:
        if not (self.mw.windowState() & Qt.WindowState.WindowMinimized):
            return False

        old_state_method = getattr(event, "oldState", None)
        if callable(old_state_method):
            try:
                return not bool(old_state_method() & Qt.WindowState.WindowMinimized)
            except Exception:
                return True
        return True

    def _handle_move_or_resize(self, status: Any, action: str) -> None:
        if not self._should_force_full_size():
            return

        if status.complete:
            return

        logger.info("Restoring locked full-size window after %s while incomplete: %s", action, status.reason)
        self._enforce_full_size_window()

    def _should_force_full_size(self) -> bool:
        if self._enforce_full_size_pending:
            return False
        if self._is_window_minimized():
            return False
        return not self._is_window_locked_full_size()

    def _is_window_minimized(self) -> bool:
        return bool(self.mw.windowState() & Qt.WindowState.WindowMinimized)

    def _supports_full_screen(self) -> bool:
        return callable(getattr(self.mw, "showFullScreen", None))

    def _is_window_full_size(self) -> bool:
        try:
            if callable(getattr(self.mw, "isFullScreen", None)) and self.mw.isFullScreen():
                return True
        except Exception:
            pass

        try:
            if callable(getattr(self.mw, "isMaximized", None)) and self.mw.isMaximized():
                return True
        except Exception:
            pass

        full_size_state = getattr(Qt.WindowState, "WindowMaximized", 0) | getattr(
            Qt.WindowState, "WindowFullScreen", 0
        )
        return bool(self.mw.windowState() & full_size_state)

    def _is_window_locked_full_size(self) -> bool:
        if self._supports_full_screen():
            try:
                if callable(getattr(self.mw, "isFullScreen", None)) and self.mw.isFullScreen():
                    return True
            except Exception:
                pass
            return bool(self.mw.windowState() & getattr(Qt.WindowState, "WindowFullScreen", 0))
        return self._is_window_full_size()

    def _apply_window_lock(self, status: Any) -> None:
        self._set_window_topmost(True)
        if self._should_force_full_size():
            logger.info("Applying locked full-size mode while incomplete: %s", status.reason)
            self._enforce_full_size_window()

    def _ensure_full_size_if_incomplete(self) -> None:
        config = self.config_store.load()
        if not config.get("enabled", False) or self.fallback.is_active():
            self._release_window_lock()
            return

        status = self.progress.get_status(self.mw, config)
        if status.complete:
            self._release_window_lock()
            return

        self._apply_window_lock(status)

    def _enforce_full_size_window(self) -> None:
        if self._enforce_full_size_pending:
            return

        self._enforce_full_size_pending = True
        self._suppress_focus_loss_until = time.monotonic() + 1.0

        def _restore() -> None:
            self._enforce_full_size_pending = False
            window_state = self.mw.windowState() & ~Qt.WindowState.WindowMinimized
            if self._supports_full_screen():
                self._forced_full_screen_active = True
                window_state &= ~getattr(Qt.WindowState, "WindowMaximized", 0)
                full_screen_state = getattr(Qt.WindowState, "WindowFullScreen", 0)
                self.mw.setWindowState(window_state | full_screen_state)
                show_full_screen = getattr(self.mw, "showFullScreen", None)
                if callable(show_full_screen):
                    show_full_screen()
            else:
                full_size_state = getattr(Qt.WindowState, "WindowMaximized", 0)
                self.mw.setWindowState(window_state | full_size_state)
                show_maximized = getattr(self.mw, "showMaximized", None)
                if callable(show_maximized):
                    show_maximized()
            self.mw.raise_()
            self.mw.activateWindow()

        QTimer.singleShot(0, _restore)

    def _set_window_topmost(self, enabled: bool) -> None:
        if self._window_topmost_enabled == enabled:
            return

        set_window_flag = getattr(self.mw, "setWindowFlag", None)
        if callable(set_window_flag):
            try:
                set_window_flag(Qt.WindowType.WindowStaysOnTopHint, enabled)
            except TypeError:
                if enabled:
                    set_window_flag(Qt.WindowType.WindowStaysOnTopHint)
        show = getattr(self.mw, "show", None)
        if callable(show):
            show()
        self._window_topmost_enabled = enabled

    def _release_window_lock(self) -> None:
        self._set_window_topmost(False)

        if not self._forced_full_screen_active:
            return

        self._forced_full_screen_active = False
        show_maximized = getattr(self.mw, "showMaximized", None)
        if callable(show_maximized):
            show_maximized()

    def _schedule_focus_loss_check(self) -> None:
        self._last_focus_loss_check_time = time.monotonic()
        QTimer.singleShot(self._focus_loss_confirmation_delay_ms, self._handle_focus_loss)

    def _handle_focus_loss(self) -> None:
        elapsed = time.monotonic() - self._last_focus_loss_check_time
        if elapsed < (self._focus_loss_confirmation_delay_ms / 1000.0) * 0.75:
            logger.debug("Ignoring stale focus loss callback.")
            return

        config = self.config_store.load()
        if not config.get("enabled", False) or self.fallback.is_active():
            return

        if time.monotonic() < self._suppress_focus_loss_until:
            logger.debug("Suppressing focus loss popup caused by blocked minimize restoration.")
            return

        if self._should_ignore_focus_loss():
            logger.debug("Ignored focus loss caused by internal Anki UI activity.")
            return

        status = self.progress.get_status(self.mw, config)
        if status.complete:
            self._release_window_lock()
            return

        self._apply_window_lock(status)

        if not self._popup_allowed():
            logger.debug("Focus loss detected while incomplete; reclaiming focus without popup.")
            self._reclaim_focus(config)
            return

        logger.info("Focus loss detected while incomplete: %s", status.reason)
        self._show_popup("Stay focused. Required decks are not complete yet.")
        self._reclaim_focus(config)

    def _should_ignore_focus_loss(self) -> bool:
        app = QApplication.instance()
        if app is None:
            return False

        try:
            if app.applicationState() == Qt.ApplicationState.ApplicationActive:
                return True
        except Exception:
            pass

        active_window = app.activeWindow()
        if self._is_main_window_family(active_window):
            return True

        modal_widget = app.activeModalWidget()
        if self._is_main_window_family(modal_widget):
            return True

        popup_widget = app.activePopupWidget()
        if self._is_main_window_family(popup_widget):
            return True

        return False

    def _is_main_window_family(self, widget: QWidget | None) -> bool:
        current = widget
        while current is not None:
            if current is self.mw:
                return True
            current = current.parentWidget()
        return False

    def _reclaim_focus(self, config: dict[str, Any]) -> None:
        if self._focus_reclaim_pending:
            return

        self._focus_reclaim_pending = True
        attempts = 2 if config.get("focus_loss_behavior") == "warn_only" else 4

        def _attempt(remaining: int) -> None:
            self._set_window_topmost(True)
            self._enforce_full_size_window()
            self.mw.raise_()
            self.mw.activateWindow()

            if remaining <= 1:
                self._focus_reclaim_pending = False
                return

            QTimer.singleShot(self._focus_reclaim_interval_ms, lambda: _attempt(remaining - 1))

        QTimer.singleShot(0, lambda: _attempt(attempts))

    def _show_popup(self, reason: str) -> None:
        if not self._popup_allowed():
            return
        self._last_popup_time = time.monotonic()
        config = self.config_store.load()
        self.popup.show_warning(self.mw, config, reason)

    def _popup_allowed(self) -> bool:
        now = time.monotonic()
        return (now - self._last_popup_time) >= self._cooldown_seconds
