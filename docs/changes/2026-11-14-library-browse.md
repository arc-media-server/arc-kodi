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

## Folders (Other videos)

- **An Other videos library has a Folders tab** (Browse, Collections, Folders; no Recommended, as
  the Apple app). It shows a folder's subfolders, each with its cover and how many videos it
  holds, then the videos loose in it (`GET /libraries/{id}/folders?path=`).
  - A folder opens in a window of its own with its name, so Back goes up a level, keeping the
    place.
  - The folder's `path` is passed back as the server gave it (e.g. `0/Holidays`).
- **Other videos show as wide cards** in Browse, Collections and Folders: their pictures are
  stills, which a poster would crop to a sliver. The grid has both layouts and picks one by a
  window property (`arc.style`).

Checked in Kodi with a scratch Other videos library (subfolders Holidays/Summer 2024,
Holidays/Christmas 2023, Concerts and a loose video): Browse as wide cards, Folders with counts,
into Holidays and Back out.

## Person and collection pages

- **A person's page** (from a title's Cast row), as the Apple app's PersonView:
  - their round photo (or initials), name, and "Acting · 14 titles in your libraries";
  - their part in the focused title ("Inception (2010) · as Dom Cobb", or "· Director" behind
    the camera), over that title's background;
  - rows of the Movies and TV Shows they act in, then Behind the Camera, newest first.

  It's Home's window with its own skin (`script-arc-person.xml`, the same control ids), so its
  rows, card menus and Play work as Home's. The grouping is `arc/people.py`, with tests.
- **A collection's page** (from a title's Collections row or a library's Collections tab): its
  name, its overview (the grid moves down under it), and its titles in release order or by
  title from a Sort pill. "This collection has nothing you can watch yet" when it's empty. The
  grid now has a hook for when a page arrives (`page_loaded`), which the collection uses for its
  header.

Checked in Kodi: Leonardo DiCaprio's page from Inception's cast; the Blade Runner Collection from
Films → Collections.
