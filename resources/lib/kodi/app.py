"""The add-on's entry logic: start the artwork proxy, run the sign-in flow when needed, then Home,
and route navigation between the windows. Opened from default.py.
"""

import xbmcgui

from arc import menus, models
from arc.api import APIError, Unreachable

from . import log as logmod
from .compat import T
from .log import log
from .session import Session
from .player import Playback
from .windows import signin, home, library, details, search, settings, menu, recommended, person


class App(object):
    def __init__(self):
        self.home_window = None
        self.playback = None  # the playing title, kept alive while Kodi plays it
        logmod.install()
        self.session = Session()
        self.session.start_proxy()

    def run(self):
        try:
            if not self._ensure_signed_in():
                return
            if not self._ensure_profile():
                return
            if not self._load():
                return
            self._home()
        finally:
            self._shut_down()

    def _shut_down(self):
        """Ends what still runs when the add-on closes: playback, then the artwork proxy's server.
        Kodi waits for an add-on's threads before it ends it, so the proxy left running kept the
        add-on alive after Back, and Kodi killed it at exit."""
        if self.playback is not None:
            try:
                self.playback.stop()
            except Exception:
                pass
            self.playback = None
        try:
            self.session.artwork.stop()
        except Exception as e:
            log.warning("stopping the artwork proxy failed: %s", type(e).__name__)
        log.info("closed")

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
            self.home_window = w
            w.doModal()
            result = w.result
            self.home_window = None
            del w
            if result == "exit":
                return
            if result == "sign_out":
                self.session.sign_out()
                return self.run()
            if result == "change_server":
                # Signed out of this server and it's forgotten: the add-on asks for one again.
                self.session.sign_out()
                self.session.forget_server()
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
        elif kind == "genre":
            self._open_genre(payload)
        elif kind == "search":
            self._open(search.SearchWindow)
        elif kind == "watchlist":
            self._open_grid(T(30082), self._watchlist_loader())
        elif kind == "playlists":
            self._open_playlists()
        elif kind == "settings":
            self._open_settings()
        elif kind == "person":
            self._open_person(payload)
        elif kind == "collection":
            self._open_collection(payload)
        elif kind == "extra":
            self._play_extra(payload)
        elif kind == "folder":
            self._open(library.FolderWindow, library=payload["library"], path=payload["path"],
                       title=payload.get("title", ""))

    def _open_person(self, credit):
        self._open(person.PersonWindow, person=credit)

    def _open_collection(self, ref):
        self._open(library.CollectionWindow, collection_id=ref.get("id"), title=ref.get("title", ""),
                   play=lambda shuffle, ids: self._play_queue(item_ids=ids, shuffle=shuffle))

    def _play_queue(self, item_ids=None, playlist_id=None, shuffle=False):
        """Play All / Shuffle: a play queue on Arc, then its first title; the player asks the queue
        for each next one."""
        from arc.queues import PlayQueue
        try:
            queue = PlayQueue.create(self.session.api, item_ids=item_ids, playlist_id=playlist_id, shuffle=shuffle)
        except Exception as e:
            log.warning("play queue failed: %s", type(e).__name__)
            xbmcgui.Dialog().notification("Arc", T(30289))
            return
        first = queue.current_item()
        if not first:
            xbmcgui.Dialog().notification("Arc", T(30289))
            return
        log.info("playing a queue of %d (%s)", len(queue.entries), "shuffled" if shuffle else "in order")
        self._play(first, 0, queue=queue)

    def _play_extra(self, extra):
        from .player import ExtraPlayback
        if self.playback is not None:
            self.playback.stop()

        def finished():
            if self.playback is pb:
                self.playback = None

        pb = ExtraPlayback(self.session, extra, on_finished=finished)
        self.playback = pb
        if not pb.start():
            self.playback = None

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
        if models.is_episode(item) and item.get("parent_id"):
            # No page of its own: an episode opens its show's page, on its season, focused on it.
            show = menus.show_ref(item)
            self._open(details.DetailsWindow, item_id=show["id"], initial=show, focus_episode=item.get("id"))
        else:
            self._open(details.DetailsWindow, item_id=item.get("id"), initial=item)

    def _context(self, payload):
        """A card's menu (Context Menu on any card): Arc's own menu with the Apple app's actions.
        `payload` has the item and, from the window, `continue_row`, `on_page` and `on_changed`
        (called with the item and the action once Arc has saved a change)."""
        item = payload.get("item") or {}
        actions = menus.card_actions(item, continue_row=payload.get("continue_row", False),
                                     on_page=payload.get("on_page", False),
                                     in_show=payload.get("in_show", False))
        labels = {"play": T(30005), "resume": T(30006), "from_start": T(30213),
                  "watched": T(30150), "unwatched": T(30151), "watchlist_add": T(30152),
                  "watchlist_remove": T(30153), "go_to_show": T(30176), "remove_continue": T(30177)}
        choice = menu.choose(item.get("title", ""), [labels[a] for a in actions])
        if choice < 0:
            return
        act = actions[choice]
        if act in ("play", "resume", "from_start"):
            self._play(item, 0 if act == "from_start" else models.resume_ms(item))
        elif act == "go_to_show":
            self._open_card({"item": item})
        else:
            self._change(item, act, payload.get("on_changed"))

    def _change(self, item, act, on_changed=None):
        """Saves a card's watched, watchlist or Continue Watching change to Arc, then updates the
        item in place and tells the window."""
        api = self.session.api
        try:
            if act in ("watched", "unwatched"):
                api.set_played(item.get("id"), act == "watched")
            elif act in ("watchlist_add", "watchlist_remove"):
                api.set_watchlist(item.get("id"), act == "watchlist_add")
            elif act == "remove_continue":
                api.remove_from_continue(item.get("id"))
        except Exception as e:
            log.warning("card action %s failed: %s", act, type(e).__name__)
            xbmcgui.Dialog().notification("Arc", T(30179))
            return
        log.debug("card action done: %s", act)
        ud = item.setdefault("user_data", {})
        if act in ("watched", "unwatched"):
            ud["played"] = act == "watched"
            ud["position_ms"] = 0
            if models.is_series(item):
                item["unwatched_count"] = 0 if act == "watched" else max(1, item.get("unwatched_count") or 1)
        elif act in ("watchlist_add", "watchlist_remove"):
            ud["watchlisted"] = act == "watchlist_add"
        if on_changed:
            try:
                on_changed(item, act)
            except Exception as e:
                log.error("refresh after %s failed: %s", act, e)

    def _open_genre(self, genre):
        """A genre from search: its library's Browse tab, filtered to the genre."""
        lib = next((l for l in self.session.libraries if l.get("id") == genre.get("library_id")), None)
        if lib is None:
            log.warning("genre's library isn't visible")
            return
        self._open_library(lib, tab="browse", genre=genre.get("name"))

    def _open_library(self, lib, tab=None, genre=None):
        """A library opens on Recommended (Browse for Other videos), as Plex and the Apple app; its
        tab pills swap the window for another tab's, so Back always returns to where it was
        opened from. `genre` filters the first Browse tab shown (a genre from search)."""
        tab = tab or library.library_tabs(lib)[0][0]
        while tab:
            if tab == "recommended":
                result = self._open(recommended.RecommendedWindow, library=lib)
            elif tab == "folders":
                result = self._open(library.FolderWindow, library=lib)
            elif tab == "collections":
                result = self._open(library.GridWindow, title=lib.get("name", ""), library=lib, tab="collections",
                                    loader=self._collections_loader(lib), style=library.library_style(lib),
                                    open_item=lambda c: self._open_collection(c))
            else:
                result = self._open(library.LibraryWindow, library=lib, genre=genre)
                genre = None
            tab = result[1] if isinstance(result, tuple) and result[0] == "tab" else None

    def _collections_loader(self, lib):
        def load(offset, limit):
            items = self.session.api.library_collections(lib.get("id")) or []
            return items, len(items)
        return load

    def _open_grid(self, title, loader, style="poster"):
        self._open(library.GridWindow, title=title, loader=loader, style=style, paged=True)

    def _open_settings(self):
        result = self._open(settings.SettingsWindow)
        if result in ("sign_out", "switch_profile", "change_server") and self.home_window is not None:
            # Home closes and _home() acts on it: a new profile gets a new Home, from scratch.
            self.home_window.result = result
            self.home_window.close()

    def _open_playlists(self):
        try:
            playlists = self.session.api.playlists()
        except Exception:
            playlists = []
        if not playlists:
            xbmcgui.Dialog().notification("Arc", T(30106))
            return
        names = [p.get("title") or p.get("name", "") for p in playlists]
        choice = menu.choose(T(30083), names)
        if choice >= 0:
            pid = playlists[choice].get("id")
            self._open(library.GridWindow, title=names[choice], loader=self._playlist_loader(pid), style="poster",
                       paged=True, play=lambda shuffle, _ids: self._play_queue(playlist_id=pid, shuffle=shuffle))

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

    def _play(self, item, resume_ms, queue=None):
        """Starts playback and returns at once. Kodi delivers the player's events (started, paused,
        ended) on this thread through the open window's loop, so it must not be held here waiting;
        the Playback reports progress and cleans up on its own threads."""
        if self.playback is not None:
            self.playback.stop()

        def finished():
            if self.playback is pb:
                self.playback = None

        pb = Playback(self.session, item, resume_ms=resume_ms, on_finished=finished, queue=queue)
        self.playback = pb
        if not pb.start():
            self.playback = None
