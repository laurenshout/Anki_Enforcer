from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aqt import gui_hooks, mw

from .config import ConfigStore
from .enforcement import FocusEnforcer
from .fallback import FallbackController
from .popup import PopupManager
from .progress_tracker import ProgressTracker
from .settings_ui import install_settings_action


@dataclass
class AddonRuntime:
    config_store: ConfigStore
    fallback: FallbackController
    popup: PopupManager
    progress: ProgressTracker
    enforcer: Optional[FocusEnforcer] = None


_runtime: Optional[AddonRuntime] = None


def _addon_key() -> str:
    return __name__.split(".")[0]


def _initialize() -> None:
    global _runtime

    if _runtime is not None:
        return

    config_store = ConfigStore(_addon_key())
    fallback = FallbackController(config_store)
    popup = PopupManager()
    progress = ProgressTracker()

    _runtime = AddonRuntime(
        config_store=config_store,
        fallback=fallback,
        popup=popup,
        progress=progress,
    )

    install_settings_action(mw, config_store, fallback, popup, progress)
    _runtime.enforcer = FocusEnforcer(mw, config_store, fallback, popup, progress)
    _runtime.enforcer.install()


def _on_profile_open() -> None:
    _initialize()


gui_hooks.profile_did_open.append(_on_profile_open)

