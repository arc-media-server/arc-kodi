"""Watch Together (the server's docs/WATCH-TOGETHER-API.md), as the Apple app's: a room shares one
timeline (the title, where it is, playing or paused); everyone streams their own copy. This has
the room's maths and words, and its live stream; kodi/together.py keeps the room, and the player
follows it.

Plain Python, tested in tests/test_together.py."""

import json
import logging
import time

from .api import APIError, Unreachable
from .events import SSEParser

log = logging.getLogger("arc")

# Kodi plays at 0.8-1.5 in steps of a tenth (its tempo), so it can't play a little faster or
# slower to catch up as the Apple app does (0.97/1.03): it jumps instead, once it's this far out,
# and then leaves the player alone a few seconds while Kodi lands (a jump lands on a keyframe,
# not exactly where asked).
SEEK_DRIFT_MS = 2000
SETTLE_MS = 8000
PAUSED_DRIFT_MS = 1500


# MARK: - codes

def normalise_code(text):
    """A code as Arc wants it: letters and digits, upper case ("abcd-1234" -> "ABCD1234")."""
    return "".join(c for c in (text or "").upper() if c.isascii() and c.isalnum())


def format_code(code):
    """A code as read aloud: XXXX-XXXX."""
    c = normalise_code(code)
    return c[:4] + "-" + c[4:] if len(c) == 8 else c


# MARK: - the room

def is_host(room):
    return bool(room and room.get("self_id") and room.get("self_id") == room.get("host_id"))


def host_name(room):
    for p in (room or {}).get("participants") or []:
        if p.get("id") == room.get("host_id"):
            return p.get("name") or ""
    return (room or {}).get("host_name") or ""


def started(room):
    """The room has played (or moved), so the lobby is over."""
    return bool(room) and (room.get("state") != "paused" or (room.get("position_ms") or 0) > 0)


def should_adopt(next_room, current):
    """Whether `next_room` replaces `current`: the same room only when at least as new."""
    if not current or current.get("id") != next_room.get("id"):
        return True
    return (next_room.get("revision") or 0) >= (current.get("revision") or 0)


def clock_offset(samples):
    """How far the server's clock is ahead of this one (ms), from the /time sample with the
    shortest round trip; samples are (c0, c3, s1, s2). None with no samples."""
    best = None
    for c0, c3, s1, s2 in samples:
        rtt = (c3 - c0) - (s2 - s1)
        offset = ((s1 - c0) + (s2 - c3)) / 2.0
        if best is None or rtt < best[0]:
            best = (rtt, offset)
    return best[1] if best else None


def expected_position(room, server_now_ms):
    """Where the room should be in the file at server time `server_now_ms`."""
    position = room.get("position_ms") or 0
    if room.get("state") != "playing":
        return position
    rate = room.get("rate") or 1
    return position + max(0, server_now_ms - (room.get("at_ms") or 0)) * rate


class Follower(object):
    """Keeps a player in step with the room: what to do each time it looks (every half second).
    `step()` returns a list of ("play",), ("pause",) or ("seek", ms)."""

    def __init__(self):
        self.settle_until = 0

    def step(self, room, local_ms, playing, now_ms, expected_ms):
        actions = []
        if room.get("state") == "playing":
            if not playing:
                actions.append(("play",))
            if now_ms >= self.settle_until and abs(local_ms - expected_ms) > SEEK_DRIFT_MS:
                actions.append(("seek", int(expected_ms)))
                self.settle_until = now_ms + SETTLE_MS
        else:
            # Paused, or waiting for someone to load: hold at the room's place.
            if playing:
                actions.append(("pause",))
            if now_ms >= self.settle_until and abs(local_ms - expected_ms) > PAUSED_DRIFT_MS:
                actions.append(("seek", int(expected_ms)))
                self.settle_until = now_ms + SETTLE_MS
        return actions

    def settle(self, now_ms):
        """This player just moved by itself (a seek the viewer made): leave it a moment."""
        self.settle_until = now_ms + SETTLE_MS


def notice(next_room, before):
    """What to say when someone else changed the timeline: ("paused_by" | "played_by" |
    "moved_by", name), or None."""
    if not before or (next_room.get("revision") or 0) <= (before.get("revision") or 0):
        return None
    by = next_room.get("changed_by")
    if not by or by == next_room.get("self_id"):
        return None
    who = next((p.get("name") for p in next_room.get("participants") or [] if p.get("id") == by), None)
    if not who:
        return None
    if next_room.get("generation") != before.get("generation"):
        return ("moved_by", who)
    if next_room.get("state") == "paused" and before.get("state") != "paused":
        return ("paused_by", who)
    if next_room.get("state") == "playing" and before.get("state") == "paused":
        return ("played_by", who)
    return None


def participant_status(p):
    """unavailable, loading, watching or ready."""
    if not p.get("available"):
        return "unavailable"
    if not p.get("ready") or p.get("state") == "waiting":
        return "loading"
    return "watching" if p.get("state") == "playing" else "ready"


def is_playing(listed):
    """A listed room that's under way ("Watching now")."""
    return listed.get("state") in ("playing", "waiting")


# MARK: - the live stream

BACKOFF = (2, 4, 8, 16, 30)
MIN_LIFE = 5
READ_TIMEOUT = 45


class RoomStream(object):
    """The room's live stream: the whole room on every change (event "room"). Reconnects with a
    growing pause; a room that's gone (404) or a sign-out (401/403) calls `on_gone` and stops.
    `wait(seconds)` returns True to stop; `stopped()` is checked between reads."""

    def __init__(self, api, room_id, on_room, on_gone, stopped, wait, clock=time.monotonic):
        self.api = api
        self.room_id = room_id
        self.on_room = on_room
        self.on_gone = on_gone
        self.stopped = stopped
        self.wait = wait
        self.clock = clock
        self.resp = None

    def abort(self):
        resp = self.resp
        if resp is None:
            return
        try:
            import socket
            resp.fp.raw._sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            resp.close()
        except Exception:
            pass

    def run(self):
        failures = 0
        while not self.stopped():
            try:
                resp = self.api.open_room_events(self.room_id, timeout=READ_TIMEOUT)
            except APIError as e:
                if e.status in (401, 403, 404):
                    self.on_gone(e.status)
                    return
                failures += 1
                delay = e.retry_after if e.status == 429 and e.retry_after else BACKOFF[min(failures - 1, len(BACKOFF) - 1)]
                if self.wait(delay):
                    return
                continue
            except Unreachable:
                failures += 1
                if self.wait(BACKOFF[min(failures - 1, len(BACKOFF) - 1)]):
                    return
                continue
            self.resp = resp
            opened = self.clock()
            try:
                self._read(resp)
                failures = 0 if self.clock() - opened >= MIN_LIFE else failures + 1
            except Exception as e:
                if not self.stopped():  # not one closed on purpose
                    log.debug("room stream dropped (%s)", type(e).__name__)
                failures += 1
            finally:
                self.resp = None
                try:
                    resp.close()
                except Exception:
                    pass
            if not self.stopped() and failures and self.wait(BACKOFF[min(failures - 1, len(BACKOFF) - 1)]):
                return

    def _read(self, resp):
        parser = SSEParser()
        while not self.stopped():
            line = resp.readline()
            if not line:
                return
            frame = parser.feed(line)
            if frame is None or frame[0] != "room":
                continue
            try:
                room = json.loads(frame[1])
            except ValueError:
                continue
            if isinstance(room, dict) and room.get("id"):
                self.on_room(room)
