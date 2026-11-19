# Subtitle Timing

Applies the owner's decision on arc-media-server/arc-media-server#479: the subtitle setting has one
name and one value style across Arc's apps.

- The player's Playback menu item and its submenu title read **Subtitle Timing** (was "Subtitle
  Offset"). Only the string (#30381) changed; the menu kind, stored state and ids are unchanged.
- Subtitle values are written as Arc writes them everywhere: `+1.5s (later)`, `−0.5s (earlier)`
  (a true minus sign, U+2212, no space before the "s"), and `0.0s` for none. New strings #30386
  and #30387 carry the direction; `arc/playback.py`'s `subtitle_timing()` formats the number.
- Audio Offset is not part of the decision and is unchanged ("50 ms later").
- Fixed in passing: string #30384 ("%s earlier") had no `msgstr` line.

Not changed here: the decision also describes 0.5 s steps up to ten seconds either way. Kodi's
subtitle steps and the menu's list of values are behaviour, not strings, so they stay as they
are; a separate change can follow if wanted.

Validation (19 November): 165 pytest checks (new ones for the format) and `tools/check.py` passed.
No skin changes. Not checked in Kodi or on a TV.
