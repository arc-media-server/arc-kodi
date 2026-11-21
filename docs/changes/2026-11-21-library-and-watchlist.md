# Library and Watchlist, as the Android app's (Kodi visual batch 2 of 4)

The second of four batches matching Kodi to the Android app (arc-android main:
`ui/browse/BrowseScreen.kt` `LibraryContent`, `HeaderButton` and `WatchlistContent`,
`ui/browse/LibraryPanels.kt`, `ui/components/Cards.kt` `PillTabs`, `data/WatchlistView.kt`).
It builds on batch 1 (#44). Pictures are in `2026-11-21-library-and-watchlist/`.

## What changed

1. **Heading.** A library's name is the page's heading, large at the top left, on all its tabs
   (Recommended too). The "TV Shows · 5" line under the tabs is gone. Pictures: `tv-library-*`,
   `recommended-tabs-after.jpg`.
2. **Tabs** sit beside the heading in Android's `PillTabs` style: one pill holding
   Recommended · Library · Collections, the showing tab lighter and the focused one white.
   "Browse" is now "Library" (Plex's word, as Android's). Kodi can't draw a holder sized to
   buttons whose widths come from their words, so each tab draws its own slice of it (rounded
   left for the first, right for the last; `tools/make_media.py` `library_tabs`) and the three
   join into one pill. Pictures: `tv-library-*`, `recommended-tabs-after.jpg`.
3. **"24 titles"** at the right of the top bar, before the pills, on a library's Library tab
   (and on collection, playlist and folder pages, where the bare number used to sit under the
   name); not on the Collections tab. Pictures: `tv-library-*`.
4. **No Play All or Shuffle on a library.** They showed there but did nothing (only collection
   and playlist pages are given a queue to play). Shuffle is now a sort (Arc's daily shuffle,
   as Android's), with no "other way round". Play All and Shuffle stay on collection and
   playlist pages, and Play and Shuffle on show pages.
5. **Sort and Filters** are two pills sized to their words, as Android's `HeaderButton`: the
   sort's name ("Title") and "Filters" ("Filters, 1 on" with filters on), instead of
   "Sort: Date Added" and "Filter: All". A library now opens sorted by Title, Android's
   default (it was Date Added). A collection's sort pill likewise shows just its order.
   Pictures: `tv-library-*`.
6. **Watchlist top bar:** the heading "Watchlist", then two pills on the right as Android's:
   what it shows (All, Movies, TV Shows) and its order (Date Added, Title, Release Date). No
   count. The view is `arc.browse.watchlist_view` (tested), the Kodi side
   `WatchlistWindow`. Pictures: `watchlist-*`.

The top bar is one layout for every grid (`script-arc-grid.xml`): the heading with any tabs
(`PageHeader` in `skin/includes.xml`) on the left; the count and the page's pills in a
right-aligned row on the right (`HeaderPill`).

## Decisions

- **Sort names stay Kodi's** ("Date Added", "Duration", "Last Watched"); Android says
  "Recently Added", "Length", "Recently Watched". Which words every app uses is for the words
  batch or the owner, not a layout change.
- **The tab holder is Surface2, nearly opaque,** rather than Android's white at 8%: on the plain
  background they look the same, and over the Recommended tab's artwork the words stay
  readable (the reason for #21's darker tabs).
- **Up from the grid goes to the tabs** on a library (Right from the last tab reaches Sort and
  Filters), and to the pills elsewhere, as before.

## Checks

- `python3 -m pytest -q`: 170 passed (new: Shuffle as a sort, the filter count, the Watchlist
  view; the default-sort tests now expect Title).
- `python3 tools/check.py`: all good. `python3 tools/build_skin.py` and
  `python3 tools/make_media.py` rerun and their output committed.
- On screen, in Kodi 20.5 under Xvfb (1920×1080) with a fresh profile, against the shared
  screenshot library's scratch Arc (arc-media-server main), driven by remote keys over
  JSON-RPC. I looked at every picture:
  - TV Shows: the Recommended tab with its tabs focused; the Library tab; Up into the tabs,
    then Right through Collections, Title and Filters, and Left back; the sort menu (Title
    ticked "A to Z", Shuffle last); Filters → Unwatched Only ("Filters, 1 on");
  - Movies: the Library tab ("24 titles", sorted by title);
  - Watchlist: All and Date Added; All → Movies (two films shown).
- Not seen on screen: a collection or playlist page with Play All and Shuffle in the new
  right-hand row (the scratch library's collections tab was empty), and an Other videos
  library's Folders tab.

No real hardware was used.

## Logging

Nothing new is logged: these are layout changes, and the Watchlist's pills sort on the device.
