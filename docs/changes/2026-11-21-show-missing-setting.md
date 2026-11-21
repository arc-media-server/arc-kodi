# Show missing episodes: one profile setting

Show Missing Episodes is now a single switch in Arc's Settings window, under Playback, saved to
the profile's `show_missing_episodes` pref (arc-media-server#495, off by default). It follows the
profile on every device, as the web (arc-media-server#497) and Android do.

- The season menu loses its Show/Hide Missing Episodes item; it keeps Mark as Watched/Unwatched
  and Shuffle Season. A season with neither (all missing) opens no menu.
- A show's page asks for its seasons with `?missing=1` only when the pref is on.
- The setting is saved through `PATCH /api/v1/me/prefs`, not Kodi's add-on settings.

## Decisions

- Label "Show missing episodes", the web's wording, as asked. Kodi's other rows are in Title Case.
- The switch sits in the Playback section beside Hide Spoilers, the other per-profile display
  choice; no new section for one row.

## Checks

- `python3 -m pytest -q`: 178 passed. `python3 tools/check.py`: all good.
- Kodi 20.5 under Xvfb against a scratch screenshot-library server: the row shows Off and is
  focusable (`settings-before.jpg`, `settings-after.jpg` in this folder). Not tried on real
  hardware.

## Logging

Nothing new: saving prefs already logs failures once where they're handled.
