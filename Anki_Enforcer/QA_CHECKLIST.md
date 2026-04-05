# QA Checklist (Sprint 5)

## Environment

- Windows MVP target
- Anki 25.09.2 (or target build under test)

## Core Flows

- Settings dialog opens from `Tools -> Anki Enforcer Settings`
- Deck list loads without error
- Config saves and persists after Anki restart
- Required deck selection persists

## Enforcement

- Incomplete state blocks close
- Incomplete state blocks minimize (or restores window immediately)
- Complete state allows close/minimize
- Focus loss triggers warning popup (best effort)

## Progress Tracking

- `Current study status` reports incomplete while cards remain
- `Current study status` flips to complete when no cards remain for the day

## Popup

- Test popup works
- Popup auto-closes after configured duration
- Bundled image loads successfully
- Text-only fallback works if bundled image is removed/invalid
- Popup messages vary across multiple triggers

## Fallback Bypass

- Password can be set/changed
- Password display/show-hide works as expected in settings
- Wrong password rejected
- Lockout triggers after repeated wrong attempts
- Correct password activates bypass
- Bypass persists until manually disabled
- Disabling bypass resumes enforcement

## Protected Settings Access

- Opening settings requires password when lock conditions are met
- Correct password grants temporary settings access
- Wrong password is rejected with clear message
- First-time setup path remains accessible when no password is configured

## Context-Aware Focus Behavior

- No warning popup during normal in-app actions (sync, browse, stats)
- Warning popup still appears on true app leave/focus loss while incomplete

## Regression Notes

- Record any Anki version-specific API differences observed
- Record any Windows-specific focus/minimize quirks
