# Manual Test Scenarios

These scenarios cover the add-on behaviors that still need a live Anki/Qt session on Windows. The automated suite under `tests/` covers config normalization, fallback auth rules, progress tracking, and core close/minimize enforcement logic.

## TS-01 Settings Entry Points

- Preconditions: Add-on installed and Anki running.
- Steps: Open settings from `Tools -> Anki Enforcer Settings`, then return to the home screen and open settings from `Focus Settings`.
- Expected: Both entry points open the same settings dialog without errors.

## TS-02 Config Persistence

- Preconditions: Settings dialog open.
- Steps: Enable the add-on, select at least one required deck, change popup duration, save, restart Anki.
- Expected: All saved values persist after restart.

## TS-03 Incomplete Study Blocks Close

- Preconditions: Enforcement enabled, at least one required deck still has cards due today.
- Steps: Try to close Anki from the title bar and from the taskbar.
- Expected: Close is blocked and a warning popup appears.

## TS-04 Incomplete Study Blocks Minimize

- Preconditions: Enforcement enabled, at least one required deck still has cards due today.
- Steps: Try minimizing from the title bar, taskbar, and Windows shortcut flow.
- Expected: The main window either never minimizes or is restored immediately to a full-screen state, and only one warning popup is shown.

## TS-04B Incomplete Study Blocks Restore-Down And Resizing

- Preconditions: Enforcement enabled, at least one required deck still has cards due today.
- Steps: Try using the restore-down button, snap Anki to part of the screen, or resize the window manually.
- Expected: The main window returns to full-screen mode and cannot stay shrunk while enforcement is active.

## TS-05 Completed Study Allows Exit

- Preconditions: Enforcement enabled and all required decks complete for the day.
- Steps: Try minimizing and closing Anki.
- Expected: Both actions work normally.

## TS-06 True Focus Loss Warning

- Preconditions: Enforcement enabled and required decks incomplete.
- Steps: Switch away from Anki to another application.
- Expected: A warning popup appears and Anki attempts to regain focus immediately. In stronger focus-lock mode, repeated refocus attempts should follow.

## TS-06B Alt-Tab Escape Attempt

- Preconditions: Enforcement enabled and required decks incomplete.
- Steps: Use `Alt+Tab` repeatedly to switch to another application.
- Expected: Anki forces itself back on top/full-screen quickly enough that you cannot remain outside the app.

## TS-07 In-App Activity Does Not False Trigger

- Preconditions: Enforcement enabled and required decks incomplete.
- Steps: Perform normal in-app flows such as sync, stats, browse, and deck navigation.
- Expected: No warning popup appears for normal in-app Anki activity.

## TS-08 Fallback Password and Lockout

- Preconditions: Settings dialog open.
- Steps: Set a fallback password, save it, then attempt to activate bypass with a wrong password three times.
- Expected: Wrong passwords are rejected, and temporary lockout activates after repeated failures.

## TS-09 Fallback Bypass Behavior

- Preconditions: Valid fallback password configured.
- Steps: Activate fallback bypass with the correct password, then try minimize/close; disable bypass and try again while incomplete.
- Expected: Minimize/close work while bypass is active, and enforcement resumes after bypass is disabled.

## TS-10 Protected Settings Access

- Preconditions: Enforcement enabled, required decks selected, fallback password configured.
- Steps: Close the settings dialog, try reopening it, enter wrong password once, then enter the correct password.
- Expected: Wrong password is rejected clearly, correct password grants temporary access, and first-time setup remains accessible if no password exists.

## TS-11 Popup Asset Fallback

- Preconditions: Add-on installed with bundled image available.
- Steps: Trigger a popup, then temporarily remove or invalidate the bundled image and trigger another popup.
- Expected: The first popup shows the bundled image; the second falls back to text-only mode without crashing.

## TS-12 Packaged Add-on Smoke Test

- Preconditions: Build the `.ankiaddon` package.
- Steps: Install the packaged build into a clean Anki profile and repeat TS-01 through TS-05.
- Expected: Packaged behavior matches the local development version.
