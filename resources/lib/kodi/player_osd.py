"""The player overlay: a dialog over the video showing Skip Intro/Recap/Credits when a marker is
on screen, and Up Next near the end. It owns no playback; it reads the Playback's ticks and tells
it to skip or to start the next episode. Auto-skip (the profile's pref) skips without a press.
"""

import xbmc
import xbmcgui

from arc import models, playback

from .compat import ADDON_PATH, T
from .log import log

SKIP = 100
UP_NEXT = 101
UP_NEXT_LABEL = 102


class PlayerOverlay(xbmcgui.WindowXMLDialog):
    def __new__(cls, pb):
        return super(PlayerOverlay, cls).__new__(cls, "script-arc-player.xml", ADDON_PATH, "Main", "1080i")

    def __init__(self, pb):
        self.pb = pb
        self.markers = []
        self.auto_skip = bool((pb.session.prefs or {}).get("auto_skip"))
        self._skipped = set()
        self._next_shown = False
        xbmcgui.WindowXMLDialog.__init__(self)

    def on_plan(self, plan):
        self.markers = plan.get("markers") or []

    def on_tick(self, source_ms, duration_ms, plan):
        marker = playback.active_marker(self.markers, source_ms)
        if marker and self.auto_skip and marker["kind"] != "credits" and marker["start_ms"] not in self._skipped:
            self._skipped.add(marker["start_ms"])
            self.pb.skip_to(marker["end_ms"])
            self._set_skip(None)
            return
        self._set_skip(marker)
        if playback.shows_up_next(self.markers, source_ms, duration_ms):
            self._show_up_next()
        else:
            self._next_shown = False
            self._set_visible(UP_NEXT, False)

    def _set_skip(self, marker):
        if marker is None:
            self._set_visible(SKIP, False)
            return
        label = {"intro": T(30180), "recap": T(30181), "credits": T(30182)}.get(marker["kind"], T(30180))
        self._marker = marker
        try:
            self.getControl(SKIP).setLabel(label)
            self.getControl(SKIP).setVisible(True)
        except Exception:
            pass

    def _show_up_next(self):
        if self._next_shown:
            return
        self._next_shown = True
        try:
            self.getControl(UP_NEXT).setVisible(True)
            self.getControl(UP_NEXT_LABEL).setLabel(T(30183))
        except Exception:
            pass

    def _set_visible(self, control_id, visible):
        try:
            self.getControl(control_id).setVisible(bool(visible))
        except Exception:
            pass

    def onClick(self, control_id):
        if control_id == SKIP and getattr(self, "_marker", None):
            self.pb.skip_to(self._marker["end_ms"])
            self._set_visible(SKIP, False)
        elif control_id == UP_NEXT:
            self.pb.play_next_now()
