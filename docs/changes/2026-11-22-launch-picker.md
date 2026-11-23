# Who's watching on Kodi launch

Opening the add-on asks who's watching while keeping the device linked.
Returning to an open window keeps the current profile. An already selected
single unlocked profile and a friend's own sign-in keep their existing shortcuts.

Settings → Profile and Server offers **Sign in automatically**. It remembers
one profile in this Kodi installation's add-on data. Sign Out clears the choice.
Arc checks the current household before using the saved profile. A deleted or
PIN-protected saved profile opens the picker. The switch shows Off and is
disabled for profiles with a PIN.

PM4K has an option to automatically reopen its last user. Arc stores the profile
explicitly chosen in Settings and requires a PIN every fresh launch for protected
profiles, following Arc's web behavior. [PM4K discussion](https://forums.plex.tv/t/pm4k-plexmod-for-kodi-18-19-20-21-22/481208?page=14)

## Validation

`python3 -m pytest -q` passed 191 tests with one existing pytest plug-in warning.
`python3 tools/check.py` passed. Kodi 20.5 on Xvfb used a fixture session to walk
a fresh launch, profile selection, the setting toggle, auto sign-in to a different
profile, the PIN prompt and the protected switch staying off. Resume behavior was
covered by the decision test. Physical remote, screensaver resume and CoreELEC
hardware were not checked. [Screenshots](2026-11-22-launch-picker/)

## Logging

One info line when opening the picker or signing in automatically. A failed
automatic selection logs its HTTP status. Logs omit profile names, IDs and secrets.
