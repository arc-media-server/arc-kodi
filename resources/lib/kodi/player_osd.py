"""Arc's overlay on the video: Skip Intro/Recap/Credits while a marker plays, and Up Next near
the end. It's a modeless dialog with nothing focusable while both are hidden, so the remote goes
to Kodi's own full-screen player (its OSD, seeking, play/pause) until one of them shows and takes
focus. Auto-skip (the profile's pref) skips without a press.
"""

import threading

import xbmc
import xbmcgui

from arc import models, playback

from .compat import ADDON_PATH, T
from .log import log

SKIP = 100
UP_NEXT = 101
UP_NEXT_TITLE = 104
UP_NEXT_PLAY = 103
UP_NEXT_CLOSE = 105

ACTION_BACK = (9, 10, 92)
ACTION_PLAYPAUSE = (12, 79, 229)
ACTION_STOP = (13,)


class PlayerOverlay(xbmcgui.WindowXMLDialog):
    def __new__(cls, pb):
        return super(PlayerOverlay, cls).__new__(cls, "script-arc-player.xml", ADDON_PATH, "Main", "1080i")

    def __init__(self, pb):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.pb = pb
        self.markers = []
        self.auto_skip = bool((pb.session.prefs or {}).get("auto_skip"))
        self._skipped = set()       # markers already skipped (by start)
        self._dismissed = set()     # markers whose Skip was closed with Back
        self._marker = None
        self._up_next = False       # showing
        self._up_next_closed = False

    # MARK: - from the Playback (its progress thread)

    def on_plan(self, plan):
        self.markers = plan.get("markers") or []
        self._skipped.clear()
        self._dismissed.clear()
        self._up_next_closed = False
        self._hide_skip()
        self._hide_up_next()

    def on_tick(self, source_ms, duration_ms, plan):
        marker = playback.active_marker(self.markers, source_ms)
        if marker and self.auto_skip and marker.get("kind") != "credits" and marker.get("start_ms") not in self._skipped:
            self._skipped.add(marker.get("start_ms"))
            log.debug("skipping the %s automatically", marker.get("kind"))
            self.pb.skip_to(marker.get("end_ms") or 0)
            return
        if marker and marker.get("start_ms") not in self._dismissed and not self._up_next:
            self._show_skip(marker)
        elif not marker:
            self._hide_skip()
        nxt = self.pb.next_item
        if nxt and not self._up_next_closed and playback.shows_up_next(self.markers, source_ms, duration_ms):
            self._show_up_next(nxt)
        elif self._up_next and not playback.shows_up_next(self.markers, source_ms, duration_ms):
            self._hide_up_next()  # seeked back before the credits

    # MARK: - showing and hiding

    def _control(self, control_id):
        try:
            return self.getControl(control_id)
        except Exception:
            return None

    def _focus_when_visible(self, control_id):
        # The skin shows the control on its next frame; focus is refused until then.
        def run():
            for _ in range(40):
                if xbmc.getCondVisibility("Control.IsVisible(%d)" % control_id):
                    self.setFocusId(control_id)
                    return
                xbmc.sleep(25)

        threading.Thread(target=run, daemon=True).start()

    def _show_skip(self, marker):
        if self._marker is marker:
            return
        self._marker = marker
        label = {"intro": T(30180), "recap": T(30181), "credits": T(30182)}.get(marker.get("kind"), T(30180))
        c = self._control(SKIP)
        if c:
            c.setLabel(label)
        self.setProperty("arc.skip", "1")
        self._focus_when_visible(SKIP)

    def _hide_skip(self):
        if self._marker is None:
            return
        self._marker = None
        self.setProperty("arc.skip", "")

    def _show_up_next(self, nxt):
        if self._up_next:
            return
        self._up_next = True
        self._hide_skip()
        title = nxt.get("title", "")
        code = models.episode_code(nxt)
        c = self._control(UP_NEXT_TITLE)
        if c:
            c.setLabel(("%s  %s" % (code, title)).strip())
        self.setProperty("arc.upnext", "1")
        self._focus_when_visible(UP_NEXT_PLAY)

    def _hide_up_next(self):
        if not self._up_next:
            return
        self._up_next = False
        self.setProperty("arc.upnext", "")

    # MARK: - input (only while Skip or Up Next has focus)

    def onClick(self, control_id):
        if control_id == SKIP and self._marker:
            end = self._marker.get("end_ms") or 0
            self._skipped.add(self._marker.get("start_ms"))
            self._hide_skip()
            self.pb.skip_to(end)
        elif control_id == UP_NEXT_PLAY:
            self._hide_up_next()
            self.pb.play_next_now()
        elif control_id == UP_NEXT_CLOSE:
            self._up_next_closed = True
            self._hide_up_next()

    def onAction(self, action):
        code = action.getId()
        if code in ACTION_BACK:
            if self._marker:
                self._dismissed.add(self._marker.get("start_ms"))
                self._hide_skip()
            if self._up_next:
                self._up_next_closed = True
                self._hide_up_next()
        elif code in ACTION_PLAYPAUSE:
            self.pb.player.pause()
        elif code in ACTION_STOP:
            self.pb.stop()
