# Anki Enforcer

Anki Enforcer is an add-on designed to help you build consistent study habits by preventing you from closing or minimizing Anki until you've completed your selected decks for the day. It includes motivational popups with images and messages to keep you focused on your learning.

## Why Anki Enforcer?

Many users struggle with procrastination or distractions while studying with Anki. This add-on ensures you finish your daily reviews before allowing you to exit the application, helping you maintain regular study routines and improve long-term retention.

## Features

- **Enforcement Mode**: Blocks closing or minimizing Anki until your required decks have no more cards left to review for the day.
- **Focus Warnings**: Shows a popup warning when you switch away from Anki (best effort detection).
- **Motivational Popups**: Displays random images and encouraging messages to keep you motivated.
- **Flexible Settings**: Choose which decks to enforce, set popup duration, and configure behavior.
- **Fallback Bypass**: Includes a password-protected emergency bypass for situations where you need to exit quickly.
- **Settings Protection**: Password-protected access to settings once enforcement is active.

## Installation

1. Download the add-on file (`.ankiaddon`).
2. In Anki, go to `Tools` > `Add-ons` > `Install from file...`.
3. Select the downloaded `.ankiaddon` file and click `Open`.
4. Restart Anki to activate the add-on.

## How to Use

1. **Open Settings**: Go to `Tools` > `Anki Enforcer Settings` or click the `Focus Settings` button on Anki's home screen.
2. **Enable the Add-on**: Check `Enable Anki Enforcer`.
3. **Select Decks**: Choose the decks you want to complete daily.
4. **Set Password**: Create a fallback password for emergency bypass.
5. **Save Settings**: Click `Save` to apply your configuration.

## Customization

### Adding Your Own Images

Personalize the popup images to keep yourself motivated:

1. Find the add-on folder in your Anki data directory: `%APPDATA%\Anki2\addons21\[addon_folder]\`
2. Open the `assets\images\` subfolder
3. Add your own image files (PNG, JPG, SVG formats work best)
4. Restart Anki

The add-on will randomly select from all images in this folder for popups.

### Adding Motivational Messages

Customize the messages that appear in popups:

1. In the add-on folder, locate `config.json`
2. Open it with a text editor
3. Find the `"insult_messages"` section
4. Add your own messages to the list
5. Save the file and restart Anki

Example customization:
```json
"insult_messages": [
  "Stay focused! Your goals are waiting.",
  "One more review, you're doing great!",
  "Consistency is key - finish strong."
]
```

For detailed instructions, see `USER_GUIDE.md`.
- Controls are backed by `scripts/anki_autostart.ps1` and update status in the dialog.
- Auto-start now uses a hidden Windows launcher so Anki should open without leaving a terminal window attached.

Examples:

```powershell
powershell -File .\scripts\anki_autostart.ps1 -Action status
powershell -File .\scripts\anki_autostart.ps1 -Action enable
powershell -File .\scripts\anki_autostart.ps1 -Action disable
```

See `AUTO_START_WINDOWS.md` for full details.

## Context-Aware Enforcement 

- Focus-loss warnings are filtered to reduce false triggers during in-app workflows (for example sync dialogs).
- Enforcement still applies to actual close/minimize/true leave attempts when required decks are incomplete.
