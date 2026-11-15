# Watch Together

Item 6 of the feature-parity list (`docs/plans/feature-parity.md`), as the Apple app's Watch
Together (its `WatchTogetherModel` and screens) on the server's `docs/WATCH-TOGETHER-API.md`. A room
shares one timeline (the title, where it is, playing or paused); everyone streams their own copy
with their own audio, subtitles and quality.

## What changed

- **Starting a room.**
  - Where: "Watch Together…" in a film's or an episode's ⋯ menu (Context Menu), on its page and on cards, wherever Arc allows Watch Together (`/capabilities`).
  - The menu lists the people this profile may invite. Select ticks people (the menu takes a set of ticks now); those who can't watch the title say so and can't be ticked.
  - **Invite** makes a room that waits on their Home rows (and this one's).
  - **Use a Code Instead** makes a room with a code and opens it straight away.
- **Home's Watch Together row**, first while there are rooms.
  - A wide card per room: the title's picture with a "Watch Together" / "Watching now" capsule, and "You're hosting" or "Hosted by Sam".
  - Then a Join with a Code card.
  - Select joins (or returns to) a room. Context Menu offers Join and Decline (Cancel Room for its maker).
  - The row follows Arc's `watch_together` change hints (live updates).
- **Join with a Code**, from Home's row or from Settings' new Watch Together section. It types into Kodi's keyboard, so phone remotes can type it too.
- **The player in a room** (`kodi/player.py`, `kodi/player_osd.py`):
  - **The lobby**, until the room first plays, over the paused picture:
    - the title and who's in the room, each Loading, Ready, Watching or Can't watch this (host marked), and those invited;
    - the host has Start, Invite More People and Leave, plus the code if the room has one;
    - everyone else sees "Waiting for Sam to start…" and Leave.
  - **Shared controls**:
    - the viewer's pause and play (Kodi's own Play/Pause) and seeks (Left/Right, the timeline, chapters, Skip Intro) go to the room as commands;
    - a follower keeps Kodi in step every half second: it plays and pauses with the room, and jumps once more than 2 s out (1.5 s while paused), then leaves Kodi 8 s to land;
    - Kodi's speed moves in tenths, so it can't play 3% faster or slower to drift back as the Apple app does. The follower's own pauses aren't sent back as the viewer's.
  - **Notices** at the top for a few seconds: "Paused by Alex", "Played by Alex", "Alex moved the room".
  - **The Playback menu** adds Invite More People and End for Everyone (host) and Leave.
  - **Up Next and Auto-Skip**: only the host's move the room, and others follow. The Episodes list moves the room too.
  - **A new title**: when the room changes title (the host's Up Next, a chosen episode), every player plays it in the same playback.
  - **Leaving and ending**:
    - Back or Stop leaves the room, and the others carry on;
    - at a title's end a player waits 15 s for the room's next title, then leaves;
    - if the host ends the room, or it's gone, it says so and playback carries on alone.
- **`kodi/together.py`** holds the room:
  - its live stream (`/watch-together/{id}/events`, reconnecting; a 404 means the room is gone);
  - a heartbeat every 2 s (file position, playing/paused/waiting, ready; `waiting` while Kodi is caching);
  - the clock offset every minute (`/time`, lowest round trip of three);
  - commands with one retry after a 409 conflict, adopting the room it returns.
- **`arc/together.py`** (tested in `tests/test_together.py`) holds:
  - codes;
  - the clock offset and where the room should be;
  - the follower's decisions;
  - notices and participants' states;
  - the room stream.
  
  `arc/api.py` gains the room calls (`RoomConflict` for 409s) and shares the SSE opening with live updates.

## Found on the way

Kodi sends an `xbmc.Player`'s events only to the thread that made it, so a playback started from a
worker thread (the room changing title) never heard that it started. The room's player switches
title in place instead, as Up Next does. Recorded in CLAUDE.md's gotchas.

## Checked

- `python3 -m pytest -q`: 95 passed. `python3 tools/check.py`: all good.
- Kodi 20 on a virtual display against a scratch Arc (not real hardware). The other participant was a script signed in as a second profile, "Alex", on another device session (heartbeats and commands through the same `arc` client):
  - **Invite**: Inception's ⋯ menu, Alex ticked, Invite. The room appeared on Home's row ("You're hosting"). Selecting it opened the lobby; Alex's accept showed them as Loading, then Ready; Start played for both.
  - **Code**: Use a Code Instead on a 3-minute video. The lobby showed the code, and Alex joined with it. Then:
    - Alex's seek to 1:30 moved Kodi there;
    - Alex's pause paused Kodi ("Paused by Alex");
    - Alex's play resumed it ("Played by Alex");
    - Kodi's own Play/Pause paused and resumed the room (Alex saw it change, `changed_by` Kodi).
  - **End for Everyone** from the Playback menu ended the room; Kodi carried on alone.
  - **Next episode**: on Firefly's 3-second test episodes, the host's Up Next moved the room through three episodes, each played in the same playback.
  - **As a guest**: Settings → Join with a Code (typed as a phone remote does). The lobby showed "Waiting for Alex to start…"; Alex's Start played Kodi.
  - **Late join**: after leaving, a rejoin started at the room's place (1:12) and caught up with one jump.
  - Back left the room each time ("left the Watch Together room"), and the add-on closed cleanly.
- Not seen: two real Kodi devices, sync over Wi-Fi or the internet, converted streams in a room (seeks there restart the conversion, as outside rooms), Decline/Cancel on Home's row, the 429 messages.

## Logging

- Info: "Watch Together room made for N people" / "with a code", "joined a Watch Together room (N here)", "left the Watch Together room", "the Watch Together room ended", "moving the room to the next episode", "following the room to another title".
- Warning: failed joins, commands, invites and title loads, by error type or status.
- Debug: each command's action, catch-up jumps, stream drops.
- Never codes, tokens, names or positions.

## Limits

- No gentle catch-up (Kodi's tempo steps are a tenth); a player more than 2 s out jumps.
- Joining from Home or a code opens the room's title in the player; if Kodi is already playing something else, that stops.
