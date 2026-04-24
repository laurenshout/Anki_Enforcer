from __future__ import annotations

from copy import deepcopy
from typing import Any

from aqt import mw


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "required_deck_ids": [],
    "fallback_password_hash": "",
    "fallback_password_plain": "",
    "anki_executable_path": "",
    "fallback_enabled": False,
    "popup_duration_seconds": 4,
    "image_folder": "assets/images",
    "insult_messages": [
        "No excuses. Finish your decks first.",
        "Sit down and review your cards.",
        "You can leave after the required decks are done.",
        "Back to work. Decks first, distractions later.",
    ],
    "focus_loss_behavior": "warn_only",
}


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class ConfigStore:
    def __init__(self, addon_key: str) -> None:
        self._addon_key = addon_key

    def load(self) -> dict[str, Any]:
        raw = mw.addonManager.getConfig(self._addon_key) or {}
        return self.normalize(raw)

    def save(self, config: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalize(config)
        mw.addonManager.writeConfig(self._addon_key, normalized)
        return normalized

    def normalize(self, config: dict[str, Any] | None) -> dict[str, Any]:
        result = deepcopy(DEFAULT_CONFIG)
        if not isinstance(config, dict):
            return result

        result.update(config)

        result["enabled"] = bool(result.get("enabled", False))
        result["required_deck_ids"] = [
            int(deck_id)
            for deck_id in (result.get("required_deck_ids") or [])
            if str(deck_id).isdigit()
        ]
        result["fallback_password_hash"] = str(result.get("fallback_password_hash") or "")
        result["fallback_password_plain"] = str(result.get("fallback_password_plain") or "")
        result["anki_executable_path"] = str(result.get("anki_executable_path") or "").strip()
        result["fallback_enabled"] = bool(result.get("fallback_enabled", False))
        result["popup_duration_seconds"] = max(
            1, min(15, _coerce_int(result.get("popup_duration_seconds", 4) or 4, 4))
        )
        # Kept for backward compatibility; MVP uses bundled assets and the UI does not expose this.
        result["image_folder"] = str(result.get("image_folder") or "assets/images").strip()
        if not result["image_folder"]:
            result["image_folder"] = "assets/images"

        messages = result.get("insult_messages")
        if not isinstance(messages, list):
            messages = []
        cleaned = [str(m).strip() for m in messages if str(m).strip()]
        result["insult_messages"] = cleaned or deepcopy(DEFAULT_CONFIG["insult_messages"])

        behavior = str(result.get("focus_loss_behavior") or "warn_only")
        result["focus_loss_behavior"] = (
            behavior if behavior in {"warn_only", "attempt_refocus"} else "warn_only"
        )
        return result
