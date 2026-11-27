# Play Next, Add to Queue and the Queue row (27 November)

From the TV app audit: Kodi could already play a list through a server queue, for Play All and
Shuffle. What it lacked was the editable upcoming queue that the Android, Apple and LG/Samsung
apps have. This follows Android's version: arc-android `docs/changes/2026-10-30-play-queues-server-name.md`
and `2026-11-01-queue-editing.md`.

## What changed

- **Playing a title starts a new queue of it,** as the web player and the other TV apps do.
  - Not in Watch Together.
  - Not for extras.
  - Only when `GET /capabilities` says `play_queues` is supported, available and allowed.
- **Play Next and Add to Queue** are in every card's menu and the title page's menu, for films,
  episodes and shows. A show adds its episodes.
  - A note says what happened.
  - With no queue yet, they start one without playing anything.
- **Home's Queue row** comes first while there's a queue. It shows the title playing and the
  playable titles after it.
  - Select or Play on a card plays on from that entry (`select`).
  - Its menu adds **Move Earlier**, **Move Later** and **Remove from Queue** for the titles after
    the one playing. Each shows only where it can do something.
  - The row reloads after any change.
- **The player:**
  - A queued title plays on whatever Auto-Play is set to, because it was queued on purpose.
  - With nothing queued after the current title, Auto-Play's next episode is added to the end of
    the queue, so the queue stays a true record.
  - Picking another episode from the player's Episodes list moves the queue on if that episode is
    next in the queue. Otherwise it starts a new queue with that episode.
  - A queue played to its end is deleted. Leaving with Back keeps it.
- **`arc/queues.py`** adds:
  - `available`, `PlayQueue.current`, `add`, `select`, `remove`, `move`, `editable`, `upcoming`
    and `delete`;
  - for an edit refused because the queue changed elsewhere (409), the queue is read again and
    the edit retried once.

  Three new tests.

## Decisions

- These follow Android's decisions (arc-media-server#80): queued titles play even with Auto-Play
  off, Back keeps the queue, and the Queue row comes first.
- Play All on a collection now plays its queued titles even with Auto-Play off. Before, that
  needed Auto-Play on.

## Checks

- `python3 -m pytest -q`: 194 passed.
- `python3 tools/check.py`: all good.
- Not run in Kodi or on hardware: the owner is testing.

## Logging

- **Info:** a title queued (next or at the end); a queue played to its end.
- **Warnings,** with the error type: queue start, add, edit, select or advance failures.
