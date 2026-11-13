# Owner feedback: the title page, Home and libraries

The owner's second look, from screenshots. Ten points, each fixed and checked in Kodi on a
virtual display (no hardware).

## Title page

- **Rows in the Apple app's order:** the cast first (owner, 7 November), then Trailers & Extras,
  Related and Collections, then the cards.
- **The round buttons beside Play couldn't be reached.** They sat in a horizontal grouplist,
  which takes over Left/Right and can't move into a child group. The row is now a plain group
  with fixed positions and explicit Left/Right.
- **Starring and Director** were dropped in mid-right, on a shaded box. They're now as the Apple
  app's: bottom right, level with the buttons, right-aligned, one line each with a muted label
  and the names in bold. A long Starring line wraps above Director; Kodi won't bottom-align a
  wrapping label, so the Python moves it up when it's long enough to wrap.
- **The hero follows the Apple app's layout:**
  - the rating in an outlined capsule, with the genres;
  - the overview, up to four lines;
  - the year and length, with the quality capsules.
- **Quality capsules fit their text.** They were a fixed 100 wide, so HDR10 and DV ran into the
  edges. Each is now a disabled auto-width button with its padding: the resolution filled, the
  rest outlined, up to six.
- **The four colours were mostly grey.** The corner glows faded out long before the middle, and
  the dark base showed through. The page now has an exact four-corner (bilinear) blend over the
  whole screen, as the Apple app's MeshGradient. It's four tinted layers whose opacities give the
  bilinear weights. The artwork mask is now the Apple app's:
  - bright to 60% down, then 45% at the foot;
  - half strength at the left.

  A title with no palette gets the Apple app's dark wash, which is also what shows until the
  palette arrives.

## Home

- **Room under a row's words.** Kodi scrolls a row only until its list's foot meets the
  grouplist's, so the room is now in the list: Home's lists are 60 taller than their cards. The
  row stride is 620, and the words end about 75 px above the foot of the screen (from about 30).
- **Continue Watching's Backdrops style.** The server's row look "arc" (the web's "Backdrops")
  showed as wide thumbnails. Home now has a third set of row slots with the web's squarer 4:3
  backdrop card:
  - the title's (or show's) background art, fading dark at the foot;
  - its logo there, or its name.
- **Unwatched episode count:** a show's poster has the Apple app's tab at its top right, with the
  episodes still to watch, on Home, libraries and grids.
- **An episode's card opens its show,** on its season, with the episode focused, instead of a page
  of its own (as the Apple app). Go to Show in the card menu does the same. The show's art comes
  from the episode, so the page isn't blank while it loads.

## Libraries

- **Recommended, Browse and Collections tabs**, as the Apple app's pill bar. A library opens on
  Recommended (Browse for Other videos), as Plex.
  - **Recommended** is Home's window with another skin: the server's Recommended rows under a
    hero, without the sidebar. The rows are titled from their type in the viewer's language
    (`arc/recommended.py`, tested; Arc's own title for a type the app doesn't know). Each row
    uses the row look the server saved, else posters, or wide cards for Continue Watching and a
    shows library's recently watched episodes.
  - **Collections** is the library's collections in a grid; one opens its titles.
  - Choosing a tab replaces the window, so Back always returns to where the library was opened
    from.

  Folders (Other videos) isn't done yet.

## Checked

- `python3 -m pytest -q`: 57 passed (new `tests/test_recommended.py`; `test_menus.py` covers the
  show's art).
- `python3 tools/check.py`: all good. It now skips `*_SLOTS` counts in the control-id check.
- Kodi 20 on a virtual display against a scratch Arc, with Continue Watching set to Backdrops on
  the scratch profile:
  - Inception's, Firefly's and Blade Runner 2049's pages (a purple wash across the whole page),
    and Right from Play reaching the round buttons;
  - Home's Backdrops row, poster spacing and unwatched tabs;
  - Firefly's episode card landing on S1 E7;
  - Films' Recommended, Collections (and a collection) and Browse tabs, with Back to Home.

## Logging

A failed Recommended load logs a warning naming the error type. Nothing else new.

## Second round (owner's screenshots: The Simpsons, the library tabs)

- **Backdrop cards were too big and square-cornered.** They're now 400x300, about a fifth
  smaller. The corners were lost because Kodi lines a mask up with the whole picture before it
  crops the picture to the control: a 16:9 backdrop cropped to 4:3 lost its sides, and the
  rounded corners went with them. The backdrop now shows at its own 16:9 shape, centred on the
  card, through a 16:9 mask that is clear at the sides with the card's rounded shape in the middle
  (`arc-mask-backdrop-wide.png`).
- **Words were hard to read over bright artwork** (the overview, the season tabs, the hint,
  Starring).
  - A scrim over the title page's artwork (`arc-title-scrim.png`) darkens it at the left, behind
    the hero's words, and towards the foot, behind the tabs and rows.
  - Season tabs, row titles, the hint and every card's words now have shadows; unselected season
    tabs are brighter; Starring's label is lighter.
  - Starring is placed by how many lines it takes, with or without a director, so it no longer
    truncates when there's no director.
- **The library tabs vanished on backgrounds of their own colour.** They're now in one dark
  capsule, as the Apple app's pill bar, with the tab showing lit in it and brighter words for the
  others. Sort and Filter line up with them.

Checked in Kodi on a virtual display: the Backdrops row (corners close up), Mushoku Tensei's page
(bright artwork), and the Films tabs on Recommended (over artwork) and Browse (plain background).

## Third round: tab spacing, Recommended's wait

- **The tabs' spacing was uneven:** every tab was a fixed 240 wide, so a short word sat in a lot
  of space. Each tab is now its own pill sized to its word with the same padding. They're
  auto-width buttons in a horizontal grouplist, three slots each with a "current" and an "other"
  button, shown by a window property. Coming up into the tabs lands on the one showing.
- **Recommended took a while to appear.**
  - On the scratch server the call takes about 13 ms and drawing it 9–36 ms. The wait on the
    owner's server is most likely the server building every row (ten or more, each up to 20
    full titles) for a large library.
  - The add-on now shows Loading… while the first answer comes.
  - It keeps the last rows of each library for the session, so the next visit shows them at
    once and refreshes them behind. The kept rows are dropped with the profile.
  - It logs the time at debug ("library recommended: N rows, fetched in X ms, shown in Y ms").
    A fetch of 1 s or more is logged at info, so a slow server shows in Kodi's log without
    debug logging. The server's own detailed log has a matching "recommended rows … took" line.

## From the owner's kodi.log (Kodi 22 RC2, Windows 11, Microsoft Store build)

- `[Arc] library recommended took 4546 ms`: the server took 4.5 s to answer the Recommended
  call on the owner's library. The scratch server answers in about 13 ms, so the wait is the
  server building its rows for a large library, not the add-on. That's for a server change; the
  add-on now shows Loading… and keeps the rows for the next visit.
- `Control 100 ... has been asked to focus, but it can't` on opening a grid: Kodi refuses focus
  to a panel until its first cards are drawn. The grid and search now focus through
  `focus_when_visible`, which tries again until it takes. Kodi still logs its first refusal.

After the server's Recommended fix (arc-media-server#464), the owner still found the tab slow,
probably because the Unraid container hadn't pulled the new image yet. To tell builds and
timings apart without debug logging:

- the add-on now logs the server's version when it connects ("loaded N libraries from Arc X");
- it logs at info any Recommended call taking 1 s or more (it was 3 s).
