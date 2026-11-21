# Title page rows land in the same place going down or up; header pills not cut off

**What:**
- On a film's or show's page, the focused row (the season bar with its episodes, Cast, Trailers
  & Extras, More Like This, Collections, the info cards) now lands at the foot of the screen
  whether you move down or back up, as Home and Recommended do (arc-kodi#55). It used to land at
  the top going up.
- On a collection's (or playlist's) page, Play All and Shuffle were cut off at the foot: the top
  bar's grouplist was 64 high and the pills 72, plus their focus zoom. It is now 88 high, with
  each control 8 down.
- The blank posters in a title page's Collections row come from the server: the collection image
  link answered 404 for a collection without artwork of its own. Fixed on the server
  (arc-media-server, collection image fallback); no add-on change.

**How:** the same layout as Home's (`skin/script-arc-home.xml`): each row is a screen-tall group
with the row at its foot, overlapped by a -540 item gap and spaced by a spacer before it (the
row's height plus the old 24 gap), so Kodi's scroll to a row's top or foot shows it in the same
place. The season bar and the episodes share one group so they move together. A 540 spacer after
the last row lets it land at the foot too.

**Checks:** `build_skin.py`, `check.py` (all good), pytest. Real Kodi 20.5 (Linux, Xvfb) with a
scratch server: a film's page down through Cast, More Like This and the cards, then back up; Cast
and More Like This are in the same place both ways (screenshots in
`2026-11-21-title-page-scroll-and-pills/`). The collection header and a show's page weren't walked
here. Not tried on a TV box.

**Logging:** nothing new.
