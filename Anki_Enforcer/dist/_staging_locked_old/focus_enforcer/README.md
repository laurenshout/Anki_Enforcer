# Focus Enforcement Anki Add-on (MVP)

An Anki add-on that blocks closing/minimizing (and warns on focus loss) until selected decks have no more cards left to do for the day.

## MVP Behavior

- Select required deck(s) in settings.
- A deck counts as complete when there are no more cards left to do for that day.
- Close/minimize is blocked while incomplete.
- Focus loss shows a warning popup (best effort).
- Popup uses bundled images/messages shipped with the add-on.
- Fallback bypass can be activated with a password and remains enabled until manually disabled.

## Install (Local Testing)

1. Copy this project folder into Anki's add-ons folder as a single add-on directory.
2. Ensure `__init__.py` is directly inside the add-on folder.
3. Restart Anki.

Windows path (typically):

- `%APPDATA%\\Anki2\\addons21\\focus_enforcer\\`

Example structure:

- `addons21/focus_enforcer/__init__.py`
- `addons21/focus_enforcer/config.json`
- `addons21/focus_enforcer/settings_ui.py`
- `addons21/focus_enforcer/assets/images/study-warning.svg`

## Settings UI

Open:

- `Tools` -> `Focus Enforcement Settings`

Configure:

- Enable/disable add-on
- Required deck selection
- Popup duration
- Focus-loss behavior
- Fallback password
- Fallback bypass activation/deactivation

## Popup Assets (Bundled)

- MVP ships with bundled popup assets in `assets/images/`.
- If bundled images are missing or unreadable, popup falls back to text-only mode.

## Testing Checklist (Manual)

- Open settings dialog from `Tools`
- Save config and reopen Anki (persistence)
- Verify `Current study status` updates for selected decks
- While incomplete: close/minimize blocked
- While complete: close/minimize allowed
- Focus loss warning appears (best effort)
- Test popup shows image/message and auto-closes
- Fallback password: wrong password rejected, correct password enables bypass
- Disable fallback bypass and confirm enforcement resumes

## Packaging

Use the PowerShell script:

- `scripts/package_addon.ps1`

It creates a `.ankiaddon` zip in `dist/`.

