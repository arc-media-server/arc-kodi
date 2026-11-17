# More library filters: watch status, HDR, video and audio formats, channels

The web's and Android TV's Filters can narrow a library by watch status and by what the files are.
Arc for Kodi only had Unwatched Only, Genre, Decade and Resolution. It now has the rest, from the
same answers (`GET /api/v1/libraries/{id}/facets` and the `/items` filter parameters).

## What changed

**New rows in a library's Filter menu,** each showing what it's set to and opening its own list
(Any, then the choices with how many titles each has, as Genre and Decade already did):
- **Watch Status:** Watched or Not Started (`watch_state` `played` / `unstarted`). It and Unwatched
  Only exclude each other, as Arc requires: choosing one turns the other off.
- **HDR:** Dolby Vision, HDR10+, HLG, HDR10, SDR, or "Not known yet" (`dynamic_range`).
- **Video Format** and **Audio Format:** HEVC, H.264, AV1…, Dolby Digital, Dolby Digital Plus,
  Dolby TrueHD, DTS… (`video_codec`, `audio_codec`).
- **Audio Channels:** 7.1, 5.1, Stereo…, most first (`audio_channels`).

**When the new rows show:** the four media rows show only when the library has more than one
value, or one is already chosen (the web's rule). A chosen value stays in its list even if the
library no longer has it. The Filter pill names a single chosen filter ("Filter: HDR10"), as before.

**Code:** the query, its parameters, the offered/choices rules and the names live in
`arc/browse.py` (plain Python, tested); the window only words and draws them. The audio codec names
moved there too, and the player's audio list uses the same table.

## Decisions

- Same rows, order and rules as Android TV and LG/Samsung, inside Kodi's existing Filter menu
  (Arc's own `menu.choose`, as before): choosing a value closes the menu, as Genre and Decade
  already did here, rather than going back to Filters.

## Checks

- `python3 -m pytest -q`: 134 passed (5 new in `test_browse.py`: Watch Status and Unwatched Only,
  the media filters' parameters, names and Clear, when a row is offered, choices and channel order,
  the names).
- `python3 tools/check.py`: all good.
- In real Kodi 20.5 on a virtual display (Linux, Xvfb; no GPU or audio) against a scratch Arc with
  four generated films (H.264 stereo, HEVC 5.1, HEVC HDR10 E-AC-3 5.1, H.264 7.1):
  - the Filter menu lists the new rows (`filter-menu.jpg`); HDR offers SDR (3) and HDR10 (1)
    (`hdr-list.jpg`);
  - HDR10 leaves Interstellar and the pill reads "Filter: HDR10" (`hdr10-chosen.jpg`);
  - Audio Channels lists 7.1, 5.1, Stereo with counts (`channels-list.jpg`).
- Not tried on Kodi on real hardware.

## Logging

None added: the facets and titles requests are already logged by `api.py` on failure, and a
facets failure is logged at debug as before.
