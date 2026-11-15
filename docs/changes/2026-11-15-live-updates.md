# Live updates

Item 5 of the feature-parity list, second half (`docs/plans/feature-parity.md`). Screens were
fetched when they opened and didn't hear about changes after that. The add-on now follows Arc's
change hints (`GET /api/v1/events`, the server's `docs/EVENTS-API.md`), so the screen showing
refreshes itself when something changes elsewhere: a title watched on the Apple TV, a scan that
added a film, the watchlist changed in the web app.

## How it works

- **`arc/events.py`** (plain Python, tested in `tests/test_events.py`):
  - `SSEParser` reads the stream;
  - `Change` says what a hint means (personal state, a library's titles, the list of
    libraries, or everything after a `resync`);
  - `Gatherer` merges hints arriving within a second, as the server asks clients to batch;
  - `EventStream` keeps one stream open: Bearer token in the header (never the URL), resumes
    with `Last-Event-ID`, reconnects every 30 minutes and after drops (backing off 2 to 60 s),
    honours 429's `Retry-After` (the server allows eight streams a profile), and stops for good
    on 401/403. A new stream's opening `resync` is skipped (the app has just loaded); a later
    one refreshes everything. Admin topics (activity, sessions, maintenance) and those only
    playback reads (markers, previews, optimized) are ignored, as are unknown ones.
- **`kodi/live.py`** runs it on a thread from when Home opens until sign-out, a profile switch
  or exit. `stop()` cuts the stream's read short, so Kodi isn't kept waiting on the add-on when
  it closes.
- **The app** keeps the open windows in a stack. On a change it fetches the profile's prefs
  again (personal changes) and the libraries (when they may have changed), then calls `on_live`
  on the window showing. Nothing refreshes under the video: progress reports make hints every
  10 seconds, and windows refresh when playback ends anyway.
- **Each screen refreshes in place, keeping the focus:**
  - Home: rows load again (`on_return`); if the profile's Home itself changed (its rows,
    libraries or the Watchlist's place), Home is rebuilt;
  - library grids (Browse, Collections, Folders, a collection, the Watchlist): the titles shown
    load again; the same titles just get their new state (ticks, progress, new episodes); a
    title added or gone redraws the grid on the title that had focus. Grids now also refresh on
    return from a title or the video, which they didn't before;
  - Recommended and a title's page: as when coming back to them;
  - Search: the same search again;
  - Settings: the values, from the prefs fetched again.
  - Library-scoped hints only refresh that library's screens.

## Checked

- `python3 -m pytest -q`: 85 passed. `python3 tools/check.py`: all good.
- Kodi 20 on a virtual display against a scratch Arc (not real hardware), changing things through
  the scratch server's web session as another device would:
  - "live updates connected" on opening Home;
  - watchlist change: Home refreshed about a second later;
  - Inception marked watched: it left Continue Watching, focus kept;
  - with Films' Browse grid open, Inception marked unwatched and Heat watched: their ticks
    changed in place;
  - a video file added to the Home Videos folder: after Arc's scan, the open grid showed it
    (5 to 6 titles); removed again, the grid redrew with the focus still on the same video;
  - Back from Home: the add-on closed at once with the stream open.
- Not seen: Settings and the title page refreshing (they reuse the return-refresh code, which
  is exercised daily), a 429, and a server restart's resync.

## Logging

- "live updates connected" (info, once per run); "live updates stopped: signed out" (info);
  "live updates failed: <error type>" (warning).
- Debug: each change's topics, which window refreshed, drops and retries, grid redraws.
- Never tokens, the stream's ids or URLs; topics only, no titles.

## Limits

- One stream per add-on run, as the server's per-profile limit needs.
- If the stream can't be held (a proxy that buffers), screens still refresh when you come back
  to them, as before.
