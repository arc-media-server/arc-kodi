# README Home picture: Continue Watching as Backdrops

The shared screenshot library now sets Home's look: Continue Watching as Backdrops, each title's
backdrop with its logo, saved as the admin's default Home layout (arc-media-server#491). The
README's Home picture is retaken to match; its alt text says so.

- **Only Home:** the other pictures don't show Home's rows. Watch Together's is the invite screen
  over Dune: Part Two's page, so it stays as it was.
- **No add-on change:** the add-on already reads the profile's Home layout from `/me/prefs`
  (`home`, where Arc fills in the admin's default) and draws the `arc` style as backdrop cards
  with the title's logo. Signed in as Jordan, Continue Watching showed Backdrops straight away.

## Checks

- The library's scratch Arc from arc-media-server's latest main (`node tools/screenshots.mjs
  --serve`, `127.0.0.1:18299`), Kodi 20.5 under Xvfb (1920×1080) with a fresh profile, signed in
  as Jordan with the library's household password, the same way as `tools/readme_shots.py`
  (only the Home picture saved). I looked at the picture.
- `python3 -m pytest -q` and `python3 tools/check.py`.

No real hardware was used.

## Logging

None: the add-on is unchanged.
