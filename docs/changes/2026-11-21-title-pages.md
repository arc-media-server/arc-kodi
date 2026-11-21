# Title pages, as the Android app's (Kodi visual batch 3 of 4)

The third of four batches matching Kodi to the Android app (arc-android main:
`ui/details/DetailsScreen.kt` `DetailsScreen`, `Header`, `PlayPill`, `HeroBackdrop`, `Seasons`
and `EpisodeCard`). It builds on batch 2 (#45). Pictures are in `2026-11-21-title-pages/`, as
before/after pairs (`film-*`, `show-*`, `show-down1/2/3-*` after Down once, twice and three
times), with a few more of the new parts (`show-shuffle`, `show-more`, `show-about`,
`show-dots`, `show-menu`, `film-down1`).

## What changed

1. **The header sits low on the first screen.** A film's header (logo, details, description,
   buttons) ends 80 above the screen's foot, with Cast below the fold; a show's is 148 shorter
   (Android's 74 dp peek), so only its season bar shows under it and the episodes wait below.
   Kodi lays controls out from the top, so `arc.titlepage.hero_layout` (tested) stacks the
   header's parts from the foot up and the Python places them. Pictures: `film-*`, `show-*`,
   `film-down1-after.jpg`.
2. **Details around the description.** Above it, the age rating boxed and the genres joined
   with " · ". Under it, the year · the running time (or "5 episodes left" for a show) · a star
   and the score (`rating`, when above 0), then the quality capsules (`titlepage.meta_line`).
   Kodi's font has no ★, so the star is an icon (lucide `star`). Starring and Directed by stay at
   the right, their foot level with the buttons'.
3. **MORE.** The description shows three lines; when that cuts it, it ends with "…", MORE shows
   under it, and the whole block takes the focus (Up from the buttons; glass behind it) and opens
   the full text in Arc's dialog. Kodi can't tell an add-on that a textbox overflowed, so
   `titlepage.clip` estimates the wrapping from the letters' widths, a little short of the box's
   width. Pictures: `show-more-after.jpg`, `show-about-after.jpg`.
4. **Play says what it plays**, in a glass pill (white at 16%) that turns white with black words
   when focused: the play icon, a short bar of how far through when part watched, then "Resume
   from 1:40:12" (a film), "Resume S1 · E3", "Play S1 · E4" or "Start watching · S1 · E1"
   (`titlepage.play_label`, `titlepage.clock`). The pill is sized to its words.
5. **The button row**, in Android's order: Play; Play from the Beginning (only when there's
   something to resume); Shuffle (a show with an episode on disk: every episode on disk in a
   shuffled play queue); Watched; Watchlist; ⋯ (the title's menu, the same one the menu key
   opens). The round buttons are glass like Play. The focused button's name shows under the row.
   Pictures: `show-shuffle-after.jpg`, `show-dots-after.jpg`, `show-menu-after.jpg`.
6. **Episode cards** as Android's `EpisodeCard`: the picture (progress, the watched tick, Not on
   disk dimmed), "S1 · E3" small and muted, the title on one line, up to three lines of the
   description at 65%, then what's left ("36m left") or the running time, and "Not on disk".
   The description under the row (textbox 202) is gone. Hide Spoilers works as before. Kodi
   doesn't wrap a label inside a list, so the Python breaks the lines. Pictures:
   `show-down2/3-*`.
7. **The artwork dims** (to 82% of the page's colour, as Home) once the focus is on the episodes
   or below, and brightens again back on the header or the season bar. Pictures:
   `show-down2/3-after.jpg`, `film-down1-after.jpg`.

Smaller: an episode's own page shows "S1 · E4 · Pilot" under the show's logo, and hides its
description under Hide Spoilers as its card does; Arc's dialog now stops a very long message
short of the screen's edges.

## Decisions

- **A part-watched film reads "Resume from 1:40:12"**, as the batch asked. Android's code shows
  the time left ("1h 6m") when it knows the length and "Resume from …" only when it doesn't;
  say if Kodi should follow that instead (one line in `titlepage.play_label`).
- **Episode cards keep Kodi's wide-card size** (464 picture, 488 apart) rather than Android's
  200 dp (400): the same as every other wide card in Kodi, and room for three lines at 23 px.
- **The number on an episode card is "S1 · E3"** (as the batch and the episode-number rule
  ask); Android's card says "EPISODE 3".
- **The season tabs are unchanged** (not in this batch); Android draws them as the library's
  `PillTabs`, which Kodi now has from batch 2 and could reuse.
- **MORE's focus is white at 20%** rather than Android's 14%: at 14% it didn't show over
  bright artwork (Breaking Bad's sky), and focus must always be visible.
- The title menu from ⋯ is the existing one (Mark Watched, Watchlist, Add to Playlist, Rate…);
  Android's ⋯ also offers Media Info and Watch Together, which Kodi has elsewhere.

## Checks

- `python3 -m pytest -q`: 177 passed (new: the clock, Play's words for a film and a show,
  the meta line, an episode's time left, clipping the description, the header's layout).
- `python3 tools/check.py`: all good. `python3 tools/build_skin.py` and
  `python3 tools/make_media.py` rerun and their output committed (new icons: shuffle, ellipsis,
  star; `arc-pill-surface-64.png` and the unused `SmallPrimaryButton` / `SmallPillButton`
  includes removed).
- On screen, in Kodi 20.5 under Xvfb (1920×1080) with a fresh profile, against the shared
  screenshot library's scratch Arc (arc-media-server main), driven by remote keys over
  JSON-RPC. I looked at every picture:
  - Dune: Part Two (part watched): the header, "Resume from 1:40:12" with its bar, MORE, the
    star and score, Starring and Directed by; Down to Cast (dimmed) and More Like This;
  - Breaking Bad: "Resume S1 · E3", Shuffle among the round buttons, "5 episodes left", the
    season bar under the header; Down to the season tab, to the episodes (dimmed, three-line
    descriptions, "36m left" on the part-watched one) and to Cast; Up to MORE (glass), Select
    (the whole description), ⋯ (the title menu).
- Not seen on screen: "Start watching" and "Play S1 · E4" (the scratch show is part watched),
  an episode's own page, a title without a logo, Not on disk cards, and a title with no rating
  or genres; they come from the same tested helpers.

No real hardware was used.

## Logging

Nothing new is logged: these are layout changes, and Shuffle and ⋯ use the existing play queue
and title menu, which log as before.
