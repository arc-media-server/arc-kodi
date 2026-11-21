# Developing Arc for Kodi

Reference for agents and contributors, moved out of `CLAUDE.md` (17 November) so it's read when
needed rather than loaded into every session.

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
- **README screenshots** come from Arc's shared screenshot library (arc-media-server's
  `docs/SCREENSHOTS.md`): run `node tools/screenshots.mjs --serve --state <file>` in the server's
  `web/`, start Kodi as above with a fresh profile, then `python3 tools/readme_shots.py --state
  <file>`. It signs in, walks the pages with remote keys and writes `docs/screenshots/*.jpg`;
  look at each one before committing.
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

- **Shortcuts found 17 November:** Kodi 20 asks about enabling the add-on on first launch
  (`Addons.SetAddonEnabled` then dismiss Kodi's own "Disabled add-ons" prompts); Arc's keyboard
  ignores `Input.SendText`, so instead of typing a server address, write
  `<scratch>/.kodi/userdata/addon_data/script.arc/session.json` with `base_url`, `token` (a device
  token from the scratch server's link flow), `profile_id` and `profile_name`; Kodi caches an
  add-on's strings.po from its first launch, so restart Kodi after adding strings.

## Design notes (full text)

The full form of the rules `CLAUDE.md` summarises.

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
- **Feel:** a TV app driven by a remote: focus always visible (white, as in Arc's design), Back
  always works, Context Menu (C or long OK) for the ⋯ actions, Play on a card plays it. Menus and
  questions are Arc's own (`kodi/windows/menu.py`: `choose`, `confirm`), never Kodi's
  `contextmenu`, `select` or `yesno`; PINs go into Arc's PIN pad (`kodi/windows/pin.py`). Arc's identity through the owner's logo (the server's `docs/brand`, copied into `tools/brand/`): the
  stacked logo on sign-in screens, the full logo in the open sidebar, the TV mark where it's
  small, on the sidebar's icon column. The sidebar's icons are the web and Android apps' (Lucide,
  ISC: `tools/brand/icons/`, notice in `resources/LICENSE-lucide.txt`); the Apple app's are SF
  Symbols, which may only be used on Apple's platforms. No colour anywhere (owner, 1 November; the new logo, 13 November): chosen and main
  controls are white with black text, and the logo is white. Dark only; artwork-led Home (no
  banner). Colours live only in `skin/includes.xml` (and the media `tools/make_media.py` draws).
- **Plex first:** for Kodi-specific behaviour (keys, the player, refresh-rate switching,
  passthrough), follow Kodi's own settings and conventions rather than adding
  options; for product behaviour follow Arc's design (the other Arc apps) and Plex. Settings come from the server
  (the profile's prefs) wherever Arc already has them; the add-on's own settings are only what
  only Kodi can know. Note differences in the PR.
