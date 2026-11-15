"""Live updates: Arc's change hints (`GET /api/v1/events`, server docs/EVENTS-API.md), so open
screens refresh when something changes elsewhere: a title watched on another device, a scan that
added films, an edit in the web app.

The stream is Server-Sent Events. Each `invalidate` names a topic ("profile", "catalog", ...) and
maybe a library; `resync` means refetch everything. They're hints, not records: the app refetches
what it shows. Hints arriving close together are merged into one `Change` (`Gatherer`), as the server asks.

Plain Python: kodi/live.py runs `EventStream` on a thread and hands each Change to the open
window. Nothing here logs what changed beyond the topic names."""

import json
import logging
import time

from .api import APIError, Unreachable

log = logging.getLogger("arc")

# Topics that change what a profile sees. Others (sessions, activity, maintenance: admin; markers,
# previews, optimized: read when playback starts) need nothing redrawn.
PERSONAL = {"profile", "playback"}
CATALOG = {"catalog", "library", "artwork"}
WATCHED = PERSONAL | CATALOG

READ_TIMEOUT = 45          # seconds without a line (Arc sends a heartbeat every 10) = a dead stream
RECONNECT_AFTER = 30 * 60  # Arc asks streams to reconnect every 30 minutes
GATHER = 1.0               # seconds to wait for more hints before acting on them
BACKOFF = (2, 5, 10, 30, 60)
MIN_LIFE = 5               # seconds: a stream that ends sooner counts as a failure


class Change(object):
    """What changed, merged from one or more hints. `topics` are the hint topics; `library_ids`
    the libraries named (empty when a hint named none); `everything` after a resync."""

    def __init__(self):
        self.topics = set()
        self.library_ids = set()
        self.unscoped = False      # a catalog hint that named no library: any library may have changed
        self.everything = False

    def add(self, event, data):
        if event == "resync":
            self.everything = True
            return
        if event != "invalidate" or not isinstance(data, dict):
            return
        topic = data.get("topic")
        if not isinstance(topic, str) or not topic:
            return
        self.topics.add(topic)
        library_id = data.get("library_id")
        if isinstance(library_id, int) and not isinstance(library_id, bool) and library_id > 0:
            self.library_ids.add(library_id)
        elif topic in CATALOG:
            self.unscoped = True

    @property
    def empty(self):
        return not self.everything and not (self.topics & WATCHED)

    def personal(self):
        """Watched state, progress, the watchlist or the profile's settings may have changed."""
        return self.everything or bool(self.topics & PERSONAL)

    def catalog(self, library_id=None):
        """Titles may have changed (anywhere, or in `library_id`)."""
        if self.everything:
            return True
        if not self.topics & CATALOG:
            return False
        return library_id is None or self.unscoped or library_id in self.library_ids

    def libraries_changed(self):
        """The list of libraries itself may have changed (one added, renamed or reordered)."""
        return self.everything or "library" in self.topics and self.unscoped

    def touches(self, library_id=None):
        """Anything a page about `library_id` (or any page, for None) shows may have changed."""
        return self.personal() or self.catalog(library_id)

    def describe(self):
        return "everything" if self.everything else ", ".join(sorted(self.topics & WATCHED))


class Gatherer(object):
    """Merges changes arriving within GATHER seconds of the first, so a burst of hints (a scan,
    a season marked watched) refreshes a screen once."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.pending = None
        self.due = None

    def add(self, change):
        if self.pending is None:
            self.pending = Change()
            self.due = self.clock() + GATHER
        p = self.pending
        p.topics |= change.topics
        p.library_ids |= change.library_ids
        p.unscoped = p.unscoped or change.unscoped
        p.everything = p.everything or change.everything

    def take(self):
        """The merged change once it's due, else None."""
        if self.pending is None or self.clock() < self.due:
            return None
        change, self.pending, self.due = self.pending, None, None
        return change


class SSEParser(object):
    """Server-Sent Events, line by line: returns (event, data, id) when a frame ends."""

    def __init__(self):
        self.last_id = None
        self._reset()

    def _reset(self):
        self._event = ""
        self._data = []

    def feed(self, line):
        if isinstance(line, bytes):
            line = line.decode("utf-8", "replace")
        line = line.rstrip("\r\n")
        if not line:
            if not self._data and not self._event:
                return None
            frame = (self._event or "message", "\n".join(self._data), self.last_id)
            self._reset()
            return frame
        if line.startswith(":"):
            return None  # a comment: Arc's heartbeat
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            self._event = value
        elif field == "data":
            self._data.append(value)
        elif field == "id" and "\0" not in value:
            self.last_id = value
        return None


class EventStream(object):
    """Keeps one stream open: reads hints and calls `on_change(change)` for each that matters
    (merge them with a Gatherer). Reconnects with the last id after a drop (backing off), honours 429's
    Retry-After, and stops for good when signed out (401/403) or when `stopped()` is true.

    `clock` and `wait(seconds)` are injectable for tests; `wait` returns True to stop."""

    def __init__(self, api, on_change, stopped, wait, clock=time.monotonic):
        self.api = api
        self.on_change = on_change
        self.stopped = stopped
        self.wait = wait
        self.clock = clock
        self.parser = SSEParser()
        self.connections = 0
        self.resp = None

    def abort(self):
        """Ends a read waiting on Arc (from another thread), so the add-on can close at once."""
        resp = self.resp
        if resp is None:
            return
        try:
            import socket
            sock = resp.fp.raw._sock  # urllib's response: unblock its readline()
            sock.shutdown(socket.SHUT_RDWR)
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
                resp = self.api.open_events(self.parser.last_id, timeout=READ_TIMEOUT)
            except APIError as e:
                if e.status in (401, 403):
                    log.info("live updates stopped: signed out")
                    return
                delay = e.retry_after if e.status == 429 and e.retry_after else BACKOFF[min(failures, len(BACKOFF) - 1)]
                log.debug("live updates: %d, again in %ds", e.status, delay)
                failures += 1
                if self.wait(delay):
                    return
                continue
            except Unreachable:
                delay = BACKOFF[min(failures, len(BACKOFF) - 1)]
                failures += 1
                if self.wait(delay):
                    return
                continue
            self.resp = resp
            self.connections += 1
            if self.connections == 1:
                log.info("live updates connected")
            opened = self.clock()
            try:
                self._read(resp)
                # A stream Arc ends at once is a failure too (or the loop would spin).
                failures = 0 if self.clock() - opened >= MIN_LIFE else failures + 1
            except Exception as e:  # a dropped connection or a read timeout
                log.debug("live updates dropped (%s)", type(e).__name__)
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
        opened = self.clock()
        first = self.connections == 1
        while not self.stopped():
            line = resp.readline()
            if not line:
                break  # Arc closed the stream
            frame = self.parser.feed(line)
            if frame is not None:
                event, data, _ = frame
                if first and event == "resync":
                    # A new stream always starts with a resync; the app has just loaded.
                    first = False
                    continue
                first = False
                try:
                    payload = json.loads(data) if data else None
                except ValueError:
                    payload = None
                change = Change()
                change.add(event, payload)
                self._deliver(change)
            if self.clock() - opened >= RECONNECT_AFTER:
                break

    def _deliver(self, change):
        if change.empty:
            return
        log.debug("live update: %s", change.describe())
        self.on_change(change)
