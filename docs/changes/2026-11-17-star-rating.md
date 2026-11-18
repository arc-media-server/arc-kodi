# Star rating

A title page's existing Context Menu (C / long OK, Kodi's equivalent of ⋯) now offers **Rate…**
for films, shows and episodes, matching Android #34. **Your Rating** reuses Arc's existing menu:
five stars down to half a star, current choice ticked and focused, and **Clear Rating** only when
rated. Unrated titles start at five stars. Back cancels; choosing the current value sends no
request. Cards' context menus stay short, as Android does.

The API client sends `PUT /api/v1/items/{id}/rating` with 1–10 half-star units, or zero to clear.
Only a successful save changes `user_data.rating`; a refusal preserves the old value and shows
“Couldn't save your rating. Try again.” Existing title callbacks refresh after saving. Strings
use reserved ids 30500–30504.

## Decisions

The default Estuary Noto Sans font lacks the Unicode star glyph. Full/half-star textures are
generated with the existing Pillow media pipeline and drawn in the existing menu's label/detail
slots. The text labels remain available to Kodi; numeric values still use the string catalog.
No font replacement, new screen or setting is needed. Shared menu layouts also regenerate the
player window; ordinary rows have no rating properties and use their existing rendering.

## Checks

- `PYTHONPATH=/workspace/arc-client-tools/python python3 -m pytest -q`: **139 passed**, one
  dependency deprecation warning. Rating tests cover half stars, clearing, escaped ids, request
  bodies, Bearer auth and refusal against a stand-in server.
- `python3 tools/check.py`: passed.
- `python3 tools/make_media.py --star-rating`, `python3 tools/build_skin.py` and
  `python3 tools/build_skin.py --check`: passed; generated outputs committed.
- Actual Debian Kodi 21.2 on Xvfb, default Estuary font, using `tools/kodi_rpc.py`: save 4.5,
  reopen with current choice focused/ticked, clear to zero, and Back preserving an unrated
  title all passed. An isolated refusal proxy verified choosing the current value sends zero
  PUTs; a refused save sends one PUT, shows the exact failure message and keeps the old rating
  focused when reopened.
- The fixture entrypoint opens the repository's actual DetailsWindow against scratch Arc
  0.1.0-dev (the existing `ams-process-shutdown` test build), with `tools/testmedia` synthetic
  films. No owner server, data or keys were used. [960×540 JPEGs](2026-11-17-star-rating/).

Not tried on a TV. These checks do not certify playback, audio, HDR or other hardware behavior.
Main `1175354` had no title-rating action when checked.

## Logging

A refused/failed save logs the outcome and exception class at warning; successful saves log
only at debug. Cancellation and same-value choices are quiet. No credentials, item names,
request bodies or URLs are logged by this feature.
