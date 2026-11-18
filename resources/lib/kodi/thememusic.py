"""A page's native audio, once per visit. Never changes Kodi's system volume."""
import threading

import xbmc
import xbmcgui

from arc.thememusic import theme_path
from .log import log


class _ThemePlayer(xbmc.Player):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme

    def onAVStarted(self):
        # stop() can precede Kodi finishing an asynchronous open. Cancel that late start too;
        # ThemeMusic.stop checks ownership so a later film or other audio is never stopped.
        if self.theme.stopped:
            self.theme.stop()


class ThemeMusic:
    def __init__(self, window):
        self.window = window
        # Construct on the main thread, like the film player. No callbacks touch film sessions.
        self.player = _ThemePlayer(self)
        self.played = False
        self.stopped = False
        self.url = None
        self.window_id = None
        self.lock = threading.RLock()

    def start(self, item):
        with self.lock:
            path = theme_path(item, self.window.session.prefs)
            if not path or self.played or self.stopped or self.player.isPlaying():
                return
            if (xbmcgui.getCurrentWindowId() != self.window_id
                    or xbmc.getCondVisibility("System.HasActiveModalDialog")):
                return
            self.played = True
            self.url = self.window.session.artwork.url_for(path)
            try:
                self.player.play(self.url, windowed=True)
            except Exception:
                self.stopped = True
                log.debug("theme music unavailable")
                return
        threading.Thread(target=self._watch, name="arc-theme", daemon=True).start()

    def _watch(self):
        monitor = xbmc.Monitor()
        while not monitor.waitForAbort(0.1):
            if self.stopped:
                return
            if (self.window._closing or xbmcgui.getCurrentWindowId() != self.window_id
                    or xbmc.getCondVisibility("System.HasActiveModalDialog")
                    or xbmc.getCondVisibility("System.ScreenSaverActive")
                    or xbmc.getCondVisibility("System.DPMSActive")):
                self.stop()
                return
        self.stop()

    def stop(self):
        with self.lock:
            self.stopped = True
            try:
                # Kodi has one native player: never stop another title or audio source.
                if self.url and (not self.player.isPlaying() or self.player.getPlayingFile() == self.url):
                    self.player.stop()
            except Exception:
                log.debug("theme music stop unavailable")
