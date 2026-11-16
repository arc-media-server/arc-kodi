"""Arc's player window (skin/script-arc-player.xml): over Kodi's video for the whole playback, it
owns the remote and behaves as the Apple and Android players:

- with the controls hidden, Left and Right skip 10 s back and forward (presses add up, then it
  seeks), Select or Down shows the controls on the timeline, Up shows them on the Subtitles
  button, Play/Pause pauses, and Back stops;
- on the timeline Left and Right skip too, Select plays or pauses, Up goes to the round buttons;
- the round buttons (Playback, Audio, Subtitles) open their menu above; Back closes a menu, then
  hides the controls;
- Skip Intro/Recap/Credits takes the focus when it appears (Select skips); Up Next appears at the
  credits (or the last 30 s), counts down when the profile plays on by itself, and plays the next
  episode at once with Play.

It reads the Playback (kodi/player.py) for where things are and asks it to seek, pause, change
tracks and so on; it never talks to Arc itself.

In a Watch Together room it also shows the lobby until the room first plays (who's there; the host
starts it), notices ("Paused by Sam") at the top, and the room's actions in the Playback menu
(Invite More People, Leave, End for Everyone). Only the host's Up Next and Auto-Skip move the
room; the others follow it.
"""

import threading
import time

import xbmc
import xbmcgui

from arc import models, playback, playerinfo, titlepage
from arc import together as wt

from .compat import ADDON_PATH, T
from .log import log

CATCHER = 90
SKIP, UP_NEXT, UP_NEXT_TITLE, UP_NEXT_PLAY, UP_NEXT_CLOSE, UP_NEXT_COUNT = 100, 101, 104, 103, 105, 106
EPISODE_LINE, TITLE, STEPPING = 201, 202, 210   # 210: what steps aside while a card is open
PLAYBACK_BUTTON, AUDIO_BUTTON, SUBTITLES_BUTTON = 301, 302, 303
BUTTONS = (PLAYBACK_BUTTON, AUDIO_BUTTON, SUBTITLES_BUTTON)
TIMELINE, TIMELINE_BAR, MARKER, TIME_GROUP, TIME_PLAYED, TIME_LEFT = 400, 401, 402, 403, 404, 405
CHAPTER_MARK_BASE, CHAPTER_MARKS = 410, 40   # the timeline's chapter marks, 410-449
THUMB_GROUP, THUMB_IMAGE, THUMB_W = 460, 461, 328   # the thumbnail's group, image and width
MENU_TITLE, MENU_LIST, MENU_BACK = 601, 602, 603
MENU_ROW, MENU_ROWS, MENU_BOTTOM = 64, 7, 744  # rows 64 high, up to 7 showing, ending above the buttons
# The tabs under the timeline (Info, Chapters, Cast, Episodes) and their cards, as the Apple player's.
TAB_ROW, TAB_ROW_Y, TAB_ROW_Y_OPEN, TAB_GAP = 500, 966, 604, 16
TAB_IDS = {"info": 501, "chapters": 502, "cast": 503, "episodes": 504}
TAB_GROUPS = {"info": (511, 140), "chapters": (512, 190), "cast": (513, 140), "episodes": (514, 200)}
TAB_ORDER = ("info", "chapters", "cast", "episodes")
INFO_IMAGE, INFO_TITLE, RESTART, PREVIOUS, INFO_OVERVIEW, INFO_META, INFO_HOW, INFO_LINE = \
    521, 522, 523, 524, 525, 526, 527, 528
CHAPTERS_LIST, CAST_LIST, EPISODES_LIST = 531, 541, 551
CARD_FOCUS = {"info": RESTART, "chapters": CHAPTERS_LIST, "cast": CAST_LIST, "episodes": EPISODES_LIST}
CONTROLS, MENU = 200, 600
INFO, INFO_LIST, INFO_BACK = 850, 852, 853   # Player Info's panel (700s are the lobby's)
INFO_ROW, INFO_EVERY = 40, 1.0              # its rows; how often it reads Kodi again (seconds)
INFO_NAMES = {"video": 30461, "decoder": 30462, "picture": 30463, "pixformat": 30464, "hdr": 30465,
              "deint": 30466, "dolby_vision": 30467, "dv_profile": 30468, "dv_layers": 30469,
              "dv_changed": 30470, "display": 30471, "output": 30472, "output_format": 30473,
              "audio": 30474, "audio_decoder": 30475, "audio_format": 30476, "audio_sink": 30477,
              "arc": 30478, "arc_method": 30479, "arc_reason": 30480}
METHOD_NAMES = {"direct": 30481, "remux": 30482, "transcode": 30483}
LOBBY, LOBBY_TITLE, LOBBY_PEOPLE, LOBBY_STATUS = 700, 701, 702, 703
LOBBY_START, LOBBY_INVITE, LOBBY_LEAVE = 710, 711, 712
NOTICE_FOR = 3.0                # seconds a notice shows
# The group each focusable control shows with.
GROUP_OF = {PLAYBACK_BUTTON: CONTROLS, AUDIO_BUTTON: CONTROLS, SUBTITLES_BUTTON: CONTROLS, TIMELINE: CONTROLS,
            501: CONTROLS, 502: CONTROLS, 503: CONTROLS, 504: CONTROLS, RESTART: CONTROLS, PREVIOUS: CONTROLS,
            CHAPTERS_LIST: CONTROLS, CAST_LIST: CONTROLS, EPISODES_LIST: CONTROLS,
            MENU_LIST: MENU, UP_NEXT_PLAY: UP_NEXT, UP_NEXT_CLOSE: UP_NEXT,
            LOBBY_START: LOBBY, LOBBY_INVITE: LOBBY, LOBBY_LEAVE: LOBBY}

TL_X, TL_W = 100, 1720          # the timeline's place (the skin's)
MARKER_Y, MARKER_Y_FOCUSED = 862, 856
TIMES_Y, MARKS_Y, THUMB_Y = 904, 872, 668   # the skin's
STEP_MS = 10000                 # Left/Right
BIG_STEP_MS = 60000             # the remote's skip keys
SEEK_SETTLE = 0.8               # seconds after the last press before it seeks
# Kodi's own player dialogs opened by a key or an action (its OSD, its info, its delay slider):
# Arc's player is the interface, so they're closed as they appear. (The
# skin's seek bar isn't here: the skin reopens it at once while paused, so Arc's player draws
# over it instead; see the skin.)
KODI_DIALOGS = ("videoosd", "fullscreeninfo", "sliderdialog", "playerprocessinfo")
HIDE_AFTER = 5.0                # seconds without a key before the controls hide (while playing)
SHOW_AFTER_SEEK = 3.0
COUNTDOWN = 10                  # seconds of Up Next before the next episode plays

A_LEFT, A_RIGHT, A_UP, A_DOWN, A_SELECT = 1, 2, 3, 4, 7
A_BACK = (9, 10, 92)
A_INFO = (11, 24)               # Info, Show OSD
A_PAUSE = (12, 79, 229)         # Pause, Play, Play/Pause
A_STOP = (13,)
A_STEP_FWD, A_STEP_BACK, A_BIG_FWD, A_BIG_BACK = (20, 77), (21, 78), (22,), (23,)
A_NEXT, A_PREV = (14,), (15,)
A_CONTEXT = (117,)
A_PROCESS_INFO = (69,)          # Kodi's Player Process Info (the O key)


def language_name(code):
    if not code:
        return ""
    try:
        name = xbmc.convertLanguage(code, xbmc.ENGLISH_NAME)
    except Exception:
        name = ""
    return name or code.upper()


CODECS = {"aac": "AAC", "ac3": "Dolby Digital", "eac3": "Dolby Digital Plus", "truehd": "Dolby TrueHD",
          "dts": "DTS", "flac": "FLAC", "mp3": "MP3", "opus": "Opus", "vorbis": "Vorbis", "alac": "ALAC"}


def audio_label(track, i):
    name = language_name(track.get("language")) or track.get("title") or T(30220) % (i + 1)
    ch = int(track.get("channels") or 0)
    layout = T(30214) if ch == 1 else T(30215) if ch == 2 else ("%d.1" % (ch - 1)) if ch > 2 else ""
    codec = CODECS.get(track.get("codec") or "", (track.get("codec") or "").upper())
    return name, " · ".join(p for p in (codec, layout) if p)


def subtitle_label(track, i):
    name = language_name(track.get("language")) or track.get("title") or T(30220) % (i + 1)
    bits = []
    if track.get("forced"):
        bits.append(T(30218))
    if track.get("hearing_impaired"):
        bits.append(T(30219))
    if track.get("title") and language_name(track.get("language")):
        bits.append(track["title"])
    if track.get("external"):
        bits.append(T(30223))
    return name, " · ".join(bits)


def quality_label(kbps):
    if not kbps:
        return T(30211)
    if kbps >= 1000:
        mbps = kbps / 1000.0
        return T(30216) % (("%d" % mbps) if mbps == int(mbps) else ("%.1f" % mbps))
    return T(30217) % kbps


class PlayerControls(xbmcgui.WindowXMLDialog):
    def __new__(cls, pb):
        return super(PlayerControls, cls).__new__(cls, "script-arc-player.xml", ADDON_PATH, "Main", "1080i")

    def __init__(self, pb):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.pb = pb
        self.markers = []
        self.chapters = []
        self.auto_skip = bool((pb.session.prefs or {}).get("auto_skip"))
        self.auto_play = (pb.session.prefs or {}).get("auto_play", True) is not False
        self._skipped = set()
        self._dismissed = set()
        self._marker = None
        self._up_next = False
        self._was_paused = False    # for showing the controls when playback pauses
        self._info_at = None        # Player Info: when it last read Kodi (None while closed)
        self._card = None           # the tab whose card is open ("info", ...), or None
        self._tabs = ["info"]       # the tabs that show
        self._details = None        # the whole title (its cast and files), fetched once per title
        self._details_for = None
        self._cast = []
        self._previous = None       # the episode before this one, for Info's Previous
        self._up_next_closed = False
        self._countdown_from = None
        self._osd = False
        self._last_key = time.time()
        self._shown_until = 0.0     # shown for a moment (after a skip) without taking the focus
        self._pending = None        # a seek target being built up by Left/Right presses
        self._pending_at = 0.0
        self._menu = None           # (kind, options) while a menu is open
        self._menu_button = None
        self._lobby = False         # Watch Together's lobby is showing
        self._lobby_done = False    # the room has played: no lobby again
        self._notice_until = 0.0
        self._room_lock = threading.Lock()   # room updates come from several threads
        if pb.together is not None:
            pb.together.notify = self._notice
        self._done = threading.Event()
        threading.Thread(target=self._loop, name="arc-player-ui", daemon=True).start()

    def onInit(self):
        self._titles()
        self.setFocusId(CATCHER)
        if self.pb.together is not None and self.pb.together.room:
            self.on_room(self.pb.together.room)

    # MARK: - from the Playback

    def on_plan(self, plan):
        self.markers = plan.get("markers") or []
        self.chapters = playback.chapters(plan)
        self._draw_chapters()
        self._skipped.clear()
        self._dismissed.clear()
        self._up_next_closed = False
        self._countdown_from = None
        self._set_skip(None)
        self._set_up_next(False)
        self._titles()

    def finish(self):
        if self.pb.together is not None and self.pb.together.notify == self._notice:
            self.pb.together.notify = None
        self._done.set()
        try:
            self.close()
        except Exception:
            pass

    # MARK: - the loop: timeline, markers, Up Next, hiding

    def _loop(self):
        monitor = xbmc.Monitor()
        while not self._done.is_set() and not monitor.waitForAbort(0.25):
            try:
                self._tick()
            except Exception as e:
                log.debug("player controls tick failed (%s)", type(e).__name__)

    def _close_kodi_dialogs(self):
        for name in KODI_DIALOGS:
            if xbmc.getCondVisibility("Window.IsVisible(%s)" % name):
                xbmc.executebuiltin("Dialog.Close(%s,true)" % name)
                log.debug("closed Kodi's %s", name)
        # A busy spinner left open once playing (Kodi's own, not Arc's).
        if self.pb._started and xbmc.getCondVisibility("Window.IsActive(busydialog) + !Player.Caching"):
            xbmc.executebuiltin("Dialog.Close(busydialog,true)")
            log.debug("closed a stuck busy dialog")

    def _tick(self):
        self._close_kodi_dialogs()
        now = time.time()
        if self._info_at is not None and now - self._info_at >= INFO_EVERY:
            self._draw_info()
        if self._pending is not None and now - self._pending_at >= SEEK_SETTLE:
            target, self._pending = self._pending, None
            self.pb.seek_to(target)
        position = self._pending if self._pending is not None else self.pb.position_ms()
        duration = self.pb.duration_ms
        self.setProperty("arc.paused", "1" if self.pb.paused else "")
        # Paused (by the viewer, Kodi or the room), the controls come up, as Plex's and the Apple
        # player's do; they stay while paused.
        if self.pb.paused and not self._was_paused and not self._osd and self._menu is None \
                and self.pb._started and not self._lobby:
            self._show()
        self._was_paused = self.pb.paused
        if self._osd or now < self._shown_until:
            self._draw_timeline(position, duration)
        elif self._pending is None and self.getProperty("arc.thumb"):
            self.setProperty("arc.thumb", "")
        if self._osd and not self.pb.paused and self._menu is None and now - self._last_key > HIDE_AFTER \
                and self.getFocusId() in (TIMELINE, CATCHER):
            self._hide()
        elif not self._osd and now >= self._shown_until and self.getProperty("arc.osd") == "1":
            self.setProperty("arc.osd", "")
        if self._notice_until and now >= self._notice_until:
            self._notice_until = 0.0
            self.setProperty("arc.notice", "")
        if not self.pb._started or self._lobby:
            return
        in_room, host = self.pb.in_room(), self.pb.room_host()
        # Skip Intro/Recap/Credits, or skipping by itself (the profile's Auto-Skip; in a room only
        # the host's, which moves everyone).
        marker = playback.active_marker(self.markers, position)
        if marker and self.auto_skip and (host or not in_room) and marker.get("kind") != "credits" \
                and marker.get("start_ms") not in self._skipped:
            self._skipped.add(marker.get("start_ms"))
            log.debug("skipping the %s by itself", marker.get("kind"))
            self.pb.skip_to(marker.get("end_ms") or 0)
            return
        nxt = self.pb.next_item if host or not in_room else None  # a room's guests follow the host
        due = bool(nxt) and not self._up_next_closed and playback.shows_up_next(self.markers, position, duration)
        if due and not self._up_next:
            self._show_up_next(nxt)
        elif not due and self._up_next:
            self._set_up_next(False)
        if self._up_next and self._countdown_from is not None:
            left = COUNTDOWN - int(now - self._countdown_from)
            self._label(UP_NEXT_COUNT, T(30221) % max(0, left))
            if left <= 0:
                self._countdown_from = None
                self._set_up_next(False)
                self.pb.play_next_now()
                return
        if not self._up_next:
            if marker and marker.get("start_ms") not in self._dismissed and marker.get("start_ms") not in self._skipped:
                self._set_skip(marker)
            elif not marker:
                self._set_skip(None)

    def _draw_timeline(self, position, duration):
        frac = min(1.0, max(0.0, float(position) / duration)) if duration > 0 else 0.0
        try:
            self.getControl(TIMELINE_BAR).setPercent(frac * 100)
            x = int(TL_X + frac * TL_W) - 4
            focused = self.getFocusId() == TIMELINE
            marker = self.getControl(MARKER)
            marker.setPosition(x, MARKER_Y_FOCUSED if focused else MARKER_Y)
            marker.setHeight(44 if focused else 32)
            self.getControl(TIME_GROUP).setPosition(min(max(x - 30, TL_X), TL_X + TL_W - 420), TIMES_Y)
        except Exception:
            pass
        self._draw_thumb(position)
        self._label(TIME_PLAYED, models.clock(position))
        self._label(TIME_LEFT, "-" + models.clock(max(0, duration - position)) if duration > 0 else "")

    def _draw_chapters(self):
        """Marks where chapters start on the timeline (a small dark gap in the bar)."""
        marks = playback.chapter_marks(self.chapters, self.pb.duration_ms, CHAPTER_MARKS)
        for i in range(CHAPTER_MARKS):
            try:
                ctrl = self.getControl(CHAPTER_MARK_BASE + i)
                if i < len(marks):
                    ctrl.setPosition(int(TL_X + marks[i] * TL_W) - 2, MARKS_Y)
                    ctrl.setVisible(True)
                else:
                    ctrl.setVisible(False)
            except Exception:
                pass

    def _chapter_name(self, i):
        return (self.chapters[i].get("title") or "").strip() or T(30291) % (i + 1)

    def _draw_thumb(self, position):
        """While Left/Right builds up a skip, the thumbnail of where it will land, above the marker
        (as the Apple and Android players); gone once it seeks."""
        url = self.pb.thumb_url(position) if self._pending is not None else None
        if not url:
            if self.getProperty("arc.thumb"):
                self.setProperty("arc.thumb", "")
            return
        duration = self.pb.duration_ms
        frac = min(1.0, max(0.0, float(position) / duration)) if duration > 0 else 0.0
        x = int(TL_X + frac * TL_W) - THUMB_W // 2
        try:
            self.getControl(THUMB_GROUP).setPosition(min(max(x, TL_X), TL_X + TL_W - THUMB_W), THUMB_Y)
            self.getControl(THUMB_IMAGE).setImage(url, False)
        except Exception:
            pass
        self.setProperty("arc.thumb", "1")

    # MARK: - showing things

    def _label(self, control_id, text):
        try:
            self.getControl(control_id).setLabel(text or "")
        except Exception:
            pass

    def _focus(self, control_id):
        """Focuses a control that shows by a window property, once Kodi has drawn it (and its
        group: Control.IsVisible doesn't look at the parent), and checks the focus took."""
        group = GROUP_OF.get(control_id)

        def run():
            for _ in range(40):
                shown = xbmc.getCondVisibility("Control.IsVisible(%d)" % control_id) and \
                    (group is None or xbmc.getCondVisibility("Control.IsVisible(%d)" % group))
                if shown:
                    self.setFocusId(control_id)
                    if self.getFocusId() == control_id:
                        return
                xbmc.sleep(25)

        threading.Thread(target=run, daemon=True).start()

    def _titles(self):
        item = self.pb.item
        self._load_details()
        self._fill_info()
        if models.is_episode(item):
            self._label(EPISODE_LINE, self._episode_line(item))
            self._label(TITLE, item.get("series_title") or item.get("title", ""))
        else:
            self._label(EPISODE_LINE, "")
            self._label(TITLE, item.get("title", ""))

    def _show(self, focus=TIMELINE):
        self._draw_chapters()  # the length may only be known once it's playing
        self._layout_tabs()
        self._osd = True
        self.setProperty("arc.osd", "1")
        self._draw_timeline(self.pb.position_ms() if self._pending is None else self._pending, self.pb.duration_ms)
        if focus:
            self._focus(focus)

    def _hide(self):
        self._osd = False
        self._close_menu(refocus=False)
        self._close_card(refocus=False)
        self.setProperty("arc.osd", "")
        if self._marker:
            self._focus(SKIP)
        elif self._up_next:
            self._focus(UP_NEXT_PLAY)
        else:
            self.setFocusId(CATCHER)

    def _flash(self):
        """Shows the timeline for a moment (after a skip) without moving the focus."""
        self._shown_until = time.time() + SHOW_AFTER_SEEK
        self.setProperty("arc.osd", "1")

    def _set_skip(self, marker):
        if marker is self._marker:
            return
        self._marker = marker
        if marker is None:
            self.setProperty("arc.skip", "")
            if self.getFocusId() == SKIP:
                self.setFocusId(CATCHER)
            return
        label = {"intro": T(30180), "recap": T(30181), "credits": T(30182)}.get(marker.get("kind"), T(30180))
        self._label(SKIP, label)
        self.setProperty("arc.skip", "1")
        if not self._osd:
            self._focus(SKIP)

    def _show_up_next(self, nxt):
        self._up_next = True
        self._set_skip(None)
        self._label(UP_NEXT_TITLE, self._episode_line(nxt))
        self._countdown_from = time.time() if self.auto_play else None
        self._label(UP_NEXT_COUNT, T(30221) % COUNTDOWN if self.auto_play else "")
        self.setProperty("arc.upnext", "1")
        if not self._osd:
            self._focus(UP_NEXT_PLAY)

    def _set_up_next(self, on):
        if not on:
            self._up_next = False
            self._countdown_from = None
            self.setProperty("arc.upnext", "")
            if self.getFocusId() in (UP_NEXT_PLAY, UP_NEXT_CLOSE):
                self.setFocusId(CATCHER)

    # MARK: - Watch Together

    def on_room(self, room):
        """The room changed (or the player opened in one): the lobby until it first plays."""
        if self.pb.together is None or not room:
            return
        with self._room_lock:
            self._on_room(room)

    def _on_room(self, room):
        if wt.started(room) or not room.get("available"):
            self._lobby_done = self._lobby_done or wt.started(room)
            if self._lobby:
                self._lobby = False
                self.setProperty("arc.lobby", "")
                self.setFocusId(CATCHER)
            return
        if self._lobby_done:
            return
        host = wt.is_host(room)
        self.setProperty("arc.host", "1" if host else "")
        self._label(LOBBY_TITLE, (room.get("item") or {}).get("title") or self.pb.item.get("title", ""))
        words = {"unavailable": T(30376), "loading": T(30373), "watching": T(30375), "ready": T(30374)}
        rows = []
        for p in room.get("participants") or []:
            name = T(30370) % p.get("name", "") if p.get("id") == room.get("self_id") else p.get("name", "")
            if p.get("id") == room.get("host_id"):
                name += "  ·  " + T(30371)
            li = xbmcgui.ListItem(name, words[wt.participant_status(p)])
            li.setProperty("ready", "1" if p.get("ready") else "")
            rows.append(li)
        rows += [xbmcgui.ListItem(p.get("name", ""), T(30372)) for p in room.get("invited") or []]
        people = self.getControl(LOBBY_PEOPLE)
        people.reset()
        people.addItems(rows)
        code = self.pb.together.lobby_code()
        self._label(LOBBY_STATUS, (T(30368) % code if code else "") if host else T(30369) % wt.host_name(room))
        if not self._lobby:
            self._lobby = True
            self._hide()
            self.setProperty("arc.lobby", "1")
            self._focus(LOBBY_START if host else LOBBY_LEAVE)

    def _notice(self, text):
        self.setProperty("arc.notice", text)
        self._notice_until = time.time() + NOTICE_FOR

    def _invite_more(self):
        invite = getattr(self.pb.together, "invite_more", None)
        if invite:
            threading.Thread(target=invite, args=(self.pb.item,), daemon=True).start()

    # MARK: - menus

    def _open_menu(self, button):
        plan = self.pb.plan or {}
        options = []  # (label, detail, selected, action)
        if button == AUDIO_BUTTON:
            title = T(30184)
            for i, t in enumerate(playback.audio_tracks(plan)):
                name, detail = audio_label(t, i)
                options.append((name, detail, t.get("index") == self.pb.audio_index,
                                lambda t=t: self.pb.choose_audio(t)))
        elif button == SUBTITLES_BUTTON:
            title = T(30185)
            current = (self.pb.subtitle or {}).get("id")
            options.append((T(30186), "", current is None, lambda: self.pb.choose_subtitle(None)))
            for i, t in enumerate(plan.get("subtitle_tracks") or []):
                name, detail = subtitle_label(t, i)
                options.append((name, detail, t.get("id") == current, lambda t=t: self.pb.choose_subtitle(t)))
        elif button == PLAYBACK_BUTTON:
            title = T(30144)
            options.append((T(30210), quality_label(self.pb.max_kbps), False,
                            lambda: self._open_submenu("quality"), True))
            if len(plan.get("versions") or []) > 1:
                current = next((v for v in plan["versions"] if v.get("file_id") == self.pb.file_id), {})
                options.append((T(30212), self._version_name(current), False,
                                lambda: self._open_submenu("version"), True))
            if self.pb.speed_available():
                options.append((T(30293), self._speed_name(self.pb.speed()), False,
                                lambda: self._open_submenu("speed"), True))
            options.append((T(30380), self._offset_name(self.pb.offset_ms("audio")), False,
                            lambda: self._open_submenu("audio_offset"), True))
            if plan.get("subtitle_tracks"):
                options.append((T(30381), self._offset_name(self.pb.offset_ms("subtitles")), False,
                                lambda: self._open_submenu("subtitle_offset"), True))
            options.append((T(30213), "", False, lambda: self.pb.seek_to(0)))
            options.append((T(30460), "", False, self._toggle_info))
            if self.pb.in_room():
                if self.pb.room_host():
                    options.append((T(30365), "", False, self._invite_more))
                options.append((T(30366), T(30330), False, self.pb.stop))
                if self.pb.room_host():
                    options.append((T(30367), "", False, self.pb.together.end))
        else:
            return
        self._menu_button = button
        self._fill_menu(title, options)

    def _open_submenu(self, kind):
        plan = self.pb.plan or {}
        if kind == "quality":
            options = [(quality_label(q), "", q == self.pb.max_kbps, lambda q=q: self.pb.choose_quality(q))
                       for q in playback.quality_options(plan)]
            self._fill_menu(T(30210), options)
        elif kind == "episodes":
            # This season's episodes, the one playing ticked; choosing one plays it (from where the
            # profile left it), as the Apple player's Episodes tab.
            options = []
            for e in self.pb.season_episodes:
                name = titlepage.episode_label(e, self.pb.season_unplaced)
                detail = models.runtime_text(models.duration_ms(e)) or ""
                options.append((name, detail, e.get("id") == self.pb.item_id,
                                lambda e=e: self.pb.play_episode(e)))
            self._fill_menu(T(30292), options)
        elif kind == "speed":
            now = self.pb.speed()
            options = [(self._speed_name(v), "", abs(v - now) < 0.05, lambda v=v: self.pb.set_speed(v))
                       for v in playback.SPEEDS]
            self._fill_menu(T(30293), options)
        elif kind in ("audio_offset", "subtitle_offset"):
            # Later or earlier than the picture, in Kodi's steps; the one in use ticked.
            which = "audio" if kind == "audio_offset" else "subtitles"
            values = playback.AUDIO_OFFSETS if which == "audio" else playback.SUBTITLE_OFFSETS
            at = playback.nearest(values, self.pb.offset_ms(which))
            options = [(self._offset_name(v), "", i == at, lambda v=v: self.pb.set_offset(which, v))
                       for i, v in enumerate(values)]
            self._fill_menu(T(30380) if which == "audio" else T(30381), options)
        elif kind == "chapters":
            at = playback.chapter_at(self.chapters, self.pb.position_ms())
            options = [(self._chapter_name(i), models.clock(c.get("start_ms") or 0), i == at,
                        lambda c=c: self.pb.seek_to(c.get("start_ms") or 0)) for i, c in enumerate(self.chapters)]
            self._fill_menu(T(30290), options)
        elif kind == "version":
            options = [(self._version_name(v), "", v.get("file_id") == self.pb.file_id,
                        lambda v=v: self.pb.choose_version(v.get("file_id"))) for v in plan.get("versions") or []]
            self._fill_menu(T(30212), options)

    @staticmethod
    def _offset_name(ms):
        if not ms:
            return T(30382)
        return (T(30383) if ms > 0 else T(30384)) % playback.offset_amount(ms)

    @staticmethod
    def _episode_line(item):
        """"S2, E4 · name", or just the name for an episode outside the show's order (Arc sends
        0/0 for one: never "S0, E0")."""
        if not models.placed(item):
            return item.get("title", "")
        return T(30222) % (item.get("season_number") or 0, item.get("episode_number") or 0, item.get("title", ""))

    @staticmethod
    def _speed_name(v):
        return T(30294) if abs(v - 1.0) < 0.05 else T(30295) % ("%.1f" % v)

    @staticmethod
    def _version_name(v):
        bits = [v.get("edition") or ""]
        h = v.get("height") or 0
        bits.append("4K" if h >= 1600 else "%dp" % h if h else "")
        bits.append((v.get("hdr") or "").upper())
        return " · ".join(b for b in bits if b)

    # MARK: - tabs and cards (Info, Chapters, Cast, Episodes)

    def _load_details(self):
        """The whole title (its cast, files and pictures), once per title, off the UI's thread."""
        item_id = self.pb.item_id
        if self._details_for == item_id:
            return
        self._details_for = item_id
        self._details, self._cast = None, []

        def work():
            try:
                details = self.pb.api.item(item_id)
            except Exception as e:
                log.debug("player details not loaded (%s)", type(e).__name__)
                return
            if self._details_for != item_id or not isinstance(details, dict):
                return
            self._details = details
            self._cast = [c for c in models.actors(details) if c.get("name")]
            self._fill_info()
            self._layout_tabs()

        threading.Thread(target=work, daemon=True).start()

    def _layout_tabs(self):
        """Shows the tabs that have something, left to right from the timeline's start."""
        has = {"info": True, "chapters": bool(self.chapters), "cast": bool(self._cast),
               "episodes": len(self.pb.season_episodes or []) > 1}
        self._tabs = [t for t in TAB_ORDER if has[t]]
        x = 0
        for t in TAB_ORDER:
            group, width = TAB_GROUPS[t]
            try:
                ctrl = self.getControl(group)
                ctrl.setVisible(has[t])
                if has[t]:
                    ctrl.setPosition(x, 0)
                    x += width + TAB_GAP
            except Exception:
                pass

    def _fill_info(self):
        item = self._details or self.pb.item or {}
        episode = models.is_episode(item)
        images = models.images(item)
        picture = (images.get("primary") or images.get("series_backdrop")) if episode else \
            (images.get("backdrop") or images.get("primary"))
        if episode and models.spoiler_hidden(self.pb.session.prefs, item):
            picture = images.get("series_backdrop") or picture
        playing = self.pb.item or {}
        bits = []
        if episode and models.placed(playing):
            bits.append(models.episode_code(playing))   # in the order shown (the playing item's)
        bits.append(models.runtime_text(self.pb.duration_ms or models.duration_ms(item)) or "")
        if item.get("year"):
            bits.append(str(item["year"]))
        meta = " · ".join(b for b in bits if b)
        badges = "   ".join(models.quality_badges(item))
        method = (self.pb.plan or {}).get("method")
        try:
            self.getControl(INFO_IMAGE).setImage(self.pb.session.art(picture) if picture else "")
            self._label(INFO_TITLE, item.get("title", ""))
            self._label(INFO_LINE, item.get("series_title", "") if episode else "")
            overview = item.get("overview") or ""
            if overview and models.spoiler_hidden(self.pb.session.prefs, item):
                overview = T(30440)
            self.getControl(INFO_OVERVIEW).setText(overview)
            self._label(INFO_META, "   ".join(b for b in (meta, badges) if b))
            self._label(INFO_HOW, T(METHOD_NAMES[method]) if method in METHOD_NAMES else "")
        except Exception as e:
            log.debug("info card not filled (%s)", type(e).__name__)
        # Previous: the episode before this one in its season.
        self._previous = titlepage.previous_episode(self.pb.season_episodes, self.pb.item_id)
        self.setProperty("arc.previous", "1" if self._previous else "")

    def _fill_card(self, name):
        if name == "chapters":
            ctrl = self.getControl(CHAPTERS_LIST)
            ctrl.reset()
            at = playback.chapter_at(self.chapters, self.pb.position_ms())
            ctrl.addItems([xbmcgui.ListItem(self._chapter_name(i), models.clock(c.get("start_ms") or 0))
                           for i, c in enumerate(self.chapters)])
            if at >= 0:
                ctrl.selectItem(at)
        elif name == "cast":
            from arc import search
            ctrl = self.getControl(CAST_LIST)
            ctrl.reset()
            items = []
            for c in self._cast:
                li = xbmcgui.ListItem(c.get("name", ""), c.get("character") or "")
                if c.get("image"):
                    li.setArt({"thumb": self.pb.session.art(c["image"])})
                li.setProperty("initials", search.initials(c.get("name")))
                items.append(li)
            ctrl.addItems(items)
        elif name == "episodes":
            from .windows.cards import item_list_item
            ctrl = self.getControl(EPISODES_LIST)
            ctrl.reset()
            eps = self.pb.season_episodes or []
            show = self.pb.item or {}
            items = []
            for e in eps:
                e = dict(e)
                e.setdefault("series_title", show.get("series_title", ""))
                items.append(item_list_item(self.pb.session, e, "thumb"))
            ctrl.addItems(items)
            ids = [e.get("id") for e in eps]
            if self.pb.item_id in ids:
                ctrl.selectItem(ids.index(self.pb.item_id))

    def _open_card(self, name):
        """Shows a tab's card under the row (the title and timeline step aside) and focuses the tab."""
        self._layout_tabs()
        if name not in self._tabs:
            name = "info"
        if name == "info":
            self._fill_info()   # the season's episodes (for Previous) may have arrived since
        else:
            self._fill_card(name)
        self._card = name
        self.setProperty("arc.card", name)
        try:
            self.getControl(TAB_ROW).setPosition(TL_X, TAB_ROW_Y_OPEN)
        except Exception:
            pass
        self._focus(TAB_IDS[name])

    def _close_card(self, refocus=True):
        if self._card is None:
            return
        self._card = None
        self.setProperty("arc.card", "")
        try:
            self.getControl(TAB_ROW).setPosition(TL_X, TAB_ROW_Y)
        except Exception:
            pass
        if refocus:
            self._focus(TIMELINE)

    def _tab_of(self, focus):
        return next((t for t, cid in TAB_IDS.items() if cid == focus), None)

    def _card_keys(self, focus, code):
        """Up, Down, Left and Right on the tabs and in the cards; True when handled."""
        tab = self._tab_of(focus)
        if tab is not None:
            if code in (A_LEFT, A_RIGHT):
                i = self._tabs.index(tab) if tab in self._tabs else 0
                j = i + (1 if code == A_RIGHT else -1)
                if 0 <= j < len(self._tabs):
                    self._open_card(self._tabs[j])
                return True
            if code == A_UP:
                self._close_card()
                return True
            if code == A_DOWN and self._card:
                self._focus(CARD_FOCUS[self._card])
                return True
            return True
        if focus in (RESTART, PREVIOUS):
            if code == A_UP:
                self._focus(TAB_IDS["info"])
            elif code == A_RIGHT and focus == RESTART and self._previous:
                self.setFocusId(PREVIOUS)
            elif code == A_LEFT and focus == PREVIOUS:
                self.setFocusId(RESTART)
            return True
        if focus in (CHAPTERS_LIST, CAST_LIST, EPISODES_LIST) and code == A_UP:
            self._focus(TAB_IDS[self._card or "info"])
            return True
        return False

    # MARK: - Player Info

    def _toggle_info(self):
        if self._info_at is None:
            self._draw_info()
            self.setProperty("arc.info", "1")
            log.debug("player info shown")
        else:
            self._info_at = None
            self.setProperty("arc.info", "")

    def _draw_info(self):
        """Reads what Kodi's player reports now and shows it (once a second while open)."""
        self._info_at = time.time()
        values = {k: xbmc.getInfoLabel(label) for k, label in playerinfo.LABELS.items()}
        hw = xbmc.getCondVisibility(playerinfo.CONDITIONS["hw"])
        entries = playerinfo.rows(values, hw=hw, plan=self.pb.plan)
        try:
            ctrl = self.getControl(INFO_LIST)
            if ctrl.size() == len(entries) and all(
                    ctrl.getListItem(i).getProperty("key") == e[1] for i, e in enumerate(entries)):
                for i, e in enumerate(entries):   # the same rows: only their values change
                    if e[0] == "row":
                        ctrl.getListItem(i).setLabel2(self._info_value(e))
                return
            ctrl.reset()
            items = []
            for e in entries:
                li = xbmcgui.ListItem(T(INFO_NAMES.get(e[1], 30460)), self._info_value(e))
                li.setProperty("kind", e[0])
                li.setProperty("key", e[1])
                items.append(li)
            ctrl.addItems(items)
            self.getControl(INFO_BACK).setHeight(76 + len(entries) * INFO_ROW + 24)
        except Exception as e:
            log.debug("player info not drawn (%s)", type(e).__name__)

    @staticmethod
    def _info_value(entry):
        if entry[0] != "row":
            return ""
        if entry[1] == "arc_method" and entry[2] in METHOD_NAMES:
            return T(METHOD_NAMES[entry[2]])
        return entry[2]

    def _fill_menu(self, title, options):
        self._label(MENU_TITLE, title)
        ctrl = self.getControl(MENU_LIST)
        ctrl.reset()
        items = []
        selected = 0
        options = [o if len(o) == 5 else o + (False,) for o in options]
        self._menu = options
        for i, (label, detail, chosen, _, _) in enumerate(options):
            li = xbmcgui.ListItem(label, detail)
            li.setProperty("selected", "1" if chosen else "")
            items.append(li)
            if chosen:
                selected = i
        ctrl.addItems(items)
        ctrl.selectItem(selected)
        # The panel fits its rows and sits just above the round buttons.
        rows = max(1, min(len(items), MENU_ROWS))
        height = 76 + rows * MENU_ROW + 16
        try:
            ctrl.setHeight(rows * MENU_ROW)
            self.getControl(MENU_BACK).setHeight(height)
            self.getControl(MENU).setPosition(1240, MENU_BOTTOM - height)
        except Exception:
            pass
        self.setProperty("arc.menu", "1")
        self._focus(MENU_LIST)

    def _close_menu(self, refocus=True):
        if self._menu is None:
            return
        self._menu = None
        self.setProperty("arc.menu", "")
        if refocus and self._menu_button:
            self.setFocusId(self._menu_button)

    # MARK: - the remote

    def onClick(self, control_id):
        self._last_key = time.time()
        if control_id == LOBBY_START and self.pb.together is not None:
            self.pb.together.play()
        elif control_id == LOBBY_INVITE:
            self._invite_more()
        elif control_id == LOBBY_LEAVE:
            self.pb.stop()
        elif control_id == SKIP and self._marker:
            end = self._marker.get("end_ms") or 0
            self._skipped.add(self._marker.get("start_ms"))
            self._set_skip(None)
            self.pb.skip_to(end)
        elif control_id == UP_NEXT_PLAY:
            self._set_up_next(False)
            self.pb.play_next_now()
        elif control_id == UP_NEXT_CLOSE:
            self._up_next_closed = True
            self._set_up_next(False)
        elif control_id in BUTTONS:
            self._open_menu(control_id)
        elif control_id == MENU_LIST and self._menu:
            pos = self.getControl(MENU_LIST).getSelectedPosition()
            if 0 <= pos < len(self._menu):
                _, _, _, action, opens_submenu = self._menu[pos]
                if not opens_submenu:
                    self._close_menu()
                action()
        elif control_id == RESTART:
            self._close_card()
            self.pb.seek_to(0)
        elif control_id == PREVIOUS and self._previous:
            self.pb.play_episode(self._previous)
        elif control_id == CHAPTERS_LIST:
            pos = self.getControl(CHAPTERS_LIST).getSelectedPosition()
            if 0 <= pos < len(self.chapters):
                self._close_card()
                self.pb.seek_to(self.chapters[pos].get("start_ms") or 0)
        elif control_id == EPISODES_LIST:
            eps = self.pb.season_episodes or []
            pos = self.getControl(EPISODES_LIST).getSelectedPosition()
            if 0 <= pos < len(eps) and eps[pos].get("id") != self.pb.item_id and eps[pos].get("available", True):
                self.pb.play_episode(eps[pos])
        elif control_id == TIMELINE:
            if self._pending is not None:
                target, self._pending = self._pending, None
                self.pb.seek_to(target)
            else:
                self.pb.toggle_pause()

    def onAction(self, action):
        code = action.getId()
        self._last_key = time.time()
        focus = self.getFocusId()
        if code in A_STOP:
            return  # Kodi stops by itself; the Playback hears of it and cleans up
        if self._lobby:
            if code in A_BACK:
                self.pb.stop()   # closing the player leaves the room
            return               # the lobby's buttons move by themselves; Select is onClick
        if code in A_PROCESS_INFO:
            self._toggle_info()
            return
        if code in A_BACK:
            if self._menu is not None:
                self._close_menu()
            elif self._info_at is not None:
                self._toggle_info()
            elif self._card is not None:
                self._close_card()
            elif self._osd:
                self._hide()
            elif focus == SKIP and self._marker:
                self._dismissed.add(self._marker.get("start_ms"))
                self._set_skip(None)
            elif focus in (UP_NEXT_PLAY, UP_NEXT_CLOSE):
                self._up_next_closed = True
                self._set_up_next(False)
            else:
                self.pb.stop()
            return
        if code in A_PAUSE:
            # Kodi pauses by itself (it handles Play/Pause for any window); show where it is.
            if not self._osd:
                self._show(focus=None)
            return
        if self._menu is not None:
            return  # the list moves by itself; Select is onClick
        if code in A_STEP_FWD or code in A_STEP_BACK or code in A_BIG_FWD or code in A_BIG_BACK:
            delta = STEP_MS if code in A_STEP_FWD else -STEP_MS if code in A_STEP_BACK else \
                BIG_STEP_MS if code in A_BIG_FWD else -BIG_STEP_MS
            self._nudge(delta)
            return
        if code in A_NEXT and self.pb.next_item:
            self.pb.play_next_now()
            return
        if self._card_keys(focus, code):
            return
        if focus in (CATCHER, TIMELINE, SKIP):
            if code in (A_LEFT, A_RIGHT):
                self._nudge(STEP_MS if code == A_RIGHT else -STEP_MS)
                return
            if focus == CATCHER and code == A_DOWN:
                # Down from the picture opens Info, as the Apple player.
                self._show(None)
                self._open_card("info")
                return
            if focus == CATCHER and (code == A_SELECT or code in A_INFO):
                self._show(TIMELINE)
                return
            if focus == TIMELINE and code == A_DOWN:
                self._open_card("info")
                return
            if focus in (CATCHER, SKIP) and code == A_UP:
                self._show(SUBTITLES_BUTTON)
                return
            if focus == SKIP and code == A_DOWN:
                self._show(TIMELINE)
                return
            if focus == TIMELINE and code == A_UP:
                self.setFocusId(SUBTITLES_BUTTON)
                return
        elif focus in BUTTONS and code == A_DOWN:
            self.setFocusId(TIMELINE)

    def _nudge(self, delta):
        """Left/Right: the target moves 10 s per press from where it's playing (or where the
        presses so far have put it), and it seeks once the presses stop."""
        base = self._pending if self._pending is not None else self.pb.position_ms()
        self._pending = playback.clamp_seek(base + delta, self.pb.duration_ms)
        self._pending_at = time.time()
        if self._osd:
            self._draw_timeline(self._pending, self.pb.duration_ms)
        else:
            self._flash()
            self._draw_timeline(self._pending, self.pb.duration_ms)
