# Arc for Kodi: the first version

The start of the Kodi client for Arc, as an add-on (one that draws its own
full-screen interface with WindowXML and never touches Kodi's library) and the Apple TV app's
look (artwork-led, dark, white focus, an icon sidebar). It uses only Arc's stable `/api/v1`.

## What's here

- **`resources/lib/arc/`** — plain Python, no Kodi imports, covered by the tests:
  - `api.py`: the `/api/v1` client (stdlib `urllib` only, no `requests`): sign-in with a TV code,
    profiles, prefs, Home's rows, browsing, seasons, search, playback, progress, keeping a
    conversion alive, cast links. Logs name routes only; the token never follows a cross-host
    redirect.
  - `models.py`: readers over Arc's answers (artwork choice, resume/progress, quality badges,
    runtime/clock), tolerant of missing and new fields.
  - `home.py`: Home's rows arranged as on the web (Continue Watching with show-art, each library's
    newest, the Watchlist at its place, seasonal rows, collections and playlists last), and the
    card model.
  - `playback.py`: the player's choices (device caps, the converted-stream clock and window,
    subtitle auto-selection as Plex's modes, the marker on screen, when Up Next shows).
- **`resources/lib/kodi/`** — the Kodi side:
  - `session.py` (server, token, profile, prefs, libraries), `storage.py` (the token in
    `addon_data`, never in settings/logs), `caps.py` (device caps from Kodi's HDR/passthrough),
    `artwork.py` (a loopback proxy that adds the Bearer header so Kodi's `<texture>` can load
    Arc's artwork), `log.py`, `app.py` (the flow and navigation).
  - `windows/`: Connect, Sign-in (Link a Device), Profiles, Home (sidebar + stacked rows with the
    focused title's artwork behind), the library Grid (Browse with Sort/Filter and paging),
    Details (hero, Play/Resume, Watched/Watchlist, seasons+episodes, Related), Search, Settings.
  - `player.py` + `player_osd.py`: Kodi's own player plays the stream (opened through a cast link
    so it needs no token); Arc's overlay owns Skip Intro/Recap/Credits and Up Next. Progress is
    reported on the source timeline every 10 s and on pause/stop; conversions are pinged while
    paused and deleted on stop; a seek outside the converted window restarts at that position;
    Kodi's own resume points are ignored. Auto-play and auto-skip follow the profile's prefs.
- **The skin** (`resources/skins/Main/1080i/`): one WindowXML per screen, `includes.xml` for the
  colours and shared pieces, media drawn by `tools/make_media.py`. White focus and controls, teal
  for the logo alone, dark only (per the owner's 1 November rule).
- **Tooling**: `tools/check.py` (XML parses, string ids exist, the `arc/` layer has no Kodi
  imports, everything compiles), `tools/make_media.py`, `tools/package.py` (the install zip).

## Decisions (on arc-media-server#80)

- **Stdlib only, no `requests`.** Kodi on Android and LibreELEC can't install Python packages.
- **Artwork through a loopback proxy**, as the Roku/TV apps do for streams: Kodi's image loader
  can't send the Bearer header, so a 127.0.0.1-only proxy adds it; the token never leaves the box.
- **Kodi's own player, not a custom engine.** It already decodes far more than a browser, with
  passthrough and refresh-rate switching; Arc only repackages/converts what the device reports it
  can't play. The caps start from a common set and are narrowed by Kodi's HDR/passthrough settings.
- **Our interface, never Kodi's library.** No scraping or `.strm`; every screen is a WindowXML we
  drive, Back always going back.

## Checks

- `python3 -m pytest -q`: 29 tests, all passing (API client against a stand-in server, Home rows,
  playback logic, models). No Kodi needed.
- `python3 tools/check.py`: skin XML parses, string ids all present, `arc/` stays Kodi-free,
  everything compiles. The Kodi layer also imports and constructs its windows cleanly against
  stub `xbmc*` modules.
- **Not yet run inside Kodi on any device.** The real interface, focus movement, playback,
  passthrough, HDR and refresh-rate switching are unverified until it runs on hardware (Windows,
  LibreELEC, Android, Apple TV). Nothing device-specific is marked done.

## Next

- The title page's foot (About/Details/Crew/Playback cards), the episode browser rising over the
  hero, and the badge capsules, as the Apple app's reference-look plan describes.
- Audio/subtitle switching in the player overlay (Arc-provided tracks via cast VTT), trickplay
  scrubbing, Watch Together.
