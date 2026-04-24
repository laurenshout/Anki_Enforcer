from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from ..config import ConfigStore


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    return hash_password(password) == stored_hash


@dataclass
class FallbackActivationResult:
    ok: bool
    message: str
    retry_after_seconds: int = 0


@dataclass
class FallbackController:
    config_store: ConfigStore
    _failed_attempts: int = 0
    _locked_until_monotonic: float = 0.0
    _settings_access_granted_until_monotonic: float = 0.0

    def is_active(self) -> bool:
        config = self.config_store.load()
        return bool(config.get("fallback_enabled", False))

    def has_settings_access_authorization(self) -> bool:
        return time.monotonic() < self._settings_access_granted_until_monotonic

    def activate_with_password(self, password: str) -> FallbackActivationResult:
        result = self._verify_password_action(
            password=password,
            on_success="Fallback bypass activated and will remain enabled until you disable it.",
        )
        if not result.ok:
            return result

        config = self.config_store.load()
        config["fallback_enabled"] = True
        self.config_store.save(config)
        return result

    def authorize_settings_access(
        self, password: str, duration_seconds: int = 300
    ) -> FallbackActivationResult:
        result = self._verify_password_action(
            password=password,
            on_success=f"Settings access unlocked for {duration_seconds} second(s).",
        )
        if not result.ok:
            return result

        self._settings_access_granted_until_monotonic = time.monotonic() + max(1, duration_seconds)
        return result

    def _verify_password_action(self, password: str, on_success: str) -> FallbackActivationResult:
        now = time.monotonic()
        if now < self._locked_until_monotonic:
            retry_after = max(1, int(self._locked_until_monotonic - now))
            return FallbackActivationResult(
                False,
                f"Too many failed attempts. Try again in {retry_after} second(s).",
                retry_after_seconds=retry_after,
            )

        config = self.config_store.load()
        stored_hash = str(config.get("fallback_password_hash", "") or "")
        if not stored_hash:
            return FallbackActivationResult(
                False,
                "No fallback password is configured yet. Set one in the settings first.",
            )

        if verify_password(password, stored_hash):
            self._failed_attempts = 0
            self._locked_until_monotonic = 0.0
            return FallbackActivationResult(True, on_success)

        self._failed_attempts += 1
        if self._failed_attempts >= 3:
            lock_seconds = min(60, 2 ** (self._failed_attempts - 2))
            self._locked_until_monotonic = now + lock_seconds
            return FallbackActivationResult(
                False,
                f"Incorrect password. Too many failed attempts. Try again in {lock_seconds} second(s).",
                retry_after_seconds=lock_seconds,
            )

        remaining_before_lock = max(0, 3 - self._failed_attempts)
        return FallbackActivationResult(
            False,
            f"Incorrect password. {remaining_before_lock} attempt(s) left before temporary lockout.",
        )

    def deactivate(self) -> None:
        config = self.config_store.load()
        config["fallback_enabled"] = False
        self.config_store.save(config)
