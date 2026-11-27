# The A–Z bar in a library's grid (27 November)

Getting to the S's in a large library meant scrolling down from the top a page at a time. The web,
the Android TV app and the Apple TV app have a letter bar for this, and Plex has one down the right
of a library. Kodi's library grid now has the same bar.

## What changed

- **The bar:** when a library's Library tab is sorted by Title, an A–Z bar runs down the right of
  the grid.
  - It shows only the letters that have titles, with "#" for digits, punctuation and other
    scripts.
  - The letters follow the list's order, so it runs Z to A when the sort is reversed.
  - It follows the filters: with Unwatched or a genre chosen, it counts only what's shown.
  - Other sorts (Date Added, Year…) show no bar, as on the other apps.
- **Moving to it:** Right from the grid's last column reaches the bar, on the letter of the title
  that had the focus. Left goes back to the same title.
- **Select on a letter:**
  - If the grid hasn't loaded that far yet, it first loads the titles up to that letter's first
    title, plus one page past it, at up to 500 titles a request.
  - Then it moves the focus to that letter's first title.
- **The grid's width is unchanged:** it still fits six posters a row. The bar sits in the margin
  at the right.
- **`arc/browse.py`:**
  - The first page of a title-sorted grid asks `/items` for `letters=1`. That parameter is already
    in the v1 contract.
  - `letter_jumps` works out where each letter starts. It matches the web's and Android's
    `letterOffsets` and Apple's `letterJumps`.
  - `pages_to_reach` plans the requests for a jump.
  - Four new tests.
- The new image `arc-pill-white-30.png` is the focused letter's pill.

Screenshots (scratch screenshot library, real Kodi on a virtual display): `2026-11-27-library-letter-bar/`.

## Decisions

- **Same behaviour as the Apple app:**
  - Only the letters that have titles. On a TV, empty letters would be focus stops that do
    nothing.
  - "#" can come twice in Arc's counts: digits come before A and other scripts after Z. It's
    shown once, at its first place in the list.
  - Titles load forwards from what the grid already has, so the grid itself works as before.
    A jump near the end of a very large library makes a few requests: about six for 3,000
    titles.
- **The bar's control id is 140:** the page header already uses 130.

## Checks

- `python3 -m pytest -q`: 195 passed.
- `python3 tools/check.py`: all good.
- `python3 tools/build_skin.py` and `python3 tools/make_media.py` were run, and their output is
  committed.
- **Real Kodi on a virtual display (Xvfb, no GPU), against the scratch screenshot library**
  (24 films):
  - The bar shows the library's 16 letters.
  - Right from Interstellar reached the bar on "I".
  - Select on "L" moved the focus to La La Land.
  - Left returned to the grid.
- **The load-ahead path:** run once with pages temporarily cut to 6 titles, then put back.
  - Select on "U" loaded the 12 missing titles in one request and landed on Up.
  - Up then moved to the row above.
- Not tried:
  - a library with thousands of titles;
  - a reversed sort on screen (the tests cover the Z to A order);
  - real hardware.

## Logging

Nothing new at info level. At debug:

- a jump's loads: "letter jump: loaded N titles in M requests";
- a jump that failed: the error type only.
