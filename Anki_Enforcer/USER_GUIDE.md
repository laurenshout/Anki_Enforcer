# User Guide: Anki Enforcer

This guide explains how to install, set up, and use the Anki Enforcer add-on.

## What Anki Enforcer Does

Anki Enforcer helps you maintain consistent study habits by preventing you from closing or minimizing Anki until you've completed your selected decks for the day. It includes:

- **Enforcement**: Blocks closing/minimizing while required decks have cards left to review
- **Focus Warnings**: Shows popups when you switch away from Anki
- **Motivational Feedback**: Displays images and messages to keep you motivated
- **Emergency Bypass**: Password-protected way to temporarily disable enforcement

## Installation

1. Download the add-on file (`.ankiaddon`).
2. In Anki, go to `Tools` > `Add-ons` > `Install from file...`.
3. Select the downloaded file and click `Open`.
4. Restart Anki to activate the add-on.

## Opening Settings

Access settings in one of these ways:

1. `Tools` > `Anki Enforcer Settings`
2. Click the `Focus Settings` button on Anki's home screen

## First-Time Setup

1. Open settings.
2. Check `Enable Anki Enforcer`.
3. Select one or more required decks from the list.
4. Set a fallback password (used for emergency bypass and settings access).
5. Click `Save`.

**Completion Rule**: A deck is complete when there are no more cards scheduled for review that day.

## Daily Usage

- **Incomplete Decks**: Closing or minimizing Anki is blocked. Focus loss may show a warning popup.
- **Complete Decks**: Anki behaves normally - you can close or minimize freely.

Check your progress anytime in settings under `Current study status`.

## Emergency Bypass

If you need to exit Anki urgently:

1. Open settings.
2. Click `Activate Fallback Bypass`.
3. Enter your fallback password.
4. Enforcement is disabled until you manually disable the bypass.

Wrong passwords are rejected. Multiple failures temporarily lock further attempts.

## Settings Protection

Once enabled with decks selected and a password set, settings become password-protected:

- Opening settings requires entering the fallback password
- Correct password gives temporary access (5 minutes by default)
- If bypass is already active, settings open without password

## Password Management

The settings include password fields with these options:

- **Fallback password**: Enter or change your password
- **Confirm password**: Re-enter when changing
- **Show/Hide**: Toggle password visibility
- **Password status**: Shows if a password is set

To change password: Enter new password in both fields, then save. To keep current password: Leave fields unchanged.

## Customizing Popups

### Adding Your Own Images

Add custom images to motivate yourself:

1. Locate the add-on folder: `%APPDATA%\Anki2\addons21\[addon_id]\`
2. Open the `assets\images\` folder
3. Add your image files (PNG, JPG, SVG recommended)
4. Restart Anki

The add-on randomly selects images from this folder for popups.

### Adding Motivational Messages

Customize the messages shown in popups:

1. In the add-on folder, open `config.json` with a text editor
2. Find the `"insult_messages"` array
3. Add your own messages as strings in the list
4. Save and restart Anki

Example:
```json
"insult_messages": [
  "Keep going! You're almost done.",
  "Study now, relax later.",
  "Your future self will thank you."
]
```

## Popup Behavior

- Popups appear automatically when enforcement triggers
- They show for the configured duration (default: 4 seconds)
- Include a random image and message
- If no images are available, show text-only
- Test popups anytime in settings with `Test Popup`

## Windows Auto-Start (Windows Only)

Automatically start Anki when Windows boots:

1. In settings, click `Browse...` next to `Anki executable path`
2. Select your `anki.exe` file (usually in Anki's installation folder)
3. Click `Save`
4. Click `Enable Auto-Start` (confirm when prompted)
5. Restart Windows to test

The add-on creates a startup shortcut that launches Anki invisibly.

## Troubleshooting

### Add-on Not Working
- Confirm the add-on is enabled in settings
- Check that required decks are selected
- Verify `Current study status` shows correctly
- Try restarting Anki

### Wrong Status Display
- Click `Refresh Status` in settings
- Ensure selected decks actually have remaining cards

### Auto-Start Issues
- Verify the executable path points to the correct `anki.exe`
- Click `Refresh Auto-Start`
- Disable then re-enable auto-start to recreate the shortcut

### Locked Out of Settings
- Use your fallback password
- If forgotten, you may need to reset the add-on configuration

### Popups Not Showing Images
- Check that image files exist in `assets\images\`
- Ensure files are valid image formats
- Restart Anki after adding images

## Known Limitations

- Focus loss detection works best-effort and may vary by system
- Some in-app actions (like syncing) shouldn't trigger warnings, but this depends on Anki's behavior
- The add-on doesn't provide system-wide locking (like blocking Alt+Tab everywhere)

## Support

If you encounter issues not covered here, check the add-on's GitHub page for updates or report problems.
