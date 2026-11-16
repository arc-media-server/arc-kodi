# Smaller buttons on the title page and the library pages

The owner asked for smaller buttons on a title's page (and a narrower Play), and the same for the
pills at the top of Recommended and the library pages.

## What changed

- **Title page:** Play is 280 x 64 (was 380 x 76); the round buttons (from the beginning,
  watched, watchlist) are 64 (were 76), their icons 30; the focused button's name sits closer.
- **Library tabs** (Recommended, Browse, Collections, Folders) and the **pills** (Play All,
  Shuffle, Sort, Filter) are 64 high (were 76).
- New `SmallPrimaryButton` / `SmallPillButton` includes and a 64-high surface pill
  (`arc-pill-surface-64.png`, from `tools/make_media.py`), so the smaller pills keep round ends.
- **The pills no longer overlap.** In a library's Browse, Sort was drawn over Shuffle (hiding it)
  and Play All ran under Sort. They now sit in a row from the right: Play All, Shuffle (200
  each), Sort (340), Filter (260); a collection's Sort takes Filter's place at 1540; the page's
  title stops at 740 so it doesn't run under them.
- **Up from Recommended's first row reaches the tabs again.** Since the rows became groups (#14),
  Kodi didn't move the focus out of the first row to the tabs; Home's Up/Down (which Recommended
  shares) now goes to `ABOVE_ROWS` (the tabs) from the first row.

## Checked

- `python3 -m pytest -q`: 99 passed. `python3 tools/check.py`: all good.
  `python3 tools/make_media.py`: only the new pill added. `python3 tools/build_skin.py`: built 14
  windows.
- Kodi 20 on a virtual display against a scratch Arc (not real hardware); screenshots in
  `docs/screens/2026-11-16-smaller-buttons/`: Inception's page (Play and the round buttons, and
  with a round button focused), Films' Recommended, Browse (all four pills, Shuffle visible) and
  the Blade Runner collection. Recommended: Up from the first row went to the tabs, Right to
  Browse, which opened.

## Logging

None.
