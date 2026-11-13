# Arc for Kodi: first run in real Kodi, and the owner's logo

The first version had only been checked with unit tests and stand-in Kodi modules. This change
runs it in real Kodi (20.5, on a virtual display) against a scratch Arc with the server's test
library, fixes what that found, and moves to the owner's new logo.

## What changed

- **The skin is built.** Kodi only reads includes, colours and fonts from the user's skin, never
  an add-on's, so the shared pieces were silently ignored. Windows are now written in `skin/` and
  `tools/build_skin.py` expands `skin/includes.xml` into the files Kodi loads. Fonts are the
  standard skin names (`font12`, `font13`, `font32_title`, `font52_title`, `font60`).
- **The owner's logo** (the server's `docs/brand`, 13 November): the stacked logo on Connect and
  Sign-in, the full logo in the open sidebar, the TV mark when it's closed, the square icon as
  the add-on's icon. The teal mark is gone; no colour anywhere. `tools/make_media.py` renders the
  brand SVGs with Chromium (`tools/render_svg.js`) so the lettering is exact.
- **Home:** the icon sidebar opens with names on focus; rows show only once they have cards; Up
  and Down move between rows (one row showing at a time, nothing peeking under the hero); the
  background and details follow the focused card from the first moment; Back to a window keeps
  your place and refreshes its rows; Play on a card plays it.
- **Title page:** Up/Down through Play, the seasons, the episodes and Related; moving along the
  season tabs shows that season; it opens on the season and episode left to watch; Related opens
  its title; the page refreshes after playing (watched state).
- **Cards:** the white border shows only on the focused row; a progress bar on part-watched
  cards; a tick on watched ones; a round avatar in the profile's colour for "Who's watching?".
- **Player:** playback no longer blocks the window that started it (that held back Kodi's player
  events, so Up Next and progress never ran); resume points work for files played as they are;
  Up Next shows the next episode and plays it; Skip and Up Next are window properties, focused
  only once visible, and pass Play/Pause and Stop through; logs no longer name item ids.
- **Settings:** Switch Profile and Sign Out rebuild Home; buttons navigate.
- **Checks:** `tools/check.py` now also fails when the built skin is stale, when the Python names
  a control its window lacks, and when a window uses an image that doesn't exist (or the media
  folder holds an unused one). `tools/kodi_rpc.py` drives Kodi for these checks.

## Checks

- `python3 -m pytest -q`: 29 passed. `python3 tools/check.py`: all good.
- In Kodi 20.5 (Linux, Xvfb, software rendering, no audio device) against a scratch Arc built
  from arc-media-server main with `tools/testmedia`: connect by address, sign in with a code
  approved from the server, choose a profile, Home's rows and sidebar, a library grid with Sort,
  the Watchlist (empty), Search, a film's and a show's title pages with seasons and episodes, a
  direct play (Arc marked it watched), an episode with Up Next playing the next one, Stop
  returning to the title page, Switch Profile.
- **Not checked:** converted (HLS) playback and seeking outside what's converted, Skip Intro (the
  test library has no markers), pause/resume progress, passthrough, HDR, refresh rates, and any
  real device. The virtual display has no audio device, so Kodi's clock runs past a clip's end;
  playback quality needs real hardware.
