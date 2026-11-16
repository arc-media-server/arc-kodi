"""Playing a title. Kodi's own player (xbmc.Player) decodes and shows the stream; Arc's player
window (kodi/player_osd.py) stays over the video for the whole playback and owns the remote, as
PM4K's does: its controls, seeking, Skip Intro/Recap/Credits, Up Next, audio and subtitles.

Progress goes to Arc on the source file's timeline every 10 s and on pause/stop; conversions are
pinged while paused and deleted on stop; Kodi's own resume points are ignored (Arc's are the
truth). A seek outside what a conversion has ready restarts it at that source position with a
fresh offset, as the web player does. Audio and picture-subtitle changes on a converted stream
ask Arc again (the conversion carries one audio track); on a file played as it is, Kodi switches
its own tracks.

In a Watch Together room (`together`, kodi/together.py) the room decides where and whether it
plays: the viewer's pause, play and seeks go to the room as commands, a follower keeps Kodi in
step with the room (playing, pausing, jumping), and the player reports itself every two seconds.
"""

import threading
import time

import xbmc
import xbmcgui

from arc import models, playback, titlepage
from arc import together as wt

from . import storage
from .compat import T
from .caps import device_caps
from .log import log

REPORT_EVERY = 10.0
FOLLOW_EVERY = 0.5        # seconds between looks at where the room is
ROOM_GRACE = 15.0         # seconds a room's player waits, at its title's end, for the room's next one
OWN_TOGGLE = 3.0          # seconds in which a pause or play Kodi reports is the follower's own


class ArcPlayer(xbmc.Player):
    """Kodi's player events for one Playback. Kodi sends every event to every xbmc.Player the
    add-on has made, so once its playback has finished this one passes nothing on (an earlier
    title's playback would otherwise act on the next one's end: advance its old queue, play an
    episode after it, report progress again)."""

    def __init__(self, playback_session):
        xbmc.Player.__init__(self)
        self.pb = playback_session

    def _live(self):
        return not self.pb.done

    def onAVStarted(self):
        if self._live():
            self.pb.on_started()

    def onPlayBackPaused(self):
        if self._live():
            self.pb.on_pause(True)

    def onPlayBackResumed(self):
        if self._live():
            self.pb.on_pause(False)

    def onPlayBackEnded(self):
        if self._live():
            self.pb.on_ended(finished=True)

    def onPlayBackStopped(self):
        if self._live():
            self.pb.on_ended(finished=False)

    def onPlayBackError(self):
        if self._live():
            self.pb.on_error()


class Playback(object):
    """One title's playback: start, keep progress, the choices made in the player, clean up."""

    def __init__(self, session, item, resume_ms=0, on_finished=None, queue=None, together=None):
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
        self.paused = False
        self._started = False
        self._switching = False  # a new stream is replacing this one: ignore the old one's end
        self.duration_ms = models.duration_ms(item)
        self.controls = None
        self.next_item = None      # the episode after this one, for Up Next
        self.queue = queue         # an arc.queues.PlayQueue (Play All, Shuffle): it says what's next
        self.done = False          # finished: Kodi's later events are for another playback
        self.thumbs = None         # the playing file's timeline thumbnails: {file, interval_ms, count}
        self.season_episodes = []  # an episode's season, for the player's Episodes list
        self.season_unplaced = False  # ...or the episodes outside the show's order
        self._start_ms = resume_ms  # the source position the current plan was asked to start at
        self._last_ms = None        # where Kodi last said it was playing (source timeline)
        # The viewer's choices, sent with every request to Arc (a restart keeps them).
        self.file_id = None
        self.audio_index = None    # Arc's stream index of the chosen audio track
        self.max_kbps = None       # a quality limit; None for the original
        self.burn_subtitle = None  # a picture subtitle Arc draws into a converted picture
        self.subtitle = None       # the subtitle track showing (a plan track), or None for Off
        self._subtitle_chosen = False  # the viewer chose (so a restart re-applies, not re-guesses)
        self._kodi_audio = None    # the profile's audio track, switched to by Kodi once playing
        self._early_ends = 0       # converted streams that ended before the title's end (retried)
        # Watch Together: the room this playback follows (kodi/together.py), or None.
        self.together = together
        self.follower = wt.Follower()
        self._own_toggle = None    # (paused, at): a pause/play the follower asked Kodi for
        self._ended_naturally = False
        self.subtitle_offset_ms = 0   # this title's subtitle offset, kept across a restart
        if together is not None:
            together.player = self

    # MARK: - start

    def start(self):
        if not self._request(self.resume_ms):
            return False
        self._open_player()
        threading.Thread(target=self._progress_loop, daemon=True).start()
        if self.together is not None:
            threading.Thread(target=self._follow_loop, daemon=True).start()
        return True

    def _choose_start_audio(self, caps, start_ms):
        """Before the first request: if Arc would convert only because the profile's audio
        language picks a track other than the file's default, play the file as it is with the
        default track and have Kodi switch to the preferred one (self._kodi_audio)."""
        self._kodi_audio = None
        try:
            preview = self.api.playback_preview(self.item_id, playback.playback_request(
                caps, start_ms=start_ms, file_id=self.file_id, max_kbps=self.max_kbps))
            if not playback.needs_default_audio_try(preview):
                return
            default = playback.default_audio_index(preview)
            again = self.api.playback_preview(self.item_id, playback.playback_request(
                caps, start_ms=start_ms, file_id=self.file_id, audio_stream=default, max_kbps=self.max_kbps))
            if (again or {}).get("method") == "direct":
                self.audio_index = default
                self._kodi_audio = preview.get("audio_stream")
                log.debug("playing the file as it is; Kodi switches to the preferred audio")
        except Exception as e:
            log.debug("playback preview failed (%s)", type(e).__name__)

    def _request(self, start_ms, failed_method=None):
        caps = playback.fallback_caps(self.caps, failed_method) if failed_method else self.caps
        self._start_ms = start_ms
        self._last_ms = start_ms
        if self.audio_index is None and not failed_method and not self.burn_subtitle:
            self._choose_start_audio(caps, start_ms)
        body = playback.playback_request(caps, start_ms=start_ms, file_id=self.file_id,
                                         audio_stream=self.audio_index, max_kbps=self.max_kbps,
                                         burn_subtitle=self.burn_subtitle)
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
        if plan.get("file_id"):
            self.file_id = plan["file_id"]
            self._fetch_thumbs(plan["file_id"])
        if self.audio_index is None and (plan.get("audio_stream") or -1) >= 0:
            self.audio_index = plan["audio_stream"]
        log.info("playing %s: %s", self.item.get("kind", "title"), plan.get("method"))
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
        try:
            info = li.getVideoInfoTag()
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
        self.paused = False
        log.debug("playback started (%s)", self.plan.get("method") if self.plan else "-")
        self._report("playing")
        if self._kodi_audio is not None and self.plan.get("method") == "direct":
            k = playback.kodi_audio_index(self.plan, self._kodi_audio)
            if k is not None:
                self.player.setAudioStream(k)
                self.audio_index = self._kodi_audio
            self._kodi_audio = None
        self._settle_subtitles()
        self._apply_offsets()
        if self.controls is None:
            self._open_controls()  # over the full-screen video, once it's showing
        if self.controls:
            self.controls.on_plan(self.plan)
        if self.queue is not None:
            self.next_item = self.queue.peek_next()
            if models.is_episode(self.item) and not self.season_episodes:
                threading.Thread(target=self._fetch_season, daemon=True).start()
        elif models.is_episode(self.item) and self.next_item is None:
            threading.Thread(target=self._fetch_next, daemon=True).start()

    def _open_controls(self):
        try:
            from .player_osd import PlayerControls
            self.controls = PlayerControls(self)
            # Modal, so no key falls through to Kodi's own full-screen player (its seeking, its
            # OSD, Back leaving the video): this window has the remote. Kodi still pauses and
            # stops by itself for Play/Pause and Stop. doModal blocks, so it runs on its own thread.
            threading.Thread(target=self.controls.doModal, name="arc-player", daemon=True).start()
        except Exception as e:
            log.warning("player controls not shown (%s: %s)", type(e).__name__, e)
            self.controls = None

    # MARK: - audio and subtitle offsets

    @staticmethod
    def offset_ms(kind):
        """Kodi's audio or subtitle delay now, in ms (positive: later than the picture)."""
        return playback.delay_ms(xbmc.getInfoLabel("Player.AudioDelay" if kind == "audio" else "Player.SubtitleDelay"))

    def set_offset(self, kind, target_ms, remember=True):
        """Moves Kodi's audio or subtitle delay to `target_ms`, a step at a time (Kodi has no call to
        set it). The audio offset is this device's (a TV and its soundbar), so it's kept for every
        title; a subtitle offset belongs to the title playing."""
        audio = kind == "audio"
        n = playback.delay_steps(self.offset_ms(kind), target_ms,
                                 playback.AUDIO_STEP_MS if audio else playback.SUBTITLE_STEP_MS)
        action = ("AudioDelay" if audio else "SubtitleDelay") + ("Plus" if n > 0 else "Minus")
        for _ in range(abs(n)):
            xbmc.executebuiltin("Action(%s)" % action)
        if n:
            # Kodi shows its own delay slider for these steps; Arc's menu already says the offset.
            xbmc.executebuiltin("Dialog.Close(sliderdialog,true)")
        if remember:
            if audio:
                storage.update(audio_offset_ms=int(target_ms))
            else:
                self.subtitle_offset_ms = int(target_ms)
            log.info("%s offset changed", kind)
            log.debug("%s offset: %d ms", kind, target_ms)

    def _apply_offsets(self):
        """A new stream starts with Kodi's default delays: put back this device's audio offset and
        the title's subtitle offset (after a restart)."""
        try:
            audio = int(storage.load().get("audio_offset_ms") or 0)
        except (TypeError, ValueError):
            audio = 0
        if audio and self.offset_ms("audio") != audio:
            self.set_offset("audio", audio, remember=False)
            log.debug("audio offset applied: %d ms", audio)
        if self.subtitle_offset_ms and self.offset_ms("subtitles") != self.subtitle_offset_ms:
            self.set_offset("subtitles", self.subtitle_offset_ms, remember=False)

    def _fetch_thumbs(self, file_id):
        """Asks Arc for the file's timeline thumbnails, once per file, off the player's thread."""
        if self.thumbs and self.thumbs.get("file") == file_id:
            return

        def run():
            try:
                tp = self.api.trickplay(self.item_id, file_id)
            except Exception as e:
                log.debug("timeline thumbnails unknown (%s)", type(e).__name__)
                return
            info = (tp or {}).get("info") or {}
            if tp and tp.get("bif") and info.get("interval_ms") and info.get("count"):
                self.thumbs = {"file": file_id, "interval_ms": int(info["interval_ms"]), "count": int(info["count"])}
            else:
                self.thumbs = None

        threading.Thread(target=run, daemon=True).start()

    # MARK: - speed (Kodi's tempo)

    @staticmethod
    def speed_available():
        """Whether Kodi can change the speed now: it does it through its audio, so not with
        passthrough, without an audio device, or with "sync playback to display"."""
        return bool(xbmc.getCondVisibility("Player.TempoEnabled"))

    @staticmethod
    def speed():
        try:
            return float(xbmc.getInfoLabel("Player.PlaySpeed") or 1.0)
        except ValueError:
            return 1.0

    def set_speed(self, target):
        """Steps Kodi's tempo to `target` (0.1 a step), checking where it got to after each."""
        for _ in range(10):
            steps = playback.speed_steps(self.speed(), target)
            if steps == 0:
                break
            before = self.speed()
            xbmc.executebuiltin("PlayerControl(TempoUp)" if steps > 0 else "PlayerControl(TempoDown)")
            xbmc.sleep(150)
            if self.speed() == before:
                log.info("speed stayed at %.1f (Kodi didn't change its tempo)", before)
                break
        log.debug("speed now %.1f", self.speed())

    def thumb_url(self, position_ms):
        """A local URL of the timeline thumbnail at `position_ms`, or None."""
        t = self.thumbs
        if not t:
            return None
        index = min(t["count"] - 1, max(0, int(position_ms // t["interval_ms"])))
        return self.session.artwork.bif_url(self.item_id, t["file"], index)

    def _fetch_next(self):
        try:
            self.next_item = self.api.next_episode(self.item_id)
        except Exception as e:
            log.debug("next episode unknown (%s)", type(e).__name__)
        self._fetch_season()

    def _fetch_season(self):
        """This episode's season (for the player's Episodes list), from its show's seasons."""
        show = self.item.get("parent_id")
        if not show:
            return
        try:
            data = self.api.seasons(show) or {}
        except Exception as e:
            log.debug("season unknown (%s)", type(e).__name__)
            return
        for season in titlepage.season_tabs(data)[1]:
            episodes = season.get("episodes") or []
            if any(e.get("id") == self.item_id for e in episodes):
                self.season_unplaced = bool(season.get("unplaced"))  # Not in This Order
                self.season_episodes = episodes
                return

    def on_pause(self, paused):
        self.paused = paused
        self._report("paused" if paused else "playing")
        # In a room, the viewer's pause or play goes to the room; Kodi's own events while a
        # stream starts or is replaced aren't the viewer's.
        if self.in_room() and self._started and not self._switching:
            own = self._own_toggle
            if own and own[0] == paused and time.time() - own[1] < OWN_TOGGLE:
                self._own_toggle = None   # the follower's own: not the viewer's
                return
            # The viewer paused or played (Kodi does Play/Pause itself): the room follows.
            if paused:
                self.together.pause()
            else:
                self.together.play()

    def on_ended(self, finished):
        if self._switching:
            return
        position = self.position_ms()
        if finished and playback.converted(self.plan) and self.duration_ms > 0 \
                and position < self.duration_ms - 30000 and self._early_ends < 3:
            self._early_ends += 1
            # Kodi reached the end of what was converted before the title's end (a slow
            # conversion, a dropped connection): carry on from there rather than finishing.
            log.warning("converted stream ended early; starting again from there")
            self._restart_at(position)
            return
        self._stop.set()
        self._report("stopped")
        self._release_session()
        self._ended_naturally = finished
        if finished and self.in_room():
            self._room_title_ended()
        elif finished and self._should_play_next():
            self._play_next()
        else:
            self._finish()

    def on_error(self):
        method = self.plan.get("method") if self.plan else None
        if method in ("direct", "remux") and not self._stop.is_set():
            log.info("playback error on %s; trying again converted", method)
            self._restart_at(self.position_ms(), failed_method="direct" if method == "direct" else "remux")
        else:
            self._fail()

    # MARK: - where it is

    def position_ms(self):
        """Where it's playing, on the source file's timeline. Once Kodi has stopped it can't say,
        so the last place it said is kept (that's what Stop saves as the resume point)."""
        try:
            # While stopping Kodi still says it's playing but at 0:00: keep what it last said.
            if self.player.isPlaying() and self._started and not self._stop.is_set():
                t = self.player.getTime()
                if t > 0 or not self._last_ms:
                    self._last_ms = playback.source_position_ms(self.plan, t)
        except Exception:
            pass
        return self._last_ms if self._last_ms is not None else self._start_ms

    def _converted_end_ms(self):
        """How far a converted stream is ready, on the source timeline (Kodi sees the growing
        playlist's length)."""
        try:
            return (self.plan.get("offset_ms") or 0) + int(self.player.getTotalTime() * 1000)
        except Exception:
            return 0

    # MARK: - what the controls ask for

    def toggle_pause(self):
        self.player.pause()

    def seek_to(self, source_ms, from_room=False):
        """Seeks to a source position: within the file (or what's converted) Kodi seeks itself;
        outside a conversion's ready part Arc starts converting from there. In a room the
        viewer's seek takes the room there too (`from_room`: the follower's own)."""
        source_ms = playback.clamp_seek(source_ms, self.duration_ms)
        if not from_room and self.in_room():
            self.follower.settle(time.time() * 1000)
            self.together.seek(source_ms)
        if not self._started or not self.player.isPlaying():
            return  # between streams, or already over
        if playback.converted(self.plan):
            offset = self.plan.get("offset_ms") or 0
            if not (offset <= source_ms <= self._converted_end_ms() - 2000):
                log.info("seek outside the converted part; starting again there")
                self._restart_at(source_ms)
                return
        try:
            self.player.seekTime(playback.player_time_ms(self.plan, source_ms) / 1000.0)
        except Exception as e:
            log.debug("seek failed (%s)", type(e).__name__)

    def skip_to(self, source_ms):
        """Skip Intro/Recap/Credits: to a marker's end."""
        self.seek_to(source_ms)

    def play_next_now(self):
        if self.in_room():
            # The room moves on, and every player in it follows (this one included).
            if self.next_item:
                log.info("moving the room to the next episode")
                self.together.command("change_item", position_ms=0, item_id=self.next_item.get("id"))
            return
        self._stop.set()
        self._report("stopped")
        self._release_session()
        self._play_next()

    def choose_audio(self, track):
        index = track.get("index")
        if index == self.audio_index:
            return
        self.audio_index = index
        self._remember({"audio_language": track.get("language") or ""})
        if playback.converted(self.plan):
            self._restart_at(self.position_ms())  # a conversion carries just one audio track
            return
        k = playback.kodi_audio_index(self.plan, index)
        if k is not None:
            self.player.setAudioStream(k)

    def choose_subtitle(self, track, remember=True):
        """Shows a subtitle track (a plan track), or none."""
        self._subtitle_chosen = True
        self.subtitle = track
        if remember:
            mode = (self.session.prefs or {}).get("subtitle_mode") or ""
            lang = playback.remembered_subtitle_language(track, mode)
            if lang is not None:
                self._remember({"subtitle_language": lang})
        burn = track.get("id") if track and track.get("image") and playback.converted(self.plan) else None
        if burn != self.burn_subtitle:
            # Picture subtitles in a converted stream are drawn in by Arc: ask again.
            self.burn_subtitle = burn
            self._restart_at(self.position_ms())
            return
        self._show_subtitle(track)

    def _show_subtitle(self, track):
        try:
            if track is None or track.get("id") == self.burn_subtitle:
                self.player.showSubtitles(False)
                return
            k = None if playback.converted(self.plan) else playback.kodi_subtitle_index(self.plan, track.get("id"))
            if k is not None:
                self.player.setSubtitleStream(k)  # inside the file Kodi is playing
                self.player.showSubtitles(True)
                return
            # External, or a converted stream (which carries no text tracks): Arc's WebVTT, on
            # the stream's clock, through a cast link (Kodi fetches it without the token).
            path = playback.subtitle_vtt_path(self.item_id, track.get("id"), self.file_id,
                                              self.plan.get("offset_ms") or 0)
            self.player.setSubtitles(self.api.cast_link(path))
            self.player.showSubtitles(True)
        except Exception as e:
            log.warning("subtitles not shown (%s)", type(e).__name__)

    def _settle_subtitles(self):
        """At the start (and after a restart) shows the chosen subtitles, or the ones the
        profile's settings choose (Plex's modes), so Kodi's own choice never applies."""
        tracks = (self.plan or {}).get("subtitle_tracks") or []
        if not self._subtitle_chosen:
            prefs = self.session.prefs or {}
            audio = next((t for t in playback.audio_tracks(self.plan) if t.get("index") == self.audio_index), None)
            self.subtitle = playback.choose_subtitle(tracks, prefs.get("subtitle_language") or "",
                                                     (audio or {}).get("language"), prefs.get("subtitle_mode") or "")
        if self.subtitle and self.subtitle.get("image") and playback.converted(self.plan) \
                and self.burn_subtitle != self.subtitle.get("id"):
            self.subtitle = None  # a picture track can't be added afterwards; the viewer can choose it
        self._show_subtitle(self.subtitle)

    def choose_quality(self, kbps):
        if kbps == self.max_kbps:
            return
        self.max_kbps = kbps
        self._restart_at(self.position_ms())

    def choose_version(self, file_id):
        if file_id == self.file_id:
            return
        self.file_id = file_id
        self.audio_index = None
        self._restart_at(self.position_ms())

    def _remember(self, prefs):
        """Saves a choice as the profile's (as the other apps do), off the player's thread."""
        def work():
            try:
                self.session.prefs = self.api.patch_prefs(prefs) or self.session.prefs
            except Exception as e:
                log.debug("choice not saved (%s)", type(e).__name__)

        threading.Thread(target=work, daemon=True).start()

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
            if self.paused:
                self._ping()
                continue
            now = time.time()
            if now - last >= REPORT_EVERY:
                self._report("playing")
                last = now

    def _report(self, state, position=None):
        if not self.plan:
            return
        pos = position if position is not None else self.position_ms()
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
        self._report("stopped", position=source_ms)
        self._release_session()
        if self._request(source_ms, failed_method=failed_method):
            self._started = False
            self._switching = True
            self._open_player()

    def _should_play_next(self):
        auto = (self.session.prefs or {}).get("auto_play", True)
        if self.queue is not None:
            return auto and self.queue.peek_next() is not None
        return models.is_episode(self.item) and auto

    def _play_next(self):
        nxt = self.next_item
        if self.queue is not None:
            try:
                nxt = self.queue.advance()   # the queue moves on with the player
            except Exception as e:
                log.warning("play queue didn't advance: %s", type(e).__name__)
                nxt = None
        elif nxt is None:
            try:
                nxt = self.api.next_episode(self.item_id)
            except Exception:
                nxt = None
        self.next_item = None
        if not self._switch_to(nxt):
            self._finish()

    def play_episode(self, episode):
        """Plays another episode in place of this one (the player's Episodes list)."""
        if not episode or episode.get("id") == self.item_id:
            return
        if self.in_room():
            self.together.command("change_item", position_ms=0, item_id=episode.get("id"))
            return
        # A season list's episodes don't carry their show's name and pictures: they're this one's.
        episode = dict(episode)
        for key in ("series_title", "parent_id", "library_id"):
            if not episode.get(key) and self.item.get(key):
                episode[key] = self.item[key]
        images = {k: v for k, v in models.images(self.item).items() if k.startswith("series_")}
        images.update(models.images(episode))
        episode["images"] = images
        self._stop.set()
        self._report("stopped")
        self._release_session()
        self.next_item = None
        if not self._switch_to(episode, models.resume_ms(episode)):
            self._finish()

    def _switch_to(self, nxt, resume_ms=0):
        """Plays `nxt` in this playback (the same player window), from `resume_ms`; False if it
        can't."""
        if nxt and models.playable(nxt):
            self.item = nxt
            self.item_id = nxt.get("id")
            self.resume_ms = resume_ms
            self.thumbs = None
            self.season_episodes = []
            self.season_unplaced = False
            self.duration_ms = models.duration_ms(nxt)
            self.file_id = None
            self.audio_index = None
            self.burn_subtitle = None
            self._subtitle_chosen = False
            self.subtitle_offset_ms = 0
            self._started = False
            self._stop.clear()
            if self._request(resume_ms):
                self._switching = True
                self._open_player()
                threading.Thread(target=self._progress_loop, daemon=True).start()
                return True
        return False

    def _fail(self):
        xbmcgui.Dialog().notification("Arc", T(30188))
        self._stop.set()
        self._finish()

    def _finish(self):
        self.done = True
        if self.controls is not None:
            try:
                self.controls.finish()
            except Exception:
                pass
            self.controls = None
        if self.on_finished:
            self.on_finished()
        if self.together is not None:
            self.together.player_closed(self, self._ended_naturally)

    # MARK: - Watch Together

    def in_room(self):
        """Following a room that's playing this title."""
        room = self.together.room if self.together is not None else None
        return bool(room) and room.get("item_id") == self.item_id

    def room_host(self):
        return self.in_room() and wt.is_host(self.together.room)

    def room_report(self):
        """(file position, playing | paused | waiting, ready) for the room's heartbeat."""
        if not self.in_room():
            return None
        position = self.position_ms()
        buffering = xbmc.getCondVisibility("Player.Caching")
        if not self._started or self._switching or buffering:
            return position, "waiting", False
        return position, "paused" if self.paused else "playing", True

    def _room_title_ended(self):
        """The room's title ended here. The host's player moves the room on to the next episode;
        every player waits a moment for the room's next title (follow_room_title), then closes,
        leaving the room."""
        nxt = self.next_item
        auto = (self.session.prefs or {}).get("auto_play", True) is not False
        if self.room_host() and nxt and auto:
            log.info("moving the room to the next episode")
            self.together.command("change_item", position_ms=0, item_id=nxt.get("id"))
        item_id = self.item_id

        def wait():
            if self.monitor.waitForAbort(ROOM_GRACE):
                return
            if self.item_id == item_id and not self.done:
                self._finish()

        threading.Thread(target=wait, daemon=True).start()

    def follow_room_title(self, item_id, start_ms):
        """The room moved to another title: play it in this playback (the same player and window;
        a player made on another thread would never hear Kodi's events)."""
        if item_id == self.item_id or self.done:
            return
        try:
            item = self.api.item(item_id)
        except Exception as e:
            log.warning("the room's title didn't load (%s)", type(e).__name__)
            return
        log.info("following the room to another title")
        if not self._stop.is_set():
            self._stop.set()
            self._report("stopped")
            self._release_session()
        self.next_item = None
        if not self._switch_to(item, start_ms):
            self._finish()

    def room_changed(self, room):
        if self.controls is not None:
            self.controls.on_room(room)

    def _follow_loop(self):
        """Keeps Kodi in step with the room: plays and pauses with it, and jumps when it's too far
        out (Kodi can't play a little faster or slower in small enough steps to catch up)."""
        while not self.done and not self.monitor.waitForAbort(FOLLOW_EVERY):
            room = self.together.room if self.together is not None else None
            if not room or room.get("item_id") != self.item_id or not room.get("available"):
                continue
            if not self._started or self._switching or self._stop.is_set():
                continue
            for action in self.follower.step(room, self.position_ms(), not self.paused, time.time() * 1000,
                                             self.together.expected_ms()):
                if action[0] in ("play", "pause"):
                    want_paused = action[0] == "pause"
                    if want_paused != self.paused:
                        self._own_toggle = (want_paused, time.time())
                        self.player.pause()  # Kodi's pause toggles
                elif action[0] == "seek":
                    log.debug("catching up with the room")
                    self.seek_to(action[1], from_room=True)

    def stop(self):
        """Stops playing (the controls' Stop and Back); on_ended then reports and cleans up."""
        self.position_ms()  # where it was, before Kodi starts stopping
        self._stop.set()
        if self.player.isPlaying():
            self.player.stop()
        else:
            self._finish()


class ExtraPlayback(Playback):
    """A trailer or other extra (an item's extras[]): its own stream through a cast link, in the
    same player, with no progress, resume or Up Next (extras keep no watch state in Arc)."""

    def __init__(self, session, extra, on_finished=None):
        item = {"id": extra.get("id"), "kind": "extra", "title": extra.get("title", ""),
                "images": extra.get("backdrop") or {}}
        Playback.__init__(self, session, item, 0, on_finished)
        self.extra = extra
        self.duration_ms = int(extra.get("duration_ms") or 0)

    def _request(self, start_ms, failed_method=None):
        self._start_ms = start_ms
        self._last_ms = start_ms
        self.plan = {"method": "direct", "url": self.extra.get("stream_url"), "duration_ms": self.duration_ms,
                     "markers": [], "audio_tracks": [], "subtitle_tracks": [], "versions": []}
        log.info("playing an extra")
        return True

    def _report(self, state, position=None):
        pass

    def _remember(self, prefs):
        pass

    def _should_play_next(self):
        return False

    def on_error(self):
        self._fail()
