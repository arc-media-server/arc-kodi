# Watch Together's row under Continue Watching

The owner, 27 November: with rooms waiting, Watch Together's row took Continue Watching's place
at the top of Home, and with it the hero, which then described a room rather than the title
you'd carry on with. It now sits under Continue Watching, in every Arc app that has the row.

## What changed

- `arc/home.py` `place_rooms_row` puts the row under Continue Watching, or the first row; Home's
  window uses it in `_wanted_rows`. Before, the rooms were the first row.

## Decisions

- **Under Continue Watching, or under the first row without it.** When the profile's Home has no
  Continue Watching (hidden, or nothing to carry on with), the rooms go under the first row
  instead, so a row of titles always has the top and the hero. Plex has no equivalent row; its
  Continue Watching always leads Home. The alternative, the rooms last, would hide an invitation
  that's waiting for you below every library's rows.
- The same rule in every app: the web, Android, Apple TV, Kodi and LG/Samsung. Roku has no Watch
  Together yet.

## Checks

- `python3 -m pytest -q`: 192 passed, with a new test for the row's place. `tools/check.py`: all
  good.
- Not tried in Kodi.

## Logging

Nothing new: it's only where a row is drawn.
