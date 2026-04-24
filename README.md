# Anki Enforcer

Anki Enforcer is an Anki add-on that keeps you in study mode until your chosen decks are done for the day. While required decks are incomplete, it can block close/minimize, force the main window back to full size, show warning popups, and try to reclaim focus if you switch away.

## What It Does

- Blocks closing while required decks are incomplete
- Blocks minimizing and pushes the main window back to full-size mode
- Re-enters full-size mode if you restore down, drag, or resize the window
- Shows warning popups with bundled images and messages
- Supports password-protected fallback bypass
- Protects settings once enforcement is active
- Can launch Anki automatically at Windows login

## Installation

Choose one of these approaches.

### Install From Source Folder

1. Download the repository as a ZIP file and extract it.
2. Locate your Anki add-ons folder: `%APPDATA%\Anki2\addons21\`
3. Copy the extracted `Anki_Enforcer` folder into `addons21`.
4. Restart Anki.

### Install From Packaged Add-on

1. Obtain the built `.ankiaddon` file.
2. In Anki, go to `Tools` > `Add-ons` > `Install from file...`
3. Select the `.ankiaddon` file.
4. Restart Anki.

## Quick Start

1. Open `Tools` > `Anki Enforcer Settings` or click `Focus Settings` on Anki's home screen.
2. Enable the add-on.
3. Select one or more required decks.
4. Pick a focus lock strength:
   `Standard focus lock` uses lighter focus reclaim.
   `Aggressive focus lock` uses repeated focus reclaim attempts.
5. Set a fallback password.
6. Save.

Completion rule: a required deck counts as complete when there are no more cards scheduled for review that day.

## Daily Behavior

### When Required Decks Are Incomplete

- Closing Anki is blocked.
- Minimizing Anki is blocked.
- If you restore down, drag, or resize the main window, it is forced back to full-size mode.
- If you switch to another app, the add-on shows a warning popup and attempts to bring Anki back to the foreground.

### When Required Decks Are Complete

- Enforcement is released.
- Anki returns to normal close/minimize behavior.

You can check current status anytime in settings under `Current study status`.

## Settings

### Focus Lock Strength

- `Standard focus lock`: lighter focus reclaim after true app leave.
- `Aggressive focus lock`: repeated focus reclaim attempts after true app leave.

### Fallback Password

The fallback password is used for:

- activating fallback bypass
- opening protected settings while enforcement is active

Wrong passwords are rejected, and repeated failures trigger a temporary lockout.

### Protected Settings

Once the add-on is enabled, decks are selected, and a password is set:

- opening settings requires the fallback password
- successful entry unlocks settings temporarily
- active fallback bypass also allows settings access

## Fallback Bypass

If you need to exit Anki urgently:

1. Open settings.
2. Click `Activate Fallback Bypass`.
3. Enter your fallback password.
4. Enforcement stays disabled until you manually turn the bypass off.

To resume enforcement, open settings and click `Disable Fallback Bypass`.

## Popups And Assets

### Popup Images

You can add your own popup images:

1. Open the add-on folder in `%APPDATA%\Anki2\addons21\[addon_folder]\`
2. Open `assets\images\`
3. Add image files such as PNG, JPG, SVG, WEBP, or BMP
4. Restart Anki

If no valid image is available, the popup falls back to text-only mode.

### Popup Messages

The current implementation uses bundled popup messages. Message editing is not exposed in the UI right now.

### Popup Timing

- Popup duration is configurable in settings
- Default duration is 4 seconds
- You can trigger a test popup from settings

## Windows Auto-Start

Windows auto-start is controlled from the settings dialog.

1. Click `Browse...` next to `Anki executable path`
2. Select `anki.exe`
3. Save
4. Click `Enable Auto-Start`

The helper script is `scripts/anki_autostart.ps1`.

Example commands:

```powershell
powershell -File .\scripts\anki_autostart.ps1 -Action status
powershell -File .\scripts\anki_autostart.ps1 -Action enable
powershell -File .\scripts\anki_autostart.ps1 -Action disable
```

See `AUTO_START_WINDOWS.md` for more detail.

## Troubleshooting

### Add-on Seems Inactive

- Make sure the add-on is enabled in settings
- Make sure at least one required deck is selected
- Check `Current study status`
- Restart Anki

### Wrong Study Status

- Click `Refresh Status`
- Confirm the selected decks actually still have cards due today

### Locked Out Of Settings

- Use the fallback password
- If the password is forgotten, you may need to reset the add-on configuration manually

### Auto-Start Issues

- Confirm the configured path points to the correct `anki.exe`
- Use `Refresh Auto-Start`
- Disable and re-enable auto-start to recreate the launcher

### Popup Images Do Not Show

- Make sure valid image files exist in `assets\images`
- Restart Anki after adding or replacing images

## Limitations

- Focus reclaim is best-effort, not a full kiosk-mode Windows lock
- Some system-level shortcuts may still briefly switch away before Anki is brought back
- Exact behavior can vary across Anki and Qt versions
- In-app Anki flows are filtered to reduce false warnings, but edge cases can still exist

## Testing

- Automated tests: `python -m unittest discover -s tests -v`
- Manual live-Anki scenarios: `tests/MANUAL_TEST_SCENARIOS.md`
- QA checklist: `QA_CHECKLIST.md`

## Project Layout

- Root `__init__.py`: Anki add-on entrypoint
- `anki_enforcer/`: main package
- `anki_enforcer/ui/`: settings and popup UI
- `anki_enforcer/services/`: enforcement, fallback, and progress logic
- `scripts/`: packaging and Windows auto-start helpers
