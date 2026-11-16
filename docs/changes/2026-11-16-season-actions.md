# A season's menu: Mark Season as Watched / Unwatched, Shuffle Season

The owner's list after "Not in This Order" asked for the season actions the TV app (arc-tv#15)
and the Android app (arc-android#24) have.

## What changed

- OK or Context Menu on a season tab of a show's page opens Arc's menu, titled with the season:
  - **Mark Season as Watched**, or **Mark Season as Unwatched** once every episode on disk is
    watched. It calls `PUT /items/{show}/played` with the season's number in the order shown
    (the route the web's show page uses). The episode cards show their ticks at once, and are put
    back with a message if Arc says no; then the show and its seasons are fetched again, so Play
    follows (Season 1 marked watched: Play moves on).
  - **Shuffle Season**, when the season has more than one episode on disk: a shuffled play queue
    of them (`POST /play-queues`, as the collection page's Shuffle), played as any queue.
- Not in This Order, and a season with nothing on disk, have no menu (Arc can't mark them as a
  season). Episodes not on disk are left as they are.
- Moving along the tabs still shows each season, as before; OK used to do nothing there.
- When the seasons are fetched again while a season tab has the focus (one just marked, or a
  change from another device), the tabs are left in place: emptying the focused list made Kodi
  move the focus to Play and the page jump to the next season to watch.

The choices (`season_actions`, `season_episode_ids`, `mark_season`) are in `arc/titlepage.py`
with tests; `kodi/windows/details.py` draws the menu, and `app.py` has a `queue` place for it.

## Picture subtitles

PGS and VobSub subtitles in a file played as it is are drawn by Kodi itself, and in a converted
stream Arc burns them in (`burn_subtitle`), so nothing more is needed; the parity plan says so.

## Logging

Info: "season marked watched|unwatched (N episodes)"; the queue's existing "playing a queue of N
(shuffled)". Warning: "season not marked: <error type>".

## Checked

Kodi on Xvfb against a scratch Arc (Firefly): Season 1 marked watched (Play moved to the
special), then unwatched (Play S1 · E1), the focus staying on the tab; Specials (one episode)
offers no Shuffle; Shuffle Season started a shuffled queue of 15. Not on real hardware.
