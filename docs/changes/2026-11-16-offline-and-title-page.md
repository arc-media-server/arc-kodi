# Server Unavailable screen, roomier info cards, and a title page that draws at once

Three things the owner noticed testing the add-on.

## Arc-Kodi wouldn't open while the server was offline

When Arc couldn't be reached at start-up, the add-on showed a notification and closed. Now it
always opens: **Server Unavailable** (`signin.UnavailableWindow`, `script-arc-unavailable.xml`),
as the connect screen looks:

- the stacked logo, "Can't Reach <server's name>", and what to check;
- **Try Again** (checks at once; "Still no answer…" if not) and **Change Server** (forgets this
  server and goes to finding one, as Settings' Change Server does);
- it checks Arc's `/health` every 15 seconds and carries on to Home by itself once Arc answers;
- Back leaves the add-on.

`App._load()` is now one loop: loaded, or the screen (retry / change server / leave), or a 401/403
sending the profile back to "Who's watching?".

## The cards at the foot of a title page

About, Details, Cast & Crew and Playback stood 20 apart with their focus ring 6 outside the
card, so the ring touched the next card and was clipped at the list's edge. Each card now sits in
a 440 x 360 slot, 10 in from its edges: the ring stays inside the slot, the cards stand 40 apart,
and the list (420 high) leaves room under them so the ring isn't cut by the screen's foot.

## A title page that sometimes waited to fill in

The page drew its picture and words from the card it was opened from, but Play, the round
buttons' icons (watched, watchlist) and the rest waited for Arc's full answer for the title, so on
a slow answer it sat half-drawn (the owner's screenshot: blank round buttons). Now Play and the
round buttons are drawn from the card's data at once; Arc's answer fills in the rest (genres,
badges, cast, rows) and corrects them. Watched/Watchlist wait for that answer before acting.

How long the answer takes is now logged: "title page loaded in N ms" at debug, or at info when it
takes 3 seconds or more, so a slow server shows in the log.

## Checked

- `python3 -m pytest -q`: 99 passed. `python3 tools/check.py`: all good. `python3
  tools/build_skin.py`: built 14 windows.
- Kodi 20 on a virtual display against a scratch Arc (not real hardware); screenshots in
  `docs/screens/2026-11-16-offline-details/`:
  - with the scratch Arc stopped, the add-on opened on Server Unavailable; Try Again said "Still
    no answer"; the scratch Arc started, and within 15 seconds the add-on went on to Home by itself
    ("Arc answered again", then "loaded 3 libraries");
  - Inception's cards: four across, 40 apart, the focused card's ring whole with room below;
  - Inception's page just after opening: Play and the three round buttons drawn with their icons.
    The scratch server answers in tens of milliseconds ("title page loaded in 31 ms"), so the slow
    case itself wasn't reproduced here.

## Logging

- "Arc can't be reached at start-up" (warning), "Arc answered again" (info).
- "title page loaded in N ms": info at 3 s or more, otherwise debug.
