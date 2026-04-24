from __future__ import annotations

import unittest

from tests import support

support.reset_fake_addon_manager()

from anki_enforcer.config import ConfigStore, DEFAULT_CONFIG


class ConfigStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = support.reset_fake_addon_manager()
        self.store = ConfigStore("focus_enforcer")

    def test_normalize_applies_defaults_and_clamps_values(self) -> None:
        normalized = self.store.normalize(
            {
                "enabled": 1,
                "required_deck_ids": [1, "2", "abc", "-3"],
                "fallback_password_hash": None,
                "fallback_password_plain": None,
                "anki_executable_path": "  C:/Program Files/Anki/anki.exe  ",
                "fallback_enabled": "yes",
                "popup_duration_seconds": 99,
                "image_folder": "   ",
                "insult_messages": [" Keep going ", "  "],
                "focus_loss_behavior": "not_valid",
            }
        )

        self.assertTrue(normalized["enabled"])
        self.assertEqual(normalized["required_deck_ids"], [1, 2])
        self.assertEqual(normalized["fallback_password_hash"], "")
        self.assertEqual(normalized["fallback_password_plain"], "")
        self.assertEqual(normalized["anki_executable_path"], "C:/Program Files/Anki/anki.exe")
        self.assertTrue(normalized["fallback_enabled"])
        self.assertEqual(normalized["popup_duration_seconds"], 15)
        self.assertEqual(normalized["image_folder"], "assets/images")
        self.assertEqual(normalized["insult_messages"], ["Keep going"])
        self.assertEqual(normalized["focus_loss_behavior"], "warn_only")

    def test_normalize_uses_default_messages_when_input_is_invalid(self) -> None:
        normalized = self.store.normalize({"insult_messages": "not-a-list"})
        self.assertEqual(normalized["insult_messages"], DEFAULT_CONFIG["insult_messages"])

    def test_save_and_load_round_trip_through_addon_manager(self) -> None:
        saved = self.store.save(
            {
                "enabled": True,
                "required_deck_ids": [10, "11"],
                "popup_duration_seconds": 2,
            }
        )

        loaded = self.store.load()

        self.assertEqual(saved, loaded)
        self.assertEqual(self.manager.writes[-1][0], "focus_enforcer")
        self.assertEqual(loaded["required_deck_ids"], [10, 11])
        self.assertEqual(loaded["popup_duration_seconds"], 2)


if __name__ == "__main__":
    unittest.main()
