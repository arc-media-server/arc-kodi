"""Playing a title. Kodi's own player (xbmc.Player) plays the stream; Arc's player dialog stays
over the video for the whole playback (controls, Skip Intro/Recap/Credits, Up Next). Progress goes
to Arc on the source file's timeline every 10 s and on pause/stop; conversions are pinged while
paused, deleted on stop; Kodi's own resume points are ignored (Arc's are the truth).

Seeking outside what a conversion has ready restarts playback at that source position with a fresh
offset, as the web player does.
"""

import threading
import time

import xbmc
import xbmcgui

from arc import models, playback

from .compat import T
from .caps import device_caps
from .log import log

REPORT_EVERY = 10.0


class ArcPlayer(xbmc.Player):
    def __init__(self, playback_session):
        xbmc.Player.__init__(self)
        self.pb = playback_session

    def onAVStarted(self):
        self.pb.on_started()

    def onPlayBackPaused(self):
        self.pb.on_pause(True)

    def onPlayBackResumed(self):
        self.pb.on_pause(False)

    def onPlayBackSeek(self, time_ms, offset):
        self.pb.on_seek(time_ms)

    def onPlayBackEnded(self):
        self.pb.on_ended(finished=True)

    def onPlayBackStopped(self):
        self.pb.on_ended(finished=False)

    def onPlayBackError(self):
        self.pb.on_error()


class Playback(object):
    """One title's playback: start, keep progress, handle markers and Up Next, clean up."""

    def __init__(self, session, item, resume_ms=0, on_finished=None):
        self.session = session
        self.api = session.api
        self.item = item
        self.item_id = item.get("id")
        self.resume_ms = resume_ms
        self.on_finished = on_finished
        self.caps = device_caps()
        self.plan = None
        self.player = ArcPlayer(self)
        self.monitor = xbmc.Monitor()
        self._stop = threading.Event()
        self._paused = False
        self._started = False
        self._switching = False  # a new stream is replacing this one: ignore the old one's end
        self.duration_ms = models.duration_ms(item)
        self.overlay = None
        self.next_item = None      # the episode after this one, for Up Next
        self._start_ms = resume_ms  # the source position the current plan was asked to start at

    # MARK: - start

    def start(self):
        if not self._request(self.resume_ms):
            return False
        self._open_player()
        threading.Thread(target=self._progress_loop, daemon=True).start()
        return True

    def _open_overlay(self):
        try:
            from .player_osd import PlayerOverlay
            self.overlay = PlayerOverlay(self)
            self.overlay.show()
        except Exception as e:
            log.warning("player overlay not shown (%s: %s)", type(e).__name__, e)
            self.overlay = None

    def skip_to(self, source_ms):
        """Skip to a marker's end (or any source position inside the current plan)."""
        if not playback.within_converted(self.plan, source_ms):
            self._restart_at(source_ms)
            return
        try:
            self.player.seekTime(playback.player_time_ms(self.plan, source_ms) / 1000.0)
        except Exception:
            pass

    def play_next_now(self):
        self._report("stopped")
        self._release_session()
        self._play_next()

    def _request(self, start_ms, failed_method=None):
        caps = playback.fallback_caps(self.caps, failed_method) if failed_method else self.caps
        self._start_ms = start_ms
        body = playback.playback_request(caps, start_ms=start_ms)
        try:
            plan = self.api.start_playback(self.item_id, body)
        except Exception as e:
            log.warning("playback request failed (%s)", type(e).__name__)
            self._fail()
            return False
        if not plan or not plan.get("url"):
            self._fail()
            return False
        self.plan = plan
        if plan.get("duration_ms"):
            self.duration_ms = plan["duration_ms"]
        log.info("playing a %s: %s", self.item.get("kind", "title"), plan.get("method"))
        return True

    def _play_url(self):
        """A cast link for the plan's stream, so Kodi's player fetches it without the token."""
        try:
            return self.api.cast_link(self.plan["url"])
        except Exception as e:
            log.warning("cast link failed (%s); using direct URL", type(e).__name__)
            return self.api.absolute(self.plan["url"])

    def _open_player(self):
        url = self._play_url()
        li = xbmcgui.ListItem(self.item.get("title", ""))
        # A converted stream already starts at the asked position; a file played as it is starts
        # at its beginning, so Kodi seeks to the resume point itself. Kodi's own resume points are
        # never used: Arc's are the truth.
        start_s = 0.0
        if self.plan.get("method") == "direct" and self._start_ms > 0:
            start_s = playback.player_time_ms(self.plan, self._start_ms) / 1000.0
        li.setProperty("StartOffset", "%.3f" % start_s)
        li.setContentLookup(False)
        if self.plan.get("hls"):
            li.setMimeType("application/vnd.apple.mpegurl")
        info = li.getVideoInfoTag()
        try:
            info.setTitle(self.item.get("title", ""))
            info.setPlot(self.item.get("overview") or "")
        except Exception:
            pass
        self.player.play(url, li)

    # MARK: - player callbacks

    def on_started(self):
        if self._started:
            return
        self._started = True
        self._switching = False
        log.debug("playback started (%s)", self.plan.get("method") if self.plan else "-")
        self._report("playing")
        if self.overlay is None:
            self._open_overlay()  # over the full-screen video, once it's showing
        if self.overlay:
            self.overlay.on_plan(self.plan)
        if models.is_episode(self.item) and self.next_item is None:
            threading.Thread(target=self._fetch_next, daemon=True).start()

    def _fetch_next(self):
        try:
            self.next_item = self.api.next_episode(self.item_id)
        except Exception as e:
            log.debug("next episode unknown (%s)", type(e).__name__)

    def on_pause(self, paused):
        self._paused = paused
        self._report("paused" if paused else "playing")

    def on_seek(self, player_time_ms):
        source_ms = playback.source_position_ms(self.plan, player_time_ms / 1000.0)
        if not playback.within_converted(self.plan, source_ms):
            log.info("seek outside the converted window; restarting at %d", source_ms)
            self._restart_at(source_ms)

    def on_ended(self, finished):
        if self._switching:
            return
        self._stop.set()
        self._report("stopped")
        self._release_session()
        if finished and self._should_play_next():
            self._play_next()
        else:
            self._close_overlay()
            if self.on_finished:
                self.on_finished()

    def on_error(self):
        method = self.plan.get("method") if self.plan else None
        if method in ("direct", "remux") and not self._stop.is_set():
            log.info("playback error on %s; trying again converted", method)
            self._restart_at(self._source_position(), failed_method="direct" if method == "direct" else "remux")
        else:
            self._fail()

    # MARK: - progress

    def _progress_loop(self):
        # One loop per playback: a newer loop (the next episode's) makes this one stop.
        self._loop_gen = getattr(self, "_loop_gen", 0) + 1
        gen = self._loop_gen
        last = 0.0
        while not self._stop.is_set() and gen == self._loop_gen:
            if self.monitor.waitForAbort(1):
                break
            if not self.player.isPlaying():
                continue
            if self._paused:
                self._ping()
                continue
            now = time.time()
            if now - last >= REPORT_EVERY:
                self._report("playing")
                last = now
            if self.overlay:
                try:
                    self.overlay.on_tick(self._source_position(), self.duration_ms, self.plan)
                except Exception as e:
                    log.warning("player overlay failed (%s: %s)", type(e).__name__, e)

    def _source_position(self):
        try:
            return playback.source_position_ms(self.plan, self.player.getTime())
        except Exception:
            return 0

    def _report(self, state, position=None):
        if not self.plan:
            return
        pos = position if position is not None else self._source_position()
        try:
            self.api.report_progress(self.item_id, pos, self.duration_ms, state)
        except Exception as e:
            # 403 means an admin ended this playback; stop quietly.
            log.debug("progress (%s) not saved: %s", state, type(e).__name__)

    def _ping(self):
        sid = self.plan.get("session_id") if self.plan else None
        if sid:
            try:
                self.api.ping_transcode(sid)
            except Exception:
                pass

    def _release_session(self):
        sid = self.plan.get("session_id") if self.plan else None
        if sid:
            self.api.stop_transcode(sid)

    # MARK: - restart / next

    def _restart_at(self, source_ms, failed_method=None):
        self._report("stopped")
        self._release_session()
        if self._request(source_ms, failed_method=failed_method):
            self._started = False
            self._switching = True
            self._open_player()

    def _should_play_next(self):
        return models.is_episode(self.item) and (self.session.prefs or {}).get("auto_play", True)

    def _play_next(self):
        nxt = self.next_item
        if nxt is None:
            try:
                nxt = self.api.next_episode(self.item_id)
            except Exception:
                nxt = None
        self.next_item = None
        if nxt and models.playable(nxt):
            self.item = nxt
            self.item_id = nxt.get("id")
            self.resume_ms = 0
            self.duration_ms = models.duration_ms(nxt)
            self._started = False
            self._stop.clear()
            if self._request(0):
                self._switching = True
                self._open_player()
                threading.Thread(target=self._progress_loop, daemon=True).start()
                return
        self._close_overlay()
        if self.on_finished:
            self.on_finished()

    def _fail(self):
        xbmcgui.Dialog().notification("Arc", T(30188))
        self._stop.set()
        self._close_overlay()
        if self.on_finished:
            self.on_finished()

    def _close_overlay(self):
        if self.overlay is not None:
            try:
                self.overlay.close()
            except Exception:
                pass
            self.overlay = None

    def stop(self):
        self._stop.set()
        if self.player.isPlaying():
            self.player.stop()
        self._close_overlay()
