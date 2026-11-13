# Arc for Kodi: notes for AI agents

The Kodi client for Arc Media Server: a full-screen add-on (`script.arc`) in the style of PM4K
(Plex for Kodi, `script.plexmod`). It draws its own interface with Kodi's WindowXML and never
touches Kodi's library: no scraping, no `.strm` files, no library sync. The server is
arc-media-server/arc-media-server (Go, with a web app). The look follows the Apple TV app
(arc-media-server/arc-apple); how it behaves inside Kodi (windows, the player, keys, Kodi's own
settings) follows PM4K; the API is the server's `docs/CLIENT-INTEGRATION.md`. The owner (GitHub:
JonzaUK) drives product vision; agents (Claude, Codex) do most implementation. Read `README.md`
and `docs/changes/` (what was built and why). The server repo's CLAUDE.md and docs/API.md are the
wider context; decisions waiting for the owner are on arc-media-server#80.

## Workflow (same as the other repos)

- Everything goes through pull requests: never push to main, never force push. Work on the branch
  the session assigns (Claude: `claude/...`; Codex: `codex/...`). The owner merges.
- Before a PR, run the checks and list the real results:
  - `python3 -m pytest -q` (the `arc/` package and the player logic, against a stand-in server;
    no Kodi needed);
  - `python3 tools/check.py` (every skin XML parses, every control id the Python uses exists in
    its window, every `$ADDON[script.arc N]` and `T(N)` string is in strings.po, and nothing
    under `resources/lib/arc/` imports a Kodi module);
  - when the media changed, `python3 tools/make_media.py` and commit the PNGs it writes.
- Record each change in `docs/changes/YYYY-MM-DD-<slug>.md`; commit messages have a summary, a
  body and the Co-Authored-By trailer. Keep working without check-ins; log product decisions on
  arc-media-server#80; stop only for risky or irreversible things.
- Never mark device, playback, HDR, Dolby Vision, passthrough or refresh-rate checks done without
  evidence from Kodi on real hardware (and say which: Windows, Linux/LibreELEC, Android, Apple
  TV). Never point tests at the owner's server, data or keys.

## Rules

- **API:** only `/api/v1`, through `resources/lib/arc/api.py`. It's promised stable (the server's
  `docs/api-v1-contract.txt`); read answers with `.get()` and defaults, and ignore unknown fields.
  If the app needs something v1 lacks, make an additive server PR and link the two PRs.
- **Two layers:** `resources/lib/arc/` is plain Python 3 (no `xbmc*` imports): the API client,
  models, Home rows, playback decisions, the player's clock and choices. It's what the tests
  cover. `resources/lib/kodi/` is the Kodi side (windows, the player, the artwork proxy,
  settings). Put logic in `arc/` whenever it can be tested without Kodi.
- **Own interface, PM4K-style:** every screen is a `WindowXML` from `resources/skins/Main/1080i/`
  (1920x1080, no dependency on the user's skin beyond its font names). Windows are opened from
  `kodi/app.py`, one at a time, with Back always going back. Never add items to Kodi's video
  library, never write `.strm`/`.nfo` files, never use `plugin://` lists for browsing.
- **Player:** Kodi's own player (`xbmc.Player`) plays; Arc's player dialog
  (`kodi/player.py`, `script-arc-player.xml`) stays open over the video for the whole playback,
  as PM4K's seek dialog does: it owns the controls, seeking (restarting a conversion when a seek
  leaves what's converted), Skip Intro/Recap/Credits, Up Next, audio and subtitle choices.
  Progress goes to Arc on the source file's timeline (`offset_ms` + Kodi's time) every 10 s and
  on pause/stop; conversions are pinged while paused and deleted on stop. Kodi's own resume
  points are ignored: Arc's are the truth.
- **Credentials:** the device token lives in the add-on's profile folder (`addon_data`), never in
  Kodi's settings UI, a URL, a log line or Kodi's databases. Kodi fetches artwork through a small
  local proxy (`kodi/artwork.py`, 127.0.0.1 only, GET image routes only) that adds the Bearer
  header, and media and subtitles through cast links (`POST /cast`), which carry their own scoped
  token. Never use Kodi's `url|Authorization=...` header suffix with the session token.
- **Feel:** a TV app driven by a remote: focus always visible (white, as the Apple app), Back
  always works, Context Menu (C or long OK) for the ⋯ actions, Play on a card plays it. Arc's
  identity through the logo and wordmark. No UI colour (owner, 1 November): chosen and main
  controls are white with black text; the teal is the logo's alone. Dark only; artwork-led Home
  (no banner). Colours live only in `resources/skins/Main/1080i/includes.xml` (and the media
  `tools/make_media.py` draws).
- **Plex first:** where Arc's apps and PM4K differ on Kodi-specific behaviour (keys, the player,
  refresh-rate switching, passthrough), follow PM4K and Kodi's own settings rather than adding
  options; for product behaviour follow the Apple app and Plex. Settings come from the server
  (the profile's prefs) wherever Arc already has them; the add-on's own settings are only what
  only Kodi can know. Log differences on arc-media-server#80.
- **Text:** every user-facing string in
  `resources/language/resource.language.en_gb/strings.po` (ids 30000–30999), used through
  `T(id)` in Python and `$ADDON[script.arc id]` in XML.
- **Logging:** `kodi/log.py` (`xbmc.log`, prefixed `[Arc]`): outcomes and failures at info or
  warning, detail only at debug; never tokens, passwords, PINs, cast links or full URLs (name the
  route, as `api.py` does). Each PR says what it logs.
- **Python:** 3.8 or newer (Kodi 19 Matrix and later), standard library only (no `requests`):
  Kodi on Android and LibreELEC can't install packages.
- **Licence:** AGPL-3.0-only, copyright "The Arc Media Server Authors".

## Layout

```
addon.xml                       the add-on: script.arc, a video script (xbmc.python 3.0.0+)
default.py                      entry point: starts kodi/app.py
resources/lib/arc/              plain Python (+ tests): api, models, home rows, playback, clock
resources/lib/kodi/             Kodi side: app (navigation), windows/, player, artwork proxy,
                                device caps, storage, log, T()
resources/skins/Main/1080i/     the WindowXML screens and includes.xml (colours, shared pieces)
resources/skins/Main/media/     PNGs drawn by tools/make_media.py (icons, logo, gradients)
resources/language/             strings.po
resources/settings.xml          the few Kodi-only settings
tests/                          pytest: the arc/ package against a stand-in Arc server
tools/                          check.py (static checks), make_media.py (draws the media)
docs/changes/                   one note per change
```

## Running it

- Install: zip the repository folder as `script.arc/` (`python3 tools/package.py` writes
  `dist/script.arc-<version>.zip`) and use Kodi's *Add-ons → Install from zip file*.
- Develop against a scratch Arc (`AMS_LISTEN=127.0.0.1:8199 ams -data <scratch> -config none` in
  the server repo, with its `tools/testmedia` library), never the owner's server.
- Kodi logs to `kodi.log` (`~/.kodi/temp/` on Linux, `%APPDATA%\Kodi\` on Windows); turn on
  Kodi's debug logging to see the add-on's debug lines.
