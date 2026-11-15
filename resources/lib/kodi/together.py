"""Watch Together in Kodi, as the Apple app's WatchTogetherModel: the rooms on Home's row, the room
this device is in, its live stream, heartbeats and clock, and the commands the player sends. The
player (kodi/player.py) follows `room`: it plays the room's title from where the room is.

Threads: the room's stream, a heartbeat every two seconds and a clock check every minute run
while in a room; callers may be on any thread, so the room is swapped under a lock."""

import threading
import time

import xbmc
import xbmcgui

from arc import together as wt
from arc.api import APIError, RoomConflict, Unreachable

from .compat import T
from .log import log

HEARTBEAT = 2.0
CLOCK_EVERY = 60.0


class Together(object):
    def __init__(self, session):
        self.session = session
        self.rooms = []          # the profile's listed rooms (Home's row)
        self.room = None         # the room this device is in, as of Arc's latest word
        self.code = None         # the code for a room this device made with one
        self.code_room = None
        self.offset_ms = 0.0     # how far the server's clock is ahead of this one
        self.open_player = None  # the app's: open_player(item, start_ms)
        self.player = None       # the Playback following the room, while there is one
        self.notify = None       # the player window's notice, while it's open
        self.invite_more = None  # the app's: invite_more(item), choosing people for this room
        self._lock = threading.Lock()
        self._stop = None
        self._stream = None
        self._switching = False  # opening the room's (new) title: the old playback's end isn't a leave

    @property
    def api(self):
        return self.session.api

    @property
    def available(self):
        return bool(((self.session.features or {}).get("watch_together") or {}).get("allowed"))

    # MARK: - the rooms list

    def refresh_rooms(self):
        try:
            self.rooms = self.api.watch_rooms()
        except APIError as e:
            if e.status != 404:
                log.debug("Watch Together rooms unavailable (%d)", e.status)
            self.rooms = []
        except Unreachable:
            pass
        return self.rooms

    def create_room(self, item_id, people):
        """A room for the chosen people; it waits on their Home rows (and this one's)."""
        made = self.api.create_invited_room(item_id, people)
        log.info("Watch Together room made for %d people", len(people))
        self.refresh_rooms()
        return made

    def start_with_code(self, item_id):
        """A room with a code, joined at once (Use a Code Instead)."""
        made = self.api.create_room(item_id)
        self.code = wt.format_code(made.get("invite_code"))
        self.code_room = (made.get("room") or {}).get("id")
        log.info("Watch Together room made with a code")
        self.begin(made.get("room") or {})

    def accept(self, listed):
        self.begin(self.api.accept_room(listed.get("id")))

    def join(self, code):
        self.begin(self.api.join_room(wt.normalise_code(code)))

    def dismiss(self, listed):
        try:
            self.api.dismiss_room(listed.get("id"))
        except Exception as e:
            log.debug("dismissing a room failed (%s)", type(e).__name__)
        self.refresh_rooms()

    def invite(self, people):
        room = self.room
        if room:
            self.adopt(self.api.invite_people(room["id"], people))

    def lobby_code(self):
        room = self.room
        return self.code if room and room.get("id") == self.code_room else None

    # MARK: - being in a room

    def begin(self, room):
        self._end_threads()
        with self._lock:
            self.room = room
        log.info("joined a Watch Together room (%d here)", len(room.get("participants") or []))
        stop = threading.Event()
        self._stop = stop
        monitor = xbmc.Monitor()

        def wait(seconds):
            return stop.wait(seconds) or monitor.abortRequested()

        self._stream = wt.RoomStream(self.api, room["id"], self.adopt, self._stream_gone,
                                     stopped=lambda: stop.is_set() or monitor.abortRequested(), wait=wait)
        for target in (self._stream.run, lambda: self._beat(stop, wait), lambda: self._clock(stop, wait)):
            threading.Thread(target=target, daemon=True).start()
        self.open_title()

    def open_title(self):
        """Plays the room's title from where the room is (joining, or the room changed title)."""
        room = self.room
        if not room or not room.get("available") or not room.get("item_id") or not self.open_player:
            if room and not room.get("available"):
                self.say(T(30347))
            return
        try:
            item = self.api.item(room["item_id"])
        except Exception as e:
            log.warning("the room's title didn't load (%s)", type(e).__name__)
            return
        self._switching = True
        try:
            self.open_player(item, int(self.expected_ms()))
        finally:
            self._switching = False

    def leave(self):
        room = self.room
        if not room:
            return
        self._end_threads()
        with self._lock:
            self.room = None
        threading.Thread(target=lambda: (self.api.leave_room(room["id"]), self.refresh_rooms()), daemon=True).start()
        log.info("left the Watch Together room")

    def end(self):
        self.command("end")

    def player_closed(self, pb, finished):
        """The room's player closed (the viewer stopped it, or the room's title ended and no next
        one came): this device leaves the room; the others carry on."""
        if self._switching or self.room is None or pb is not self.player:
            return
        self.player = None
        self.leave()

    def _end_threads(self):
        if self._stop is not None:
            self._stop.set()
        if self._stream is not None:
            self._stream.abort()
        self._stop = None
        self._stream = None

    def _stream_gone(self, status):
        if status == 404:
            self._gone(T(30348))

    def _gone(self, text):
        self._end_threads()
        with self._lock:
            self.room = None
        self.say(text)
        self.refresh_rooms()

    # MARK: - the clock and where the room is

    def server_now_ms(self):
        return time.time() * 1000 + self.offset_ms

    def expected_ms(self):
        room = self.room
        return wt.expected_position(room, self.server_now_ms()) if room else 0

    def _clock(self, stop, wait):
        while not stop.is_set():
            samples = []
            for _ in range(3):
                c0 = int(time.time() * 1000)
                try:
                    t = self.api.server_time(c0)
                except Exception:
                    break
                samples.append((c0, int(time.time() * 1000), t.get("server_received_ms") or 0,
                                t.get("server_sent_ms") or 0))
            offset = wt.clock_offset(samples)
            if offset is not None:
                self.offset_ms = offset
            if wait(CLOCK_EVERY):
                return

    # MARK: - commands and heartbeats

    def play(self):
        self.command("play")

    def pause(self):
        self.command("pause")

    def seek(self, ms):
        self.command("seek", position_ms=max(0, int(ms)))

    def command(self, action, position_ms=None, item_id=None):
        """Sends a command off the UI thread with the room's revision; if the room changed
        meanwhile, adopts it and tries once more."""
        def run():
            current = self.room
            if not current:
                return
            try:
                self.adopt(self.api.room_command(current["id"], current.get("revision") or 0, action,
                                                 position_ms=position_ms, item_id=item_id))
                log.debug("room command %s", action)
            except RoomConflict as c:
                self.adopt(c.room)
                again = self.room
                if not again:
                    return
                try:
                    self.adopt(self.api.room_command(again["id"], again.get("revision") or 0, action,
                                                     position_ms=position_ms, item_id=item_id))
                except Exception as e:
                    log.debug("room command %s refused again (%s)", action, type(e).__name__)
            except APIError as e:
                if e.status == 404:
                    self._gone(T(30348))
                else:
                    log.warning("room command %s failed (%d)", action, e.status)
            except Exception as e:
                log.warning("room command %s failed (%s)", action, type(e).__name__)

        threading.Thread(target=run, daemon=True).start()

    def _beat(self, stop, wait):
        while not wait(HEARTBEAT):
            current, pb = self.room, self.player
            if not current or pb is None:
                continue
            report = pb.room_report()
            if report is None:
                continue
            position, state, ready = report
            try:
                self.adopt(self.api.room_heartbeat(current["id"], current.get("generation") or 0, position, state,
                                                   ready and state != "waiting"))
            except RoomConflict as c:
                self.adopt(c.room)  # a seek or a new title: report against it next time
            except APIError as e:
                if e.status == 404:
                    self._gone(T(30348))
                    return
            except Exception:
                pass  # offline a moment: the next beat tries again

    # MARK: - the room changing

    def adopt(self, next_room):
        """Takes a room from Arc if it's at least as new as the one held, and acts on what
        changed: the room ended, moved to another title, or someone paused or played it."""
        if not isinstance(next_room, dict) or not next_room.get("id"):
            return
        with self._lock:
            current = self.room
            if current is None or not wt.should_adopt(next_room, current):
                return
            self.room = next_room
        if next_room.get("state") == "ended":
            log.info("the Watch Together room ended")
            self._gone(T(30349))
            return
        if next_room.get("item_id") and next_room.get("item_id") != current.get("item_id"):
            pb = self.player
            if pb is not None and not pb.done:
                # The room's player plays the new title itself (Kodi sends a player's events only
                # to the thread that made it, so a new player can't be made here).
                threading.Thread(target=pb.follow_room_title,
                                 args=(next_room["item_id"], int(self.expected_ms())), daemon=True).start()
            else:
                log.info("the room moved on to another title; join it again from Home to follow")
        said = wt.notice(next_room, current)
        if said:
            words = {"paused_by": 30350, "played_by": 30351, "moved_by": 30352}
            self.say(T(words[said[0]]) % said[1])
        pb = self.player
        if pb is not None:
            pb.room_changed(next_room)

    def say(self, text):
        """A short note: in the player's capsule while it's open, else Kodi's notification."""
        notify = self.notify
        if notify is not None:
            try:
                notify(text)
                return
            except Exception:
                pass
        xbmcgui.Dialog().notification(T(30330), text, sound=False)
