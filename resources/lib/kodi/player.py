"""Playing a title. Kodi's own player (xbmc.Player) decodes and shows the stream; Arc's player
window (kodi/player_osd.py) stays over the video for the whole playback and owns the remote: its controls, seeking, Skip Intro/Recap/Credits, Up Next, audio and subtitles.

Progress goes to Arc on the source file's timeline every 10 s and on pause/stop; conversions are
pinged while paused and deleted on stop; Kodi's own resume points are ignored (Arc's are the
truth). A seek outside what a conversion has ready restarts it at that source position with a
fresh offset, as the web player does. Audio and picture-subtitle changes on a converted stream
ask Arc again (the conversion carries one audio track); on a file played as it is, Kodi switches
its own tracks.
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

    def onPlayBackEnded(self):
        self.pb.on_ended(finished=True)

    def onPlayBackStopped(self):
        self.pb.on_ended(finished=False)

    def onPlayBackError(self):
        self.pb.on_error()


class Playback(object):
    """One title's playback: start, keep progress, the choices made in the player, clean up."""

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
        self.paused = False
        self._started = False
        self._switching = False  # a new stream is replacing this one: ignore the old one's end
        self.duration_ms = models.duration_ms(item)
        self.controls = None
        self.next_item = None      # the episode after this one, for Up Next
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

    # MARK: - start

    def start(self):
        if not self._request(self.resume_ms):
            return False
        self._open_player()
        threading.Thread(target=self._progress_loop, daemon=True).start()
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
        if self.audio_index is None and (plan.get("audio_stream") or -1) >= 0:
            self.audio_index = plan["audio_stream"]
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
        if self.controls is None:
            self._open_controls()  # over the full-screen video, once it's showing
        if self.controls:
            self.controls.on_plan(self.plan)
        if models.is_episode(self.item) and self.next_item is None:
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

    def _fetch_next(self):
        try:
            self.next_item = self.api.next_episode(self.item_id)
        except Exception as e:
            log.debug("next episode unknown (%s)", type(e).__name__)

    def on_pause(self, paused):
        self.paused = paused
        self._report("paused" if paused else "playing")

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
        if finished and self._should_play_next():
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

    def seek_to(self, source_ms):
        """Seeks to a source position: within the file (or what's converted) Kodi seeks itself;
        outside a conversion's ready part Arc starts converting from there."""
        source_ms = playback.clamp_seek(source_ms, self.duration_ms)
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
            self.file_id = None
            self.audio_index = None
            self.burn_subtitle = None
            self._subtitle_chosen = False
            self._started = False
            self._stop.clear()
            if self._request(0):
                self._switching = True
                self._open_player()
                threading.Thread(target=self._progress_loop, daemon=True).start()
                return
        self._finish()

    def _fail(self):
        xbmcgui.Dialog().notification("Arc", T(30188))
        self._stop.set()
        self._finish()

    def _finish(self):
        if self.controls is not None:
            try:
                self.controls.finish()
            except Exception:
                pass
            self.controls = None
        if self.on_finished:
            self.on_finished()

    def stop(self):
        """Stops playing (the controls' Stop and Back); on_ended then reports and cleans up."""
        self.position_ms()  # where it was, before Kodi starts stopping
        self._stop.set()
        if self.player.isPlaying():
            self.player.stop()
        else:
            self._finish()
