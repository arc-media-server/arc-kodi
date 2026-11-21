# Recommended's hero scrolls away, as Home's

A library's Recommended tab kept its hero (the focused title's logo, details and overview)
fixed on screen while the rows scrolled under it. It now behaves as Home after batch 5 (#50):
the hero is the first entry of the scrolling list, so it scrolls away once focus moves below
the first row, the artwork dims behind the rows (Home's `scrolled` property), and it comes back
when you return to the first row. Up from the first row still goes to the library's tabs.

- `skin/script-arc-library-rows.xml`: the hero moves into the rows' grouplist (Home's hero
  spot 66 and groups 67/68), under the tabs, with Home's dimming layer. Same positions as before
  at the top of the page.
- `kodi/windows/home.py`: reused as is, with two small hooks: `SIZE_HERO` (Recommended keeps the
  skin's hero height, as the tabs sit above it) and Up from the first row reaching
  `ABOVE_ROWS` when Kodi moves to the hero's spot. `recommended.py` turns the hero spot on.

## Checks

`python3 tools/build_skin.py`, `python3 tools/check.py` (all good) and `python3 -m pytest -q`
(180 passed). Real Kodi (21, Linux, Xvfb at 1920×1080) against the shared screenshot library:
Movies → Recommended, Down twice (hero gone, artwork dimmed, rows line up under the tabs), Up
twice (hero back), Up again (focus on the Recommended tab). [Pictures](2026-11-21-recommended-hero/).
Not tried on real hardware or with a physical remote.

## Logging

None added: a layout and focus change; the existing Recommended load logging is unchanged.
