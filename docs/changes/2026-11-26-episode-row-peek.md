# Show the next episode at the edge of Kodi’s season shelf

Season shelves show four full episode cards and a sliver of the fifth at
1080p, following Arc for Android TV. Episode artwork keeps its 16:9 proportions.
The episode number, title, synopsis and duration use the narrower card width.
The shelf still scrolls to bring the focused card fully into view.

The change applies to series episode cards. Card sizes elsewhere use their
existing layouts.

## Checks

- Regenerated the skin. `tools/check.py`, all 191 pytest tests and
  `git diff --check` passed.
- In Kodi on Xvfb with a local fixture, verified four full cards with a
  72-pixel fifth-card edge, then scrolled to the fifth episode. Physical
  hardware and playback were outside these checks.

## Logging

Layout only. No new logs.
