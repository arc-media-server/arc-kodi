# Left-align Kodi media card captions

Titles and metadata under poster, thumbnail and Backdrop cards align with the
left edge of the artwork. The shared layouts cover Home, Recommended, Library,
Collections and other media shelves and grids.

Individual episodes on Home and Recommended can show the series name, the
episode title, and the season and episode number on separate lines. Grouped
updates keep their existing captions. Hide Spoilers conceals episode titles for
unstarted episodes.

## Checks

- Regenerated the skin. All 191 pytest tests, `tools/check.py` and
  `git diff --check` passed.
- Exercised Home, all three Recommended shelf styles, Library and Collections
  in Kodi on a virtual display with local fixture data. Checked episode titles
  on started and unstarted cards with Hide Spoilers enabled. Physical hardware
  was outside these checks.

[Home](2026-11-26-kodi-media-card-captions/home.jpg) ·
[Recommended](2026-11-26-kodi-media-card-captions/recommended.jpg) ·
[Library](2026-11-26-kodi-media-card-captions/library.jpg) ·
[Collections](2026-11-26-kodi-media-card-captions/collections.jpg)

## Logging

No new logs.
