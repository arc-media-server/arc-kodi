# Library parity: sort and filters

The rest of feature-parity item 2, starting with a library's Browse grid, as the Apple app's
(ArcKit LibraryQuery and LibraryView). Built on PR #4.

## Sort and filters

- **Seven sorts:** Title, Date Added, Release Date, Year, Rating, Duration and Last Watched.
  Choosing the sort in use again turns it round, as in the Apple app. The menu names the current
  sort's direction (A to Z, Newest first, Highest first, Longest first, Most recent first, or the
  reverse), following the server's own order (`itemOrdering`). Kodi's standard font has no arrow
  characters, so the direction is in words.
- **Filters**, from the library's facets (`GET /libraries/{id}/facets`):
  - Unwatched Only;
  - Genre, Decade and, for films, Resolution, each a list with "Any" and the number of titles
    for each value;
  - Clear Filters, once something is filtered.

  The Filter pill names what's shown (All, Unwatched, a genre, a decade, a resolution, or
  "Filtered" for several), and an empty result says "Nothing matches these filters."
- Changing the sort or a filter keeps the focus on its pill; a grid's first page only takes the
  focus when it's opened.
- The logic is `arc/browse.py`, with tests.

## Fixed along the way

- **Arc's menus showed one row fewer than they had room for.** A list with seven options
  scrolled the first one away and left an empty row. Kodi takes a list's rows per page from its
  height in the skin, not a later `setHeight()`, and the skin had 428 (six and a half rows). The
  menu list is now 512 (its eight rows) and the player's 448 (its seven).
- **Starring is placed by an estimate of its width** (`titlepage.wraps`, from the letters'
  widths, tested against lines seen to fit or wrap in Kodi) instead of a character count. The
  character count left a gap above a line that fitted.

## Checked

- `python3 -m pytest -q`: 63 passed (new `tests/test_browse.py`; Starring cases in
  `test_titlepage.py`).
- `python3 tools/check.py`: all good.
- Kodi on a virtual display, Films:
  - Sort by Title, with the focus staying on Sort;
  - the Sort menu naming "Newest first";
  - Filter → Genre → Thriller, leaving one title and the pill saying "Filter: Thriller";
  - the seven-row Genre list showing whole.

## Logging

A failed facets load logs at debug; the grid works without filters.
