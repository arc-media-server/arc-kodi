# Arc for Kodi: notes for AI agents

The Kodi client for Arc Media Server: a full-screen add-on (`script.arc`) that draws its own interface with Kodi's WindowXML and never
touches Kodi's library: no scraping, no `.strm` files, no library sync. The server is
arc-media-server/arc-media-server (Go, with a web app). The look follows the Apple TV app
(arc-media-server/arc-apple); how it behaves inside Kodi (windows, the player, keys, Kodi's own
settings) follows Kodi's conventions; the API is the server's `docs/CLIENT-INTEGRATION.md`. The owner (GitHub:
JonzaUK) drives product vision; agents (Claude, Codex) do most implementation. Read `README.md`
and `docs/changes/` (what was built and why). The server repo's CLAUDE.md and docs/API.md are the
wider context; decisions waiting for the owner are on arc-media-server#80.

## Workflow (same as the other repos)

- Everything goes through pull requests: never push to main, never force push. Work on the branch
  the session assigns (Claude: `claude/...`; Codex: `codex/...`). The owner merges.
- Before a PR, run the checks and list the real results:
  - `python3 -m pytest -q` (the `arc/` package and the player logic, against a stand-in server;
    no Kodi needed);
  - `python3 tools/check.py` (every skin XML parses, the built windows match `skin/`, every
    control id the Python uses exists in its window, every `$ADDON[script.arc N]` and `T(N)`
    string is in strings.po, and nothing under `resources/lib/arc/` imports a Kodi module);
  - after changing `skin/`, `python3 tools/build_skin.py`; after changing the media,
    `python3 tools/make_media.py`; commit what they write.
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
- **Own interface:** every screen is a `WindowXML` from `resources/skins/Main/1080i/`
  (1920x1080, no dependency on the user's skin beyond its standard font names). Kodi reads
  includes, colours and fonts only from the user's skin, so windows are written in `skin/` with
  our shared pieces (`skin/includes.xml`) and `tools/build_skin.py` expands them into the files
  Kodi loads; never edit `resources/skins/Main/1080i/` by hand. Windows are opened from
  `kodi/app.py`, one at a time, with Back always going back. Never add items to Kodi's video
  library, never write `.strm`/`.nfo` files, never use `plugin://` lists for browsing.
- **Playback compatibility (owner, 13 November):** prefer original sources and let Kodi's own
  player/settings handle decoding, software fallback, HDR/Dolby Vision conversion, tone mapping
  and audio output. Do not infer source restrictions from the display or maintain per-device
  compatibility rules. Keep selected resolution/quality and server/profile limits, progress,
  and existing playback-error fallback. This policy does not certify native HDR/Atmos output.
- **Player:** Kodi's own player (`xbmc.Player`) decodes and shows the stream; Arc's player
  window (`kodi/player_osd.py`, `script-arc-player.xml`) is open, modal, over the video for the
  whole playback and owns the remote: the controls in the Apple/Android layout
  (title, Playback/Audio/Subtitles buttons, timeline), seeking, Skip Intro/Recap/Credits, Up Next,
  the menus. Keep it modal: a modeless window lets keys fall through to Kodi's own full-screen
  player and OSD. Kodi pauses and stops by itself for Play/Pause and Stop; don't repeat those.
  `kodi/player.py` holds the playback: progress on the source file's timeline (`offset_ms` +
  Kodi's time) every 10 s and on pause/stop, conversions pinged while paused and deleted on stop,
  a seek outside what's converted restarting the conversion there. In a file played as it is Kodi
  switches audio and subtitle tracks itself (Arc would otherwise repackage for a non-default audio
  track); in a converted stream audio and picture subtitles ask Arc again and text subtitles come
  as Arc's WebVTT through a cast link. Kodi's own resume points are ignored: Arc's are the truth.
- **Credentials:** the device token lives in the add-on's profile folder (`addon_data`), never in
  Kodi's settings UI, a URL, a log line or Kodi's databases. Kodi fetches artwork through a small
  local proxy (`kodi/artwork.py`, 127.0.0.1 only, GET image routes only) that adds the Bearer
  header, and media and subtitles through cast links (`POST /cast`), which carry their own scoped
  token. Never use Kodi's `url|Authorization=...` header suffix with the session token.
- **Feel:** a TV app driven by a remote: focus always visible (white, as the Apple app), Back
  always works, Context Menu (C or long OK) for the ⋯ actions, Play on a card plays it. Menus and
  questions are Arc's own (`kodi/windows/menu.py`: `choose`, `confirm`), never Kodi's
  `contextmenu`, `select` or `yesno`; PINs go into Arc's PIN pad (`kodi/windows/pin.py`). Arc's identity through the owner's logo (the server's `docs/brand`, copied into `tools/brand/`): the
  stacked logo on sign-in screens, the full logo in the open sidebar, the TV mark where it's
  small, on the sidebar's icon column. The sidebar's icons are the web and Android apps' (Lucide,
  ISC: `tools/brand/icons/`, notice in `resources/LICENSE-lucide.txt`); the Apple app's are SF
  Symbols, which may only be used on Apple's platforms. No colour anywhere (owner, 1 November; the new logo, 13 November): chosen and main
  controls are white with black text, and the logo is white. Dark only; artwork-led Home (no
  banner). Colours live only in `skin/includes.xml` (and the media `tools/make_media.py` draws).
- **Plex first:** for Kodi-specific behaviour (keys, the player,
  refresh-rate switching, passthrough), follow Kodi's own settings and conventions rather than adding
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
skin/                           the windows as written, and includes.xml (colours, fonts, pieces)
resources/skins/Main/1080i/     the windows Kodi loads, built from skin/ by tools/build_skin.py
resources/skins/Main/media/     PNGs from tools/make_media.py (icons, the brand logos, gradients)
resources/language/             strings.po
resources/settings.xml          the few Kodi-only settings
tests/                          pytest: the arc/ package against a stand-in Arc server
tools/                          check.py (static checks), build_skin.py, make_media.py (+ render_svg.js
                                and brand/: the owner's logo files), package.py
docs/changes/                   one note per change
```

## Running it

- Install: zip the repository folder as `script.arc/` (`python3 tools/package.py` writes
  `dist/script.arc-<version>.zip`) and use Kodi's *Add-ons → Install from zip file*.
- Develop against a scratch Arc (`AMS_LISTEN=127.0.0.1:8199 ams -data <scratch> -config none` in
  the server repo, with its `tools/testmedia` library), never the owner's server.
- **Checking it in Kodi** (Linux; real Kodi on a virtual display, no hardware): install Kodi and
  Xvfb (`apt-get install kodi xvfb imagemagick`), build and start a scratch Arc with its test
  library, then `Xvfb :99 -screen 0 1920x1080x24 &` and
  `HOME=<scratch> DISPLAY=:99 kodi --windowing=x11 &` with the repository linked as
  `<scratch>/.kodi/addons/script.arc`. Drive it with `tools/kodi_rpc.py` (remote keys, typing,
  launching the add-on, screenshots) and read `<scratch>/.kodi/temp/kodi.log`. Approve the
  sign-in code with `POST /api/v1/auth/link/approve` from the scratch server's admin session.
  This shows layout, focus, navigation and the API flows, not playback quality: the virtual
  display has no audio device or GPU (Kodi's clock runs on past a clip's end without one).
- Kodi gotchas found that way: a control with a fixed `<visible>` ignores `setVisible()` (use a
  window property in the condition); focusing a control that shows only once it has items fails
  until Kodi's next frame (`focus_when_visible`); a grouplist rewrites its children's Up/Down, and
  a button row inside one needs its own `<ondown>`; Kodi calls `onInit` again on every return to
  a window (`on_return`); never block in a click handler, or Kodi's player events never arrive;
  a horizontal grouplist takes over its children's Left/Right and can't move into a child group
  (lay such a row out as a plain group); a vertical one can't move into a child group either, even
  with `<defaultcontrol>`, so windows whose rows are groups step between them in Python
  (`ArcWindow.ROW_STOPS`, Home's own Up/Down); a grouplist scrolls only until the focused control's
  foot meets its own, so room under a row has to be inside the row; Kodi won't bottom-align a
  wrapping label; an auto-width disabled button makes a capsule that fits its text; a list
  takes how many rows it shows from its height in the skin, not a later `setHeight()`; Kodi's
  standard font has no arrow characters; Kodi sends an `xbmc.Player`'s events only to the thread
  that made it, so make players on the add-on's main thread (or reuse one) and never in a worker;
  a list draws its chosen row with its focused layout even when the list isn't focused; a list's layout
  `condition` is checked once for the whole list, not per item, so different kinds of entry share
  one layout and show their parts by `ListItem.Property` (Settings).
- Kodi logs to `kodi.log` (`~/.kodi/temp/` on Linux, `%APPDATA%\Kodi\` on Windows); turn on
  Kodi's debug logging to see the add-on's debug lines.
