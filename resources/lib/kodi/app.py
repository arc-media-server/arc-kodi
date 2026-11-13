"""The add-on's entry logic: start the artwork proxy, run the sign-in flow when needed, then Home,
and route navigation between the windows. Opened from default.py.
"""

import xbmcgui

from arc import models
from arc.api import APIError, Unreachable

from . import log as logmod
from .compat import T
from .log import log
from .session import Session
from .player import Playback
from .windows import signin, home, library, details, search, settings


class App(object):
    def __init__(self):
        logmod.install()
        self.session = Session()
        self.session.start_proxy()

    def run(self):
        if not self._ensure_signed_in():
            return
        if not self._ensure_profile():
            return
        if not self._load():
            return
        self._home()

    # MARK: - sign-in flow

    def _ensure_signed_in(self):
        while not self.session.signed_in:
            if not self.session.base_url:
                if signin.ConnectWindow.open(self.session) != "connected":
                    return False
            result = signin.SignInWindow.open(self.session)
            if result == "change_server":
                self.session.base_url = None
                continue
            if result != "signed_in":
                return False
        return True

    def _ensure_profile(self):
        while not self.session.has_profile:
            result = signin.ProfilesWindow.open(self.session)
            if result != "chosen":
                return False
        return True

    def _load(self):
        try:
            self.session.refresh()
            return True
        except Unreachable:
            xbmcgui.Dialog().notification("Arc", T(30004))
            return False
        except APIError as e:
            if e.status in (401, 403):
                # the token or profile is no longer valid; sign in again
                self.session.forget_profile()
                return self._ensure_profile() and self._load()
            xbmcgui.Dialog().notification("Arc", e.message)
            return False

    # MARK: - home + navigation

    def _home(self):
        while True:
            w = home.HomeWindow(home.HomeWindow.xml, self._path(), "Main", "1080i", session=self.session)
            w.nav = self._navigate
            w.doModal()
            result = w.result
            del w
            if result == "exit":
                return
            if result == "sign_out":
                self.session.sign_out()
                return self.run()
            if result == "switch_profile":
                self.session.forget_profile()
                if not self._ensure_profile() or not self._load():
                    return
                continue
            return

    def _path(self):
        from .compat import ADDON_PATH
        return ADDON_PATH

    def _navigate(self, kind, payload):
        """Called by Home and other windows to open a place, a card or the player."""
        if kind == "card":
            self._open_card(payload)
        elif kind == "context":
            self._context(payload)
        elif kind == "play":
            self._play(payload["item"], payload.get("resume", 0))
        elif kind == "library":
            self._open_library(payload)
        elif kind == "search":
            self._open(search.SearchWindow)
        elif kind == "watchlist":
            self._open_grid(T(30082), self._watchlist_loader())
        elif kind == "playlists":
            self._open_playlists()
        elif kind == "settings":
            self._open_settings()

    def _open(self, window_cls, **kwargs):
        w = window_cls(window_cls.xml, self._path(), "Main", "1080i", session=self.session, **kwargs)
        if hasattr(w, "nav"):
            w.nav = self._navigate
        w.doModal()
        result = getattr(w, "result", None)
        del w
        return result

    def _open_card(self, card):
        item = card["item"]
        if models.is_series(item) or not models.playable(item):
            self._open(details.DetailsWindow, item_id=item.get("id"), initial=item)
        else:
            self._open(details.DetailsWindow, item_id=item.get("id"), initial=item)

    def _context(self, card):
        item = card["item"]
        options = [T(30005), T(30151) if models.watched(item) else T(30150),
                   T(30153) if models.watchlisted(item) else T(30152)]
        choice = xbmcgui.Dialog().contextmenu(options)
        if choice == 0:
            self._play(item, models.resume_ms(item)) if models.playable(item) else self._open_card(card)
        elif choice == 1:
            try:
                self.session.api.set_played(item.get("id"), not models.watched(item))
            except Exception:
                pass
        elif choice == 2:
            try:
                self.session.api.set_watchlist(item.get("id"), not models.watchlisted(item))
            except Exception:
                pass

    def _open_library(self, lib):
        self._open(library.LibraryWindow, library=lib)

    def _open_grid(self, title, loader, style="poster"):
        self._open(library.GridWindow, title=title, loader=loader, style=style, paged=True)

    def _open_settings(self):
        result = self._open(settings.SettingsWindow)
        if result == "sign_out":
            self.session.sign_out()
            self.run()
        elif result == "switch_profile":
            self.session.forget_profile()
            if self._ensure_profile() and self._load():
                pass

    def _open_playlists(self):
        try:
            playlists = self.session.api.playlists()
        except Exception:
            playlists = []
        if not playlists:
            xbmcgui.Dialog().notification("Arc", T(30106))
            return
        names = [p.get("title") or p.get("name", "") for p in playlists]
        choice = xbmcgui.Dialog().select(T(30083), names)
        if choice >= 0:
            pid = playlists[choice].get("id")
            self._open_grid(names[choice], self._playlist_loader(pid))

    # MARK: - loaders

    def _watchlist_loader(self):
        def load(offset, limit):
            items = self.session.api.watchlist()
            return items, len(items)
        return load

    def _playlist_loader(self, playlist_id):
        def load(offset, limit):
            data = self.session.api.playlist(playlist_id) or {}
            items = [e.get("item", {}) for e in data.get("entries", [])]
            return items, len(items)
        return load

    # MARK: - playback

    def _play(self, item, resume_ms):
        done = {"over": False}

        def finished():
            done["over"] = True

        pb = Playback(self.session, item, resume_ms=resume_ms, on_finished=finished)
        if not pb.start():
            return
        # Keep this window's modal loop alive until playback is over; the Playback reports progress
        # and cleans up on its own thread, and calls `finished` when it ends (or fails to start).
        monitor = pb.monitor
        while not done["over"]:
            if monitor.waitForAbort(0.5):
                pb.stop()
                break
