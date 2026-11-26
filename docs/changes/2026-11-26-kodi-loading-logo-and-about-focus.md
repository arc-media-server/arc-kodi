# Sharpen Kodi’s loading logo and show the full About focus ring

The loading screen uses a dedicated 803 × 200 PNG rendered from the original
Arc artwork. It has enough pixels for the logo’s existing size at 4K. The
sidebar still uses its own render.

The About row now starts inside the title page’s scroll area. Its first
card has room for the complete focus outline.

## Checks

- Regenerated the media and skin. `tools/check.py`, `git diff --check`, and all
  191 pytest tests passed.
- Verified the logo during the profile handoff in Kodi on a 1080p virtual
  display. Opened a fixture title, focused About, and moved right to the
  neighbouring card. Physical hardware was outside these checks.

[Loading screen](2026-11-26-kodi-loading-logo-and-about-focus/loading.jpg) ·
[Focused About card](2026-11-26-kodi-loading-logo-and-about-focus/about.jpg)

## Logging

Presentation changes only. No new logs.
