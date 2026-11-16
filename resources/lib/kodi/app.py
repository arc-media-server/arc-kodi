"""The add-on's entry logic: start the artwork proxy, run the sign-in flow when needed, then Home,
and route navigation between the windows. Opened from default.py.
"""

import xbmcgui

from arc import menus, models
from arc.api import APIError, Unreachable

from . import log as logmod
from .compat import T
from .log import log
from .live import Live
from .session import Session
from .together import Together
from .player import Playback
from .windows import signin, home, library, details, search, settings, menu, recommended, person


class App(object):
    def __init__(self):
        self.home_window = None
        self.playback = None  # the playing title, kept alive while Kodi plays it
        self.stack = []       # the open windows, Home first; the last is the one showing
        logmod.install()
        self.session = Session()
        self.session.start_proxy()
        self.live = Live(self.session, self._live_change)
        self.together = Together(self.session)
        self.together.open_player = lambda item, start_ms: self._play(item, start_ms, together=True)
        self.together.invite_more = lambda item: self._invite(item, room_id=(self.together.room or {}).get("id"))
        self.session.together = self.together

    def run(self):
        try:
            while True:
                if not self._ensure_signed_in():
                    return
                if not self._ensure_profile():
                    return
                loaded = self._load()
                if loaded == "change_server":
                    # From the Server Unavailable screen: forget this server, find another.
                    self.session.sign_out()
                    self.session.forget_server()
                    continue
                if not loaded:
                    return
                self._home()
                return
        finally:
            self._shut_down()

    def _shut_down(self):
        """Ends what still runs when the add-on closes: playback, then the artwork proxy's server.
        Kodi waits for an add-on's threads before it ends it, so the proxy left running kept the
        add-on alive after Back, and Kodi killed it at exit."""
        self.live.stop()
        self.together.leave()
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
        """Loads the profile's state from Arc. If Arc can't be reached (off, asleep, restarting),
        the Server Unavailable screen waits for it rather than the add-on closing. Returns True
        once loaded, "change_server", or False to leave."""
        while True:
            try:
                self.session.refresh()
                return True
            except Unreachable:
                log.warning("Arc can't be reached at start-up")
                result = signin.UnavailableWindow.open(self.session)
                if result == "retry":
                    continue
                return "change_server" if result == "change_server" else False
            except APIError as e:
                if e.status in (401, 403):
                    # the token or profile is no longer valid; sign in again
                    self.session.forget_profile()
                    if not self._ensure_profile():
                        return False
                    continue
                xbmcgui.Dialog().notification("Arc", e.message)
                return False

    # MARK: - home + navigation

    def _home(self):
        while True:
            w = home.HomeWindow(home.HomeWindow.xml, self._path(), "Main", "1080i", session=self.session)
            w.nav = self._navigate
            self.home_window = w
            self.stack = [w]
            self.live.start()
            w.doModal()
            result = w.result
            self.home_window = None
            self.stack = []
            del w
            if result == "reload":
                continue  # the profile's Home changed on Arc: build it again
            self.live.stop()
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
        elif kind == "together_card":
            self._together_card(payload["card"], payload.get("menu", False))
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
        self.stack.append(w)
        try:
            w.doModal()
        finally:
            if self.stack and self.stack[-1] is w:
                self.stack.pop()
        result = getattr(w, "result", None)
        del w
        return result

    def _live_change(self, change):
        """A change on Arc (live updates): fetch the profile's settings and libraries again if
        they may have changed, then let the window showing refresh itself. Nothing refreshes
        under the video: windows refresh when it ends anyway, and progress reports would
        otherwise refresh them every few seconds."""
        if self.playback is not None:
            return
        api = self.session.api
        try:
            if change.personal():
                self.session.prefs = api.prefs() or self.session.prefs
            if change.libraries_changed():
                self.session.libraries = api.libraries() or self.session.libraries
        except Exception as e:
            log.debug("live update: refetch failed (%s)", type(e).__name__)
        top = self.stack[-1] if self.stack else None
        if top is not None and not getattr(top, "_closing", False):
            log.debug("live update: refreshing %s", type(top).__name__)
            top.on_live(change)

    def _open_card(self, card):
        if card.get("room") or card.get("join_code"):
            self._together_card(card)
            return
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
                                     in_show=payload.get("in_show", False),
                                     together=self.together.available)
        labels = {"play": T(30005), "resume": T(30006), "from_start": T(30213),
                  "watched": T(30150), "unwatched": T(30151), "watchlist_add": T(30152),
                  "watchlist_remove": T(30153), "go_to_show": T(30176), "remove_continue": T(30177),
                  "watch_together": T(30331)}
        choice = menu.choose(item.get("title", ""), [labels[a] for a in actions])
        if choice < 0:
            return
        act = actions[choice]
        if act in ("play", "resume", "from_start"):
            self._play(item, 0 if act == "from_start" else models.resume_ms(item))
        elif act == "go_to_show":
            self._open_card({"item": item})
        elif act == "watch_together":
            self._invite(item)
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

    # MARK: - Watch Together

    def _together_card(self, card, with_menu=False):
        """A card on Home's Watch Together row: Select joins (or returns to) the room; Context Menu
        offers Join and Decline (Cancel Room for its maker). The last card joins with a code."""
        if card.get("join_code"):
            self._join_code()
            return
        room = card["room"]
        if with_menu:
            choice = menu.choose(card.get("label", ""), [T(30334) if room.get("joined") else T(30333),
                                                         T(30336) if room.get("hosting") else T(30335)])
            if choice < 0:
                return
            if choice == 1:
                self.together.dismiss(room)
                self._refresh_home()
                return
        try:
            self.together.accept(room)
        except Exception as e:
            log.warning("joining a Watch Together room failed (%s)", type(e).__name__)
            self._tell(T(30362))
            self._refresh_home()

    def _join_code(self):
        code = xbmcgui.Dialog().input(T(30359))
        if not code:
            return
        try:
            self.together.join(code)
        except APIError as e:
            log.info("joining with a code refused (%d)", e.status)
            self._tell(T(30360) if e.status == 404 else T(30361) if e.status == 429 else T(30362))
        except Exception as e:
            log.warning("joining with a code failed (%s)", type(e).__name__)
            self._tell(T(30362))

    def _invite(self, item, room_id=None):
        """Who to watch with: the people this profile may invite, ticked with Select, then Invite
        (a room waits on their Home rows) or Use a Code Instead (a room with a code, at once).
        For a room this device is in (`room_id`), Invite adds them to it."""
        try:
            people = self.session.api.watch_people(item.get("id"))
        except Exception as e:
            log.warning("who to invite didn't load (%s)", type(e).__name__)
            self._tell(T(30355))
            return
        title = item.get("title", "")
        message = T(30377) if room_id else T(30343) % title
        if not people:
            message = T(30354)
        chosen, focus = set(), None
        while True:
            options = [(p.get("name", ""), T(30346) if p.get("can_watch") is False else T(30353) if p.get("friend") else "")
                       for p in people]
            actions = []
            if people:
                options.append(T(30344))
                actions.append("invite")
            if not room_id:
                options.append(T(30345))
                actions.append("code")
            choice = menu.choose(T(30330), options, selected=chosen, focus=focus, message=message)
            if choice < 0:
                return
            if choice < len(people):
                focus = choice
                if people[choice].get("can_watch") is not False:
                    chosen ^= {choice}
                continue
            act = actions[choice - len(people)]
            if act == "invite" and not chosen:
                focus = choice
                continue
            ids = [people[i].get("id") for i in sorted(chosen)]
            try:
                if act == "code":
                    self.together.start_with_code(item.get("id"))
                elif room_id:
                    self.together.invite(ids)
                else:
                    self.together.create_room(item.get("id"), ids)
                    self._tell(T(30358) % title)
                    self._refresh_home()
            except APIError as e:
                log.warning("Watch Together room not made (%d)", e.status)
                self._tell(T(30356) if e.status == 429 else T(30357))
            except Exception as e:
                log.warning("Watch Together room not made (%s)", type(e).__name__)
                self._tell(T(30357))
            return

    def _tell(self, message):
        menu.choose(T(30330), [T(30000)], message=message)

    def _refresh_home(self):
        if self.home_window is not None:
            self.home_window.on_return()

    def _open_settings(self):
        result = self._open(settings.SettingsWindow)
        if result == "join_code":
            self._join_code()
            return
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

    def _play(self, item, resume_ms, queue=None, together=False):
        """Starts playback and returns at once. Kodi delivers the player's events (started, paused,
        ended) on this thread through the open window's loop, so it must not be held here waiting;
        the Playback reports progress and cleans up on its own threads."""
        if self.playback is not None:
            self.playback.stop()

        def finished():
            if self.playback is pb:
                self.playback = None

        pb = Playback(self.session, item, resume_ms=resume_ms, on_finished=finished, queue=queue,
                      together=self.together if together else None)
        self.playback = pb
        if not pb.start():
            self.playback = None
