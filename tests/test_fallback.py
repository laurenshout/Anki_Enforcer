from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.support import MemoryConfigStore

from anki_enforcer.services.fallback import FallbackController, hash_password


class FallbackControllerTests(unittest.TestCase):
    def test_activate_and_deactivate_toggle_bypass_state(self) -> None:
        store = MemoryConfigStore(
            {
                "fallback_password_hash": hash_password("secret"),
                "fallback_enabled": False,
            }
        )
        controller = FallbackController(store)

        result = controller.activate_with_password("secret")

        self.assertTrue(result.ok)
        self.assertTrue(controller.is_active())

        controller.deactivate()
        self.assertFalse(controller.is_active())

    def test_wrong_passwords_trigger_lockout_and_then_recover(self) -> None:
        store = MemoryConfigStore({"fallback_password_hash": hash_password("secret")})
        controller = FallbackController(store)

        with patch(
            "anki_enforcer.services.fallback.time.monotonic",
            side_effect=[10.0, 10.0, 10.0, 11.0, 13.0],
        ):
            first = controller.activate_with_password("bad")
            second = controller.activate_with_password("bad")
            third = controller.activate_with_password("bad")
            locked = controller.activate_with_password("secret")
            recovered = controller.activate_with_password("secret")

        self.assertFalse(first.ok)
        self.assertIn("2 attempt(s) left", first.message)
        self.assertFalse(second.ok)
        self.assertIn("1 attempt(s) left", second.message)
        self.assertFalse(third.ok)
        self.assertIn("Try again in 2 second(s)", third.message)
        self.assertFalse(locked.ok)
        self.assertIn("Too many failed attempts", locked.message)
        self.assertTrue(recovered.ok)
        self.assertTrue(controller.is_active())

    def test_authorize_settings_access_expires_after_duration(self) -> None:
        store = MemoryConfigStore({"fallback_password_hash": hash_password("secret")})
        controller = FallbackController(store)

        with patch("anki_enforcer.services.fallback.time.monotonic", return_value=20.0):
            result = controller.authorize_settings_access("secret", duration_seconds=5)

        self.assertTrue(result.ok)

        with patch("anki_enforcer.services.fallback.time.monotonic", return_value=24.0):
            self.assertTrue(controller.has_settings_access_authorization())

        with patch("anki_enforcer.services.fallback.time.monotonic", return_value=25.5):
            self.assertFalse(controller.has_settings_access_authorization())

    def test_missing_password_configuration_returns_clear_error(self) -> None:
        controller = FallbackController(MemoryConfigStore())

        result = controller.activate_with_password("anything")

        self.assertFalse(result.ok)
        self.assertIn("No fallback password is configured yet", result.message)


if __name__ == "__main__":
    unittest.main()
