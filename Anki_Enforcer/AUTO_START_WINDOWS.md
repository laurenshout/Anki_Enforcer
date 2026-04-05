# Windows Auto-Start (Sprint 9)

## Feasibility

Anki add-ons run **inside** Anki.  
They cannot guarantee Windows login startup behavior by themselves.

Auto-start must be configured at OS level.  
For MVP, this project uses a Startup-folder shortcut approach because it is simple and easy to undo.

## Script

Use:

- `scripts/anki_autostart.ps1`

Supported actions:

- `status`: show whether startup shortcut is present
- `enable`: create startup shortcut for Anki
- `disable`: remove startup shortcut

The script creates a Startup-folder shortcut that launches Anki through a hidden Windows script. This avoids leaving a terminal window open on login when the local `anki.exe` behaves like a console launcher.

## Examples

From project root:

```powershell
powershell -File .\scripts\anki_autostart.ps1 -Action status
powershell -File .\scripts\anki_autostart.ps1 -Action enable
powershell -File .\scripts\anki_autostart.ps1 -Action disable
```

If Anki is installed in a non-standard path:

```powershell
powershell -File .\scripts\anki_autostart.ps1 -Action enable -AnkiPath "D:\Apps\Anki\anki.exe"
```

If you enabled auto-start with an older build and still get a terminal window on login, run `disable` and then `enable` again to recreate the startup entry with the hidden launcher.

## Safety

- No registry edits are performed in MVP.
- No Task Scheduler task is created in MVP.
- Changes are explicit and reversible via `-Action disable`.
