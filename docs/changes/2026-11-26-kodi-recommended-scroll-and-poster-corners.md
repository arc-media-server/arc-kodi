# Align Recommended shelves and round Search posters consistently

A focused Recommended shelf lands directly beneath the library tabs from
either direction. Viewport-height focus groups keep the landing position
stable while the shelves retain their usual spacing and the next shelf
can still peek into view.

The rounded mask on a poster follows the card bounds when Kodi crops its
artwork to fill the card. Search, Home and the other shared poster shelves
use that same mask.

## Checks

- Regenerated the skin. `tools/check.py`, `git diff --check` and all 191 pytest
  tests passed.
- In Kodi on a virtual display, reproduced the differing Recommended scroll
  positions with Backdrop, poster and thumbnail shelves. The first and middle
  shelves produced identical captures when reached from above and below after
  the fix. Verified entry from the tabs, returning to the tabs, selecting a
  card and switching tabs with an empty library.
- Verified the same corner curves with portrait and wide source art in Search.
  Physical hardware was outside these checks.

[Recommended](2026-11-26-kodi-recommended-scroll-and-poster-corners/recommended.jpg) ·
[Search](2026-11-26-kodi-recommended-scroll-and-poster-corners/search.jpg)

## Logging

Presentation and scroll geometry only. No new logs.
