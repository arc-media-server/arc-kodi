# Rows-only Recommended

Recommended now starts with its first shelf under the library tabs, matching
Arc for Android TV. Moving through shelves uses the full area below the tabs.
Up from the first shelf returns to the tabs and Down re-enters at the first
shelf. An empty library shows the existing empty message and leaves the tabs
available.

The layout follows the requested Android TV design. The shared row code still
handles posters, thumbnails, Backdrops, and card actions. Home keeps its hero.

## Checks

- Regenerated the Kodi skin, ran `tools/check.py`, and passed all 191 pytest tests.
- Walked the populated and empty Recommended screens in Kodi on Xvfb with a
  local fixture. Checked row navigation, card selection, returning to the tabs,
  and switching to Library from the empty state.
- Physical hardware and playback were outside these checks.

## Logging

Presentation and focus changes only. No new logs.
