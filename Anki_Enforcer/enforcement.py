from __future__ import annotations

import logging
import os
import time
from typing import Any

from aqt.qt import QApplication, QEvent, QObject, QTimer, Qt, QWidget

from .config import ConfigStore
from .fallback import FallbackController
from .popup import PopupManager
from .progress_tracker import ProgressTracker

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
        self._addon_dir = os.path.dirname(__file__)

    def install(self) -> None:
        if self._installed:
            return
        self.mw.installEventFilter(self._event_filter)
        self._installed = True
        logger.info("Focus enforcer event filter installed.")

    def handle_event(self, _obj: QObject, event: QEvent) -> bool:
        if self._can_ignore_enforcement():
            return False

        event_type = event.type()

        if event_type == QEvent.Type.Close:
            config = self.config_store.load()
            status = self.progress.get_status(self.mw, config)
            if not status.complete:
                logger.info("Blocked close attempt: %s", status.reason)
                event.ignore()
                self._show_popup("You cannot close Anki until the required decks are complete.")
                return True
            return False

        if event_type == QEvent.Type.WindowStateChange:
            self._handle_window_state_change()
            return False

        if event_type == QEvent.Type.WindowDeactivate:
            self._schedule_focus_loss_check()
            return False

        return False

    def _can_ignore_enforcement(self) -> bool:
        config = self.config_store.load()
        if not config.get("enabled", False):
            return True
        if self.fallback.is_active():
            return True
        return False

    def _handle_window_state_change(self) -> None:
        config = self.config_store.load()
        if not config.get("enabled", False) or self.fallback.is_active():
            return

        if self.mw.windowState() & Qt.WindowState.WindowMinimized:
            status = self.progress.get_status(self.mw, config)
            if status.complete:
                return

            logger.info("Intercepted minimize while incomplete: %s", status.reason)
            self._show_popup("No minimizing. Finish the required decks first.")

            def _restore() -> None:
                self.mw.setWindowState(self.mw.windowState() & ~Qt.WindowState.WindowMinimized)
                self.mw.showNormal()
                self.mw.raise_()
                self.mw.activateWindow()

            QTimer.singleShot(0, _restore)

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

        if self._should_ignore_focus_loss():
            logger.debug("Ignored focus loss caused by internal Anki UI activity.")
            return

        status = self.progress.get_status(self.mw, config)
        if status.complete:
            return

        if not self._popup_allowed():
            logger.debug("Focus loss detected while incomplete but popup suppressed by cooldown.")
            return

        logger.info("Focus loss detected while incomplete: %s", status.reason)
        self._show_popup("Stay focused. Required decks are not complete yet.")

        if config.get("focus_loss_behavior") == "attempt_refocus":
            QTimer.singleShot(0, self._try_refocus)

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

    def _try_refocus(self) -> None:
        self.mw.raise_()
        self.mw.activateWindow()

    def _show_popup(self, reason: str) -> None:
        if not self._popup_allowed():
            return
        self._last_popup_time = time.monotonic()
        config = self.config_store.load()
        self.popup.show_warning(self.mw, config, self._addon_dir, reason)

    def _popup_allowed(self) -> bool:
        now = time.monotonic()
        return (now - self._last_popup_time) >= self._cooldown_seconds
