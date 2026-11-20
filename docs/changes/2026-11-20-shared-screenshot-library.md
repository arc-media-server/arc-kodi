# README screenshots from Arc's shared library

The README's nine pictures are retaken against Arc's shared screenshot library
(arc-media-server#489, its `docs/SCREENSHOTS.md`; owner, 20 November). The library is made of
well-known films and shows matched on TMDB, so these pictures show the same titles, artwork,
descriptions and cast as the server's and the other apps' pictures. The old pictures used the
server's generated test library.

- **Pages:** the same pages as the web README where the add-on has them:
  - Home (Continue Watching, with Severance);
  - the featured film, Dune: Part Two;
  - the featured show, Breaking Bad;
  - the Movies library (Browse);
  - the profile picker (Jordan, Alex, Kids, Sam).

  Also the pages the README already showed: search ("dune"), Watch Together's invite screen
  (from Dune: Part Two, with the Kids profile greyed because it can't watch the film), Settings
  and the sign-in code. The file names are unchanged. Each picture is a 1600×900 JPEG of real
  Kodi at 1920×1080.
- **Retaking them:** `tools/readme_shots.py` drives Kodi with remote keys over JSON-RPC:
  - it types the address and the library's throwaway household password into Arc's own
    keyboard, moving focus key by key as a remote would, and reads Kodi's focused label to find
    its way;
  - it walks the pages and writes `docs/screenshots/*.jpg`;
  - it refuses any address that isn't the scratch server on this machine.

  `docs/DEVELOPING.md` has the steps.
- **README:**
  - the alt text names what each picture shows;
  - the TMDB credit sits under the pictures, worded as the server README's.
- **Removed:** nothing. The add-on had no fixture data or tooling made only for the README
  pictures, because the old pictures used the server's test library.

## Checks

- `python3 -m pytest -q` and `python3 tools/check.py`.
- The walk: Kodi 20.5 under Xvfb (1920×1080) against the library's scratch Arc
  (`node tools/screenshots.mjs --serve`, `127.0.0.1:18299`), run three times from a fresh Kodi
  profile (the first run stopped at a Back step, since fixed). I looked at every picture.

No real hardware was used. The pictures show layout, not playback.

## Limits

- Breaking Bad's backdrop is bright desert, so its description reads less strongly than on
  darker artwork. It is still legible at full size, thanks to the text shadow.
- The walk relies on the pages' current focus order. If a page's layout changes, the script
  stops with the label it couldn't reach rather than taking a wrong picture.

## Logging

None: the add-on is unchanged. The script prints only the files it writes; it never prints the
password, a token or a URL.
