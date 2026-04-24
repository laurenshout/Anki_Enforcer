from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from aqt import gui_hooks, mw

from .config import ConfigStore
from .services.enforcement import FocusEnforcer
from .services.fallback import FallbackController
from .services.progress import ProgressTracker
from .ui.popup import PopupManager
from .ui.settings import install_settings_action, open_settings_dialog


@dataclass
class AddonRuntime:
    config_store: ConfigStore
    fallback: FallbackController
    popup: PopupManager
    progress: ProgressTracker
    enforcer: Optional[FocusEnforcer] = None


_runtime: Optional[AddonRuntime] = None
_HOME_BUTTON_CMD = "focus_enforcer:open_settings"
_hooks_installed = False
_profile_hook_installed = False


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
    _install_home_button_hooks()


def _on_profile_open() -> None:
    _initialize()


def _is_deck_browser_context(context: Any) -> bool:
    if context is None:
        return False
    cls = context.__class__
    # Be strict here: broader matching can inject into multiple deck-browser-related
    # webviews/components and cause duplicate buttons on screen.
    return cls.__name__ == "DeckBrowser"


def _inject_home_button(web_content: Any, context: Any) -> None:
    if not _is_deck_browser_context(context):
        return

    body = getattr(web_content, "body", "")
    marker = "focus-enforcer-home-btn"
    if marker in body:
        return

    button_html = f"""
<style>
.focus-enforcer-home-btn {{
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 9999;
  border: 1px solid #9ca3af;
  border-radius: 10px;
  background: #f8fafc;
  color: #111827;
  padding: 8px 10px;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0,0,0,.12);
}}
.focus-enforcer-home-btn:hover {{
  background: #e5e7eb;
}}
</style>
<script>
(function() {{
  const buttons = Array.from(document.querySelectorAll('.focus-enforcer-home-btn'));
  if (buttons.length > 1) {{
    buttons.slice(0, -1).forEach((el) => el.remove());
  }}
}})();
</script>
<button class="focus-enforcer-home-btn" id="{marker}" onclick="pycmd('{_HOME_BUTTON_CMD}')">
  Focus Settings
</button>
"""
    web_content.body = f"{body}\n{button_html}"


def _handle_home_button_message(handled: Any, message: str, context: Any, *args: Any) -> Any:
    if isinstance(handled, tuple) and handled and handled[0]:
        return handled

    if message != _HOME_BUTTON_CMD or not _is_deck_browser_context(context):
        return handled

    if _runtime is None:
        _initialize()
    if _runtime is None:
        return handled

    open_settings_dialog(
        mw,
        _runtime.config_store,
        _runtime.fallback,
        _runtime.popup,
        _runtime.progress,
    )

    if isinstance(handled, tuple):
        if len(handled) >= 2:
            return (True, handled[1])
        return (True,)
    return True


def _install_home_button_hooks() -> None:
    global _hooks_installed
    if _hooks_installed:
        return

    will_set = getattr(gui_hooks, "webview_will_set_content", None)
    if will_set is not None:
        will_set.append(_inject_home_button)

    did_receive = getattr(gui_hooks, "webview_did_receive_js_message", None)
    if did_receive is not None:
        did_receive.append(_handle_home_button_message)

    _hooks_installed = True


def install_addon() -> None:
    global _profile_hook_installed
    if _profile_hook_installed:
        return
    gui_hooks.profile_did_open.append(_on_profile_open)
    _profile_hook_installed = True
