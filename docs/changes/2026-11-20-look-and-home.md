# Look and Home, as the Android app's (Kodi visual batch 1 of 4)

The owner compared every app's screens against the shared screenshot library and wants Kodi to
match the Android app (arc-android main: `ui/theme/Theme.kt`, `ui/components/Cards.kt`,
`ui/browse/BrowseScreen.kt`). This is the first of four batches: the look and Home. Pictures
are in `2026-11-20-look-and-home/`, as before/after pairs.

## What changed

1. **Background.** Arc's near-black instead of a grey wash: Android's Background `#0B0B10`,
   Surface `#15151C` and Surface2 `#1F1F28`, in `skin/includes.xml` (`bg`, `surface`,
   `surface2`) and `tools/make_media.py`. Every page's `PageBackground` is now flat `bg`, and
   the hero's scrim fades into it (`arc-wash.png` is gone). The pills drawn in Surface
   (`arc-pill-surface*.png`) follow. Pictures: `tv-library-*`, `watchlist-*`.
2. **Home's hero gives way.** The hero (logo or name, details, overview) is now the first entry
   of Home's scrolling list, so once focus moves below the first row it scrolls away, and the
   artwork dims to 82% of the background, as Android's `HomeContent` and `HeroBackdrop`. Up
   back onto the first row scrolls back to the hero: a hidden spot at the hero's top
   (control 66) takes the focus and hands it on to the first row once the list has scrolled.
   Pictures: `home-row2-*`, `home-back-up-after.jpg`.
3. **Rows line up.** Continue Watching sat 30 px higher than every later row: the rows were 590
   with a 30 gap between them, and Kodi scrolls only as far as a row's foot, so each later row
   landed 30 lower. The gap is now inside each row (620, no gap), so every row's title is at
   the same height. Pictures: `home-*`, `home-row2-*`.
4. **Episode cards** show the show's name, then "S1 · E2" under it (the card rule in
   AGENT-RULES; Android's `cardTitle`): `arc.home.card_title`. This applies to every episode
   card (Continue Watching, search, rows). Pictures: `home-*`.
5. **A card's second line is just the year** ("2024"), as Android's `cardSubtitle`, not the
   year and running time; on Home, library, Watchlist and search cards. Pictures: `home-*`,
   `watchlist-*`.
6. **Unwatched-episodes badge:** a white badge with corners rounded 12 (6 dp) and black
   numbers, 12 in (6 dp) from the picture's top right, as Android's `WatchBadge`
   (`arc-count-badge.png`, a nine-slice). Kodi can't size a picture to its words, so it has a
   width for one, two and three digits (40, 54, 68), the number right-aligned 14 in (7 dp).
   Pictures: `tv-library-*`, `watchlist-*`.
7. **Watched tick:** a white circle with a black check, 44 across (22 dp), 12 in from the top
   right, on every card for a watched title: posters, wide cards (now including the episode
   cards on show pages, which had none) and backdrop cards. The tick and badge are one include,
   `WatchBadge`. Pictures: `show-*`.

## Decisions

- **Down Home, the focused row sits at the foot of the screen with the row above it in view**
  (Kodi's grouplist scrolls only as far as it must, as Android's `minimalBringIntoView`); going
  up, the row comes to the top. Android's own list scrolls the same minimal way.
- **The title page's wash** for a title without a palette (`wash-*`, the Apple app's) is left
  for the title-page batch, as is the rest of the title page.
- **The README's pictures** still show the grey background; I suggest retaking them all once
  the four batches are in, rather than four times.

## Checks

- `python3 -m pytest -q`: 168 passed (a new test for the card title).
- `python3 tools/check.py`: all good. `python3 tools/build_skin.py` and
  `python3 tools/make_media.py` rerun and their output committed.
- On screen, in Kodi 20.5 under Xvfb (1920×1080) with a fresh profile, against the shared
  screenshot library's scratch Arc (arc-media-server main, `node tools/screenshots.mjs
  --serve`), signed in as Jordan, driven by remote keys over JSON-RPC as `tools/readme_shots.py`
  does. I looked at every picture:
  - Home on Continue Watching (items 1, 3, 4, 5);
  - Home after Down twice and back Up twice (items 2, 3);
  - the TV Shows and Movies libraries' Browse grids (items 1, 5, 6);
  - Watchlist (items 1, 5, 6);
  - Breaking Bad's page with its first season (item 7).
- Not seen on screen: a badge of two or three digits (no show in the library has ten or more
  unwatched), and a tick on a poster or backdrop card (nothing in those rows is watched); they
  use the same include as the ones seen.

No real hardware was used.

## Logging

Nothing new is logged: these are layout changes.
