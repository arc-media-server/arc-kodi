# The title page, as the Apple app's

The first item on the feature-parity list (`docs/plans/feature-parity.md`). The title page was a
hero, Play/Resume, Watched/Watchlist as words, seasons and episodes, and Related. It's now the
Apple app's page, as far as Kodi's controls allow.

## What changed

- **Background in the title's colours.** The server's palette (four corner colours) tints four
  soft corner glows (`arc-glow-*.png`, white, tinted with `setColorDiffuse`) under the artwork,
  which fades into them at the left and the foot through a mask (`arc-hero-mask.png`). The
  colours go through `arc.titlepage.toned()`, a port of the Apple app's `toned()`: they're
  darkened and desaturated so the page stays dark. Kodi has no mesh gradient, so this is an
  approximation of the Apple look.
- **Hero.** The logo (or the title), the info line, the quality badges as capsules (4K/HDR/DV
  filled white; others outlined), the overview, and Starring/Directed by at the right on a soft
  shade so it reads over bright artwork.
- **Play says what plays.** Play, Resume 1:02:03, Play S1 · E5 or Resume S1 · E5 (from
  `titlepage.next_to_play()` / `play_action()`: the in-progress episode, otherwise the first
  unwatched one, otherwise the first). Round icon buttons follow: from the beginning, watched and
  watchlist. The focused button's name shows beside the row, as the Apple app's hint does.
- **Episodes.** Upcoming episodes are dimmed. Selecting an episode, or pressing Play on one,
  plays it.
- **New rows.** Cast & Crew (round photos, name and part; it opens the person's titles), the
  title's Collections (opens the collection), and Trailers & Extras (played in Arc's player
  through `ExtraPlayback`: a direct stream from the extra's `stream_url`, with no progress,
  resume or Up Next, since extras keep no watch state).
- **The About, Details, Crew and Playback cards** at the foot, as the Apple app's. Details: release
  date, runtime, rating and genres. Crew: directors, writers and studio. Playback: the server, the connection (home network or away), the
  profile, quality, bitrate, size and file name. The text is built in `arc/titlepage.py`
  (tested); the session now records `local` from `/auth/status` for the connection line.
- `tools/check.py` also counts media named from the Python (the watched/watchlist icons are set
  through window properties), so they aren't reported as unused.

Up/Down stays Kodi's own grouplist navigation: the page scrolls, and the hero moves up out of
view as focus moves down.

## Checked

- `python3 -m pytest -q`: 47 passed (new `tests/test_titlepage.py`).
- `python3 tools/check.py`: all good.
- Kodi 20 on a virtual display against a scratch Arc (no hardware): Inception (palette, badges,
  Starring, Related, the Cast row with round photos, the cards) and Firefly ("Play S1 · E5",
  season pills, the episode row opening on episode 5). Collections and extras use the same rows
  and Back behaviour, but weren't seen with real data: the test library has no extras, and its
  collections don't show on these titles.

## Logging

One new info line, "playing an extra", when an extra starts. Failures go through the existing
playback error path.

## Limits

- Person and collection pages are plain grids for now. Proper pages come with library parity.
- The episode browser doesn't rise over the hero as a sheet. The page scrolls instead.
