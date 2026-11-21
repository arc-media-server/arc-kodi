# README screenshots retaken

The nine README screenshots in `docs/screenshots/` are retaken from main after the four visual
batches (#44–#47) and the Show missing episodes setting (#48). The old ones still showed the
grey background and the earlier sign-in, profiles and Settings screens.

## Checks

- One run of `tools/readme_shots.py` in Kodi 20.5 under Xvfb, with a fresh Kodi profile, against
  arc-media-server's shared screenshot library (`web/tools/screenshots.mjs --serve`, a scratch
  server on this machine). Each picture was checked by eye; none needed fixing.
- No code changed, so no tests were run. Not tried on real hardware.

## Logging

None: pictures only.
