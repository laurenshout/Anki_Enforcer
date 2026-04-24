from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests import support
from tests.support import (
    FakeMainWindow,
    FakeWindowEvent,
    MemoryConfigStore,
    RecordingPopup,
    StaticFallback,
    StaticProgress,
    reset_fake_qapplication,
    reset_fake_qtimer,
)

from anki_enforcer.services import enforcement as enforcement_module
from anki_enforcer.services.enforcement import FocusEnforcer


class FocusEnforcerTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fake_qapplication()
        reset_fake_qtimer()
        self.config_store = MemoryConfigStore({"enabled": True})
        self.popup = RecordingPopup()
        self.fallback = StaticFallback(active=False)
        self.mw = FakeMainWindow()

    def test_install_registers_event_filter_once(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=True),
        )

        enforcer.install()
        enforcer.install()

        self.assertEqual(len(self.mw.event_filters), 1)

    def test_close_is_blocked_while_incomplete(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="3 cards left"),
        )
        event = FakeWindowEvent(enforcement_module.QEvent.Type.Close)

        with patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            return_value=100.0,
        ):
            handled = enforcer.handle_event(None, event)

        self.assertTrue(handled)
        self.assertTrue(event.ignored)
        self.assertEqual(len(self.popup.calls), 1)
        self.assertEqual(
            self.popup.calls[0][2],
            "You cannot close Anki until the required decks are complete.",
        )

    def test_new_minimize_is_blocked_and_window_is_restored(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="2 cards left"),
        )
        self.mw.setWindowState(enforcement_module.Qt.WindowState.WindowMinimized)
        event = FakeWindowEvent(
            enforcement_module.QEvent.Type.WindowStateChange,
            old_state=enforcement_module.Qt.WindowState.WindowNoState,
        )

        with patch.object(
            enforcement_module.QTimer,
            "singleShot",
            side_effect=lambda _delay, callback: callback(),
        ), patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            side_effect=[100.0, 100.0, 100.0],
        ):
            handled = enforcer.handle_event(None, event)

        self.assertTrue(handled)
        self.assertTrue(event.ignored)
        self.assertEqual(self.mw.windowState(), enforcement_module.Qt.WindowState.WindowFullScreen)
        self.assertEqual(self.mw.show_normal_calls, 0)
        self.assertEqual(self.mw.show_maximized_calls, 0)
        self.assertEqual(self.mw.show_full_screen_calls, 1)
        self.assertEqual(self.mw.raise_calls, 1)
        self.assertEqual(self.mw.activate_calls, 1)
        self.assertEqual(self.popup.calls[0][2], "No minimizing. Finish the required decks first.")
        self.assertEqual(enforcer._suppress_focus_loss_until, 101.0)
        self.assertTrue(
            self.mw.window_flags.get(enforcement_module.Qt.WindowType.WindowStaysOnTopHint, False)
        )

    def test_restore_down_is_recovered_to_fullscreen(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="2 cards left"),
        )
        self.mw.setWindowState(enforcement_module.Qt.WindowState.WindowNoState)
        event = FakeWindowEvent(
            enforcement_module.QEvent.Type.WindowStateChange,
            old_state=enforcement_module.Qt.WindowState.WindowMaximized,
        )

        with patch.object(
            enforcement_module.QTimer,
            "singleShot",
            side_effect=lambda _delay, callback: callback(),
        ), patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            side_effect=[200.0, 200.0, 200.0],
        ):
            handled = enforcer.handle_event(None, event)

        self.assertFalse(handled)
        self.assertEqual(self.mw.windowState(), enforcement_module.Qt.WindowState.WindowFullScreen)
        self.assertEqual(self.mw.show_full_screen_calls, 1)
        self.assertTrue(
            self.mw.window_flags.get(enforcement_module.Qt.WindowType.WindowStaysOnTopHint, False)
        )

    def test_resize_fallback_reenters_fullscreen_without_popup(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="2 cards left"),
        )
        self.mw.setWindowState(enforcement_module.Qt.WindowState.WindowNoState)
        event = FakeWindowEvent(enforcement_module.QEvent.Type.Resize)

        with patch.object(
            enforcement_module.QTimer,
            "singleShot",
            side_effect=lambda _delay, callback: callback(),
        ), patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            return_value=300.0,
        ):
            handled = enforcer.handle_event(None, event)

        self.assertFalse(handled)
        self.assertFalse(event.ignored)
        self.assertEqual(self.mw.windowState(), enforcement_module.Qt.WindowState.WindowFullScreen)
        self.assertEqual(self.mw.show_full_screen_calls, 1)
        self.assertEqual(self.popup.calls, [])

    def test_move_fallback_reenters_fullscreen_without_popup(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="2 cards left"),
        )
        self.mw.setWindowState(enforcement_module.Qt.WindowState.WindowNoState)
        event = FakeWindowEvent(enforcement_module.QEvent.Type.Move)

        with patch.object(
            enforcement_module.QTimer,
            "singleShot",
            side_effect=lambda _delay, callback: callback(),
        ), patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            return_value=400.0,
        ):
            handled = enforcer.handle_event(None, event)

        self.assertFalse(handled)
        self.assertFalse(event.ignored)
        self.assertEqual(self.mw.windowState(), enforcement_module.Qt.WindowState.WindowFullScreen)
        self.assertEqual(self.mw.show_full_screen_calls, 1)
        self.assertEqual(self.popup.calls, [])

    def test_minimize_is_allowed_when_study_is_complete(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=True, reason="done"),
        )
        self.mw.setWindowState(enforcement_module.Qt.WindowState.WindowMinimized)
        event = FakeWindowEvent(
            enforcement_module.QEvent.Type.WindowStateChange,
            old_state=enforcement_module.Qt.WindowState.WindowNoState,
        )

        handled = enforcer.handle_event(None, event)

        self.assertFalse(handled)
        self.assertFalse(event.ignored)
        self.assertEqual(self.popup.calls, [])

    def test_focus_loss_popup_is_suppressed_during_blocked_minimize_restore(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="2 cards left"),
        )
        enforcer._last_focus_loss_check_time = 0.0
        enforcer._suppress_focus_loss_until = 2.0

        with patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            side_effect=[1.0, 1.0],
        ):
            enforcer._handle_focus_loss()

        self.assertEqual(self.popup.calls, [])

    def test_focus_loss_reclaims_focus_even_in_standard_mode(self) -> None:
        self.config_store = MemoryConfigStore(
            {"enabled": True, "focus_loss_behavior": "warn_only"}
        )
        support.DummyApplication._instance = SimpleNamespace(
            applicationState=lambda: 0,
            activeWindow=lambda: None,
            activeModalWidget=lambda: None,
            activePopupWidget=lambda: None,
        )
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="2 cards left"),
        )
        enforcer._last_focus_loss_check_time = 0.0

        with patch.object(
            enforcement_module.QTimer,
            "singleShot",
            side_effect=lambda _delay, callback: callback(),
        ), patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            return_value=10.0,
        ):
            enforcer._handle_focus_loss()

        self.assertGreaterEqual(self.mw.raise_calls, 2)
        self.assertGreaterEqual(self.mw.activate_calls, 2)
        self.assertEqual(self.mw.windowState(), enforcement_module.Qt.WindowState.WindowFullScreen)
        self.assertEqual(
            self.popup.calls[0][2],
            "Stay focused. Required decks are not complete yet.",
        )

    def test_release_window_lock_turns_off_topmost_and_exits_forced_fullscreen(self) -> None:
        enforcer = FocusEnforcer(
            self.mw,
            self.config_store,
            self.fallback,
            self.popup,
            StaticProgress(complete=False, reason="2 cards left"),
        )

        with patch.object(
            enforcement_module.QTimer,
            "singleShot",
            side_effect=lambda _delay, callback: callback(),
        ), patch(
            "anki_enforcer.services.enforcement.time.monotonic",
            return_value=500.0,
        ):
            enforcer._enforce_full_size_window()
        enforcer._set_window_topmost(True)

        enforcer._release_window_lock()

        self.assertFalse(
            self.mw.window_flags.get(enforcement_module.Qt.WindowType.WindowStaysOnTopHint, False)
        )
        self.assertEqual(self.mw.windowState(), enforcement_module.Qt.WindowState.WindowMaximized)
        self.assertEqual(self.mw.show_maximized_calls, 1)


if __name__ == "__main__":
    unittest.main()
