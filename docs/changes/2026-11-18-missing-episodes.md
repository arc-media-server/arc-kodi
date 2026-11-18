# Show Missing Episodes in Kodi

The season menu now offers **Show Missing Episodes** / **Hide Missing Episodes** using the
existing authenticated `GET /api/v1/series/{id}/seasons?missing=1`. Missing provider episodes
stay focusable for reading their description, are dimmed and labelled **Not on disk**, and
cannot play or open a mutating context menu. Playback selection, Shuffle and Mark Season
continue to use only episodes on disk. No server changes or media writes.

The current season and available episode selection survive a refresh. Missing-only seasons
and Not in This Order retain the visibility toggle. A failed request keeps the last successful
view and reports the existing error message; stale responses cannot overwrite newer requests.
Kodi resets focus when a focused list is rebuilt: the changed season list now restores focus.

## Decisions

- Off by default, local to the open show, retained during refresh/return to that page. Reopening
  the show starts with on-disk episodes. Reuses the existing season menu, matching Arc Android;
  no new settings or layout. The alternative was a new persistent profile preference.
- Plex/PM4K parity for this particular missing-provider-episode control could not be confirmed.
  A bounded Plex search found community feature requests, not a documented native Kodi control;
  this implements Arc's existing API and Android behavior without claiming Plex equivalence.
- Provider coverage depends on what the server knows in the selected ordering. The client does
  not contact metadata providers or trigger a scan. Not in This Order remains a separate list.

## Checks

- Baseline: latest fetched main `848d0d1`; clean new `codex/kodi-missing-episodes` worktree.
- Required Python suite: **165 passed**. After the native focus finding/fix, only the affected
  API/title-page/adapter tests were repeated: **29 passed**. One existing environment plugin
  deprecation warning; no failures remaining.
- `python3 tools/check.py`: passed, repeated after the relevant focus change.
- Actual Kodi **21.2**, Linux/Xvfb, isolated profile and loopback metadata fixture: default hidden,
  show/hide, inserted missing-only season, retained season focus, Back cancelling the menu,
  unavailable episode OK/Play/context blocked, no native player started, authenticated seasons
  requests. The native flow caught the focus reset; its regression failed before the fix and
  passed afterward. The affected native flow passed after correction.
- Actual screenshots: [menu, missing episode, missing-only season](2026-11-18-missing-episodes/).
- No skin/media changes, so no regeneration required. No server suite, provider/network test,
  physical remote, real-device playback, HDR/audio or owner-server acceptance. Generated local
  metadata only; no owner data accessed. Temporary Kodi/display/fixture processes stopped.

## Logging

No new high-volume logs. Uses existing API route/error logging and error toast; no tokens,
URLs, provider response bodies or episode metadata are added to logs.
