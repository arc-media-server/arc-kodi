"""Arc's player window (skin/script-arc-player.xml): over Kodi's video for the whole playback, it
owns the remote, as PM4K's does, and behaves as the Apple and Android players:

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
"""

import threading
import time

import xbmc
import xbmcgui

from arc import models, playback

from .compat import ADDON_PATH, T
from .log import log

CATCHER = 90
SKIP, UP_NEXT, UP_NEXT_TITLE, UP_NEXT_PLAY, UP_NEXT_CLOSE, UP_NEXT_COUNT = 100, 101, 104, 103, 105, 106
EPISODE_LINE, TITLE, OVERVIEW = 201, 202, 203
PLAYBACK_BUTTON, AUDIO_BUTTON, SUBTITLES_BUTTON = 301, 302, 303
BUTTONS = (PLAYBACK_BUTTON, AUDIO_BUTTON, SUBTITLES_BUTTON)
TIMELINE, TIMELINE_BAR, MARKER, TIME_GROUP, TIME_PLAYED, TIME_LEFT = 400, 401, 402, 403, 404, 405
CHAPTER_MARK_BASE, CHAPTER_MARKS = 410, 40   # the timeline's chapter marks, 410-449
THUMB_GROUP, THUMB_IMAGE, THUMB_W = 460, 461, 328   # the thumbnail's group, image and width
MENU_TITLE, MENU_LIST, MENU_BACK = 601, 602, 603
MENU_ROW, MENU_ROWS, MENU_BOTTOM = 64, 7, 816  # rows 64 high, up to 7 showing, ending above the buttons
CONTROLS, MENU = 200, 600
# The group each focusable control shows with.
GROUP_OF = {PLAYBACK_BUTTON: CONTROLS, AUDIO_BUTTON: CONTROLS, SUBTITLES_BUTTON: CONTROLS, TIMELINE: CONTROLS,
            MENU_LIST: MENU, UP_NEXT_PLAY: UP_NEXT, UP_NEXT_CLOSE: UP_NEXT}

TL_X, TL_W = 100, 1720          # the timeline's place (the skin's)
MARKER_Y, MARKER_Y_FOCUSED = 934, 928
STEP_MS = 10000                 # Left/Right
BIG_STEP_MS = 60000             # the remote's skip keys
SEEK_SETTLE = 0.8               # seconds after the last press before it seeks
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
        self._up_next_closed = False
        self._countdown_from = None
        self._osd = False
        self._last_key = time.time()
        self._shown_until = 0.0     # shown for a moment (after a skip) without taking the focus
        self._pending = None        # a seek target being built up by Left/Right presses
        self._pending_at = 0.0
        self._menu = None           # (kind, options) while a menu is open
        self._menu_button = None
        self._done = threading.Event()
        threading.Thread(target=self._loop, name="arc-player-ui", daemon=True).start()

    def onInit(self):
        self._titles()
        self.setFocusId(CATCHER)

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

    def _tick(self):
        now = time.time()
        if self._pending is not None and now - self._pending_at >= SEEK_SETTLE:
            target, self._pending = self._pending, None
            self.pb.seek_to(target)
        position = self._pending if self._pending is not None else self.pb.position_ms()
        duration = self.pb.duration_ms
        self.setProperty("arc.paused", "1" if self.pb.paused else "")
        if self._osd or now < self._shown_until:
            self._draw_timeline(position, duration)
        elif self._pending is None and self.getProperty("arc.thumb"):
            self.setProperty("arc.thumb", "")
        if self._osd and not self.pb.paused and self._menu is None and now - self._last_key > HIDE_AFTER \
                and self.getFocusId() in (TIMELINE, CATCHER):
            self._hide()
        elif not self._osd and now >= self._shown_until and self.getProperty("arc.osd") == "1":
            self.setProperty("arc.osd", "")
        if not self.pb._started:
            return
        # Skip Intro/Recap/Credits, or skipping by itself (the profile's Auto-Skip).
        marker = playback.active_marker(self.markers, position)
        if marker and self.auto_skip and marker.get("kind") != "credits" and marker.get("start_ms") not in self._skipped:
            self._skipped.add(marker.get("start_ms"))
            log.debug("skipping the %s by itself", marker.get("kind"))
            self.pb.skip_to(marker.get("end_ms") or 0)
            return
        nxt = self.pb.next_item
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
            self.getControl(TIME_GROUP).setPosition(min(max(x - 30, TL_X), TL_X + TL_W - 420), 976)
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
                    ctrl.setPosition(int(TL_X + marks[i] * TL_W) - 2, 944)
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
            self.getControl(THUMB_GROUP).setPosition(min(max(x, TL_X), TL_X + TL_W - THUMB_W), 740)
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
        try:
            self.getControl(OVERVIEW).setText(item.get("overview") or "")
        except Exception:
            pass
        if models.is_episode(item):
            self._label(EPISODE_LINE, T(30222) % (item.get("season_number") or 0, item.get("episode_number") or 0,
                                                 item.get("title", "")))
            self._label(TITLE, item.get("series_title") or item.get("title", ""))
        else:
            self._label(EPISODE_LINE, "")
            self._label(TITLE, item.get("title", ""))

    def _show(self, focus=TIMELINE):
        self._draw_chapters()  # the length may only be known once it's playing
        self._osd = True
        self.setProperty("arc.osd", "1")
        self._draw_timeline(self.pb.position_ms() if self._pending is None else self._pending, self.pb.duration_ms)
        if focus:
            self._focus(focus)

    def _hide(self):
        self._osd = False
        self._close_menu(refocus=False)
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
        self._label(UP_NEXT_TITLE, T(30222) % (nxt.get("season_number") or 0, nxt.get("episode_number") or 0,
                                               nxt.get("title", "")))
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
            if models.is_episode(self.pb.item) and self.pb.season_episodes:
                options.append((T(30292), T(30155) % (self.pb.item.get("season_number") or 0), False,
                                lambda: self._open_submenu("episodes"), True))
            if self.chapters:
                at = playback.chapter_at(self.chapters, self.pb.position_ms())
                options.append((T(30290), self._chapter_name(at) if at >= 0 else "", False,
                                lambda: self._open_submenu("chapters"), True))
            options.append((T(30213), "", False, lambda: self.pb.seek_to(0)))
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
                name = "%s. %s" % (e.get("episode_number") or "", e.get("title", ""))
                detail = models.runtime_text(models.duration_ms(e)) or ""
                options.append((name, detail, e.get("id") == self.pb.item_id,
                                lambda e=e: self.pb.play_episode(e)))
            self._fill_menu(T(30292), options)
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
    def _version_name(v):
        bits = [v.get("edition") or ""]
        h = v.get("height") or 0
        bits.append("4K" if h >= 1600 else "%dp" % h if h else "")
        bits.append((v.get("hdr") or "").upper())
        return " · ".join(b for b in bits if b)

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
        if control_id == SKIP and self._marker:
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
        if code in A_BACK:
            if self._menu is not None:
                self._close_menu()
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
        if focus in (CATCHER, TIMELINE, SKIP):
            if code in (A_LEFT, A_RIGHT):
                self._nudge(STEP_MS if code == A_RIGHT else -STEP_MS)
                return
            if focus == CATCHER and (code in (A_SELECT, A_DOWN) or code in A_INFO):
                self._show(TIMELINE)
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
