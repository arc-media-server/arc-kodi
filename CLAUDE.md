# Arc for Kodi: notes for AI agents

The Kodi client for Arc Media Server: a full-screen add-on (`script.arc`) that
draws its own interface with WindowXML and never touches Kodi's library. Its
look follows Arc's design (arc-apple is the fullest version); how it behaves inside Kodi follows
Kodi's own conventions and settings. Read `README.md`; `docs/DEVELOPING.md` has the layout, running it in Kodi, the Kodi gotchas
and the full design notes summarised below.

**Shared rules:** arc-media-server's `docs/AGENT-RULES.md` applies here (workflow, decisions, Arc's
design, API, logging). Read it at the start of a session: `../arc-media-server/docs/AGENT-RULES.md`
when the server is checked out beside this one, otherwise from GitHub. The essentials:

- Pull requests only: never push to main, never force push. Commits end with the Co-Authored-By
  trailer only, no session links. A change note per change in `docs/changes/`.
- Never point tests at the owner's server, data or keys. Never mark device, playback, HDR, Dolby
  Vision, passthrough or refresh-rate checks done without evidence from Kodi on real hardware
  (and say which).
- Only `/api/v1`, through `resources/lib/arc/api.py` (read answers with `.get()` and defaults);
  if it lacks something, an additive server PR, linked.

## This add-on

- **Checks before a PR:** `python3 -m pytest -q` and `python3 tools/check.py`; after changing
  `skin/`, `python3 tools/build_skin.py`; after changing the media, `python3 tools/make_media.py`;
  commit what they write. Check screens in real Kodi when you change them (`docs/DEVELOPING.md`).
- **Two layers:** `resources/lib/arc/` is plain Python, no `xbmc*` imports, and holds the logic the
  tests cover; `resources/lib/kodi/` is the Kodi side. Put logic in `arc/` whenever it can be.
- **Windows:** written in `skin/` with `skin/includes.xml` and built by `tools/build_skin.py`;
  never edit `resources/skins/Main/1080i/` by hand. One window at a time, Back always goes back.
  Never add to Kodi's library, write `.strm`/`.nfo` files or use `plugin://` lists.
- **Playback:** Kodi's own player decodes; prefer original sources and let Kodi's settings handle
  decoding, HDR conversion and audio output (owner, 13 November). Arc's player window stays open
  and modal over the video for the whole playback. Arc's resume points are the truth.
- **Credentials:** the device token lives in `addon_data`, never in Kodi's settings, a URL, a log
  or Kodi's databases. Artwork goes through the local proxy, media through cast links; never
  `url|Authorization=...` with the session token.
- **Feel:** menus and questions are Arc's own (`kodi/windows/menu.py`, `pin.py`), never Kodi's
  dialogs. Colours live only in `skin/includes.xml` (and `tools/make_media.py`). Kodi-specific
  behaviour (keys, player, refresh rate, passthrough) follows Kodi's own settings; product
  behaviour follows Arc's design and Plex. The add-on's own settings are only what only Kodi knows.
- **Text:** every string in `resources/language/resource.language.en_gb/strings.po` (ids
  30000–30999), via `T(id)` and `$ADDON[script.arc id]`.
- **Logging:** `kodi/log.py` (`[Arc]`); name the route, never cast links or full URLs.
- **Python** 3.8+, standard library only. **Licence:** AGPL-3.0-only.
