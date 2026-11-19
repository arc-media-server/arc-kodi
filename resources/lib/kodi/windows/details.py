"""A title's page, as the Apple app's: the artwork over the title's own four colours, the hero
(logo, info line, badge capsules, overview, Starring and Directed by), Play (saying what it
plays) and round buttons (Play from the Beginning, Watched, Watchlist), a show's seasons and
episodes, More Like This, Cast, Collections, Trailers & Extras, and the About / Details / Crew /
Playback cards. The choices are arc/titlepage.py's; this draws them."""

import time

import xbmcgui

from arc import home as homerows
from arc import models, titlepage

from ..thememusic import ThemeMusic
from .. import toast
from ..compat import T
from ..log import log
from . import menu
from .base import ArcWindow, list_item
from .cards import item_art, item_list_item, set_progress

PLAY = 100
RESTART = 101
WATCHED = 102
WATCHLIST = 103
LOGO = 110
TITLE = 111
INFO = 112
OVERVIEW = 113
BG = 115
RATING = 141
GENRES = 142
CAPSULE_BASE = 160      # six slots, each a filled (160 + 2i) and an outlined (161 + 2i) capsule
CAPSULE_SLOTS = 6
STARRING = 95
DIRECTORS = 96
GLOWS = (120, 121, 122, 123)

SEASONS = 200
EPISODES = 201
RELATED = 300
RELATED_TITLE = 311
CAST = 330
CAST_TITLE = 331
COLLECTIONS = 340
COLLECTIONS_TITLE = 341
EXTRAS = 350
EXTRAS_TITLE = 351
CARDS = 360

# Left, right; and how long (ms) a title may take to load before it's logged at info.
MOVE_ACTIONS, SLOW_MS = (1, 2), 3000

# The Kodi side's words for arc/titlepage.py's card keys.
CARD_KEYS = {"released": 30145, "runtime": 30146, "rated": 30160, "genres": 30161, "directed": 30147,
             "written": 30159, "studios": 30148, "server": 30162, "connection": 30163, "profile": 30166,
             "quality": 30167, "bitrate": 30168, "size": 30169, "file": 30170}


class DetailsWindow(ArcWindow):
    # The page's rows, top to bottom (see ArcWindow.ROW_STOPS): Play and the round buttons, the
    # season tabs, the episodes, Cast, Extras, Related, Collections, the cards.
    ROW_STOPS = ((PLAY, RESTART, WATCHED, WATCHLIST), (SEASONS,), (EPISODES,), (CAST,), (EXTRAS,),
                 (RELATED,), (COLLECTIONS,), (CARDS,))

    xml = "script-arc-details.xml"

    def __init__(self, *args, **kwargs):
        self.item_id = kwargs.pop("item_id")
        self.initial = kwargs.pop("initial", None)
        # An episode to land on (a show opened from an episode's card): its season shows and it
        # takes the focus, once, as the Apple app opens an episode on its show's page.
        self.focus_episode = kwargs.pop("focus_episode", None)
        ArcWindow.__init__(self, *args, **kwargs)
        self.theme_music = ThemeMusic(self)
        self.item = None
        self.seasons = []       # the order's seasons (Play follows these)
        self.tabs = []          # the season tabs: the seasons, then Not in This Order
        self.season_index = 0
        self.show_missing = False
        self._seasons_request = 0
        self.related = []
        self.cast = []
        self.extras = []
        self.collections = []
        self.action = None      # what Play does: titlepage.play_action()
        self.nav = None

    def on_init(self):
        self.theme_music.window_id = xbmcgui.getCurrentWindowId()
        self.set_label(RELATED_TITLE, T(30143))
        self.set_label(CAST_TITLE, T(30171))
        self.set_label(COLLECTIONS_TITLE, T(30122))
        self.set_label(EXTRAS_TITLE, T(30149))
        if self.initial:
            # The card's own data draws the page at once: the picture, the words, and Play and
            # the round buttons (watched and watchlist from the card's state), so nothing waits
            # on Arc's full answer, which fills in the rest (genres, badges, cast, rows).
            self._render_hero(self.initial)
            self._render_actions(self.initial)
        else:
            self._render_actions({})
        started = time.time()

        def fetch():
            item = self.session.api.item(self.item_id)
            took = int((time.time() - started) * 1000)
            (log.info if took >= SLOW_MS else log.debug)("title page loaded in %d ms", took)
            return item

        self.run_async(fetch, self._loaded)
        self.run_async(lambda: self.session.api.palette(self.item_id), self._show_palette)

    def on_return(self):
        # Watched state and the resume point may have changed while playing.
        self.run_async(lambda: self.session.api.item(self.item_id), self._refreshed)
        if self.item and models.is_series(self.item):
            self._load_seasons()

    def on_live(self, change):
        # Theme music follows profile changes without restarting a tune.
        if self.session.prefs.get("theme_music") is False:
            if self.theme_music.played:
                self.theme_music.stop()
        else:
            self.theme_music.start(self.item)
        if change.touches((self.item or {}).get("library_id")):
            self.on_return()

    def _refreshed(self, item, error):
        if error is None and item:
            self.item = item
            self._render_actions()

    def _loaded(self, item, error):
        if error is not None or not item:
            toast.show(T(30004))
            self.on_back()
            return
        self.item = item
        self.theme_music.start(item)
        self._render_hero(item)
        self._render_actions()
        self._render_rows(item)
        self._render_cards(item)
        if models.is_series(item):
            self._load_seasons()
        self._load_related()
        if not self.focus_episode:
            self.focus_id(PLAY)

    # MARK: - background and hero

    def _show_palette(self, palette, error):
        corners = titlepage.palette_corners(palette) if error is None else None
        for control_id, colour in zip(GLOWS, corners or titlepage.WASH):
            try:
                self.getControl(control_id).setColorDiffuse(colour)
            except Exception:
                pass

    def _render_hero(self, item):
        art = item_art(self.session, item)
        self.set_image(BG, art.get("fanart") or art.get("thumb"))
        self.set_image(LOGO, art.get("clearlogo"))
        self.set_label(TITLE, "" if art.get("clearlogo") else item.get("title", ""))
        rating = item.get("content_rating") or ""
        self.setProperty("arc.rating", rating)
        self.set_label(RATING, rating)
        self.set_label(GENRES, "  ·  ".join((item.get("genres") or [])[:3]))
        self.set_text(OVERVIEW, item.get("overview") or item.get("tagline") or "")
        self.set_label(INFO, self._facts(item))
        # The quality capsules: the resolution filled, the rest outlined, as the reference's.
        # Each sizes to its text (an auto-width button).
        badges = models.quality_badges(item)[:CAPSULE_SLOTS]
        for i in range(CAPSULE_SLOTS):
            text = badges[i] if i < len(badges) else ""
            filled = i == 0 and text in ("4K", "1080p", "720p", "SD")
            self.set_label(CAPSULE_BASE + 2 * i + (0 if filled else 1), text)
            self.setProperty("arc.cap%d" % i, ("f" if filled else "o") if text else "")
        # Starring and Director at the right, as the Apple app's: the label lighter, the names
        # bold, ending level with the buttons. Starring (which may wrap to two lines) sits above
        # Director, or in its place when there's no director.
        stars = titlepage.starring(item)
        directors = titlepage.people(item, ("director",), 2)
        self.set_label(STARRING, self._labelled(T(30158), stars) if stars else "")
        self.set_label(DIRECTORS, self._labelled(T(30147), directors) if directors else "")
        # Kodi won't bottom-align a wrapping label, so the Python places Starring by how many
        # lines it takes (titlepage.wraps estimates it from the letters' widths).
        wraps = bool(stars) and titlepage.wraps(T(30158), ", ".join(stars))
        bottom = 36 if directors else 76      # where Starring's last line must end, in the row
        lines = 2 if wraps else 1
        try:
            self.getControl(STARRING).setPosition(1120, bottom - 38 * lines)
            self.getControl(STARRING).setHeight(40 * lines)
        except Exception:
            pass

    @staticmethod
    def _labelled(label, names):
        return "[COLOR FFD8D8DE]%s[/COLOR] [B]%s[/B]" % (label, ", ".join(names))

    def _facts(self, item):
        """The year (or an episode's code and year) and the length."""
        bits = []
        if models.is_episode(item):
            code = self._code(item)
            if code:
                bits.append(code)
        if item.get("year"):
            bits.append(str(item["year"]))
        rt = models.runtime_text(models.duration_ms(item))
        if rt:
            bits.append(rt)
        return "  ·  ".join(bits)

    @staticmethod
    def _code(item):
        s, e = item.get("season_number"), item.get("episode_number")
        return T(30172) % (s, e) if models.placed(item) else ""

    # MARK: - Play and the round buttons

    def _render_actions(self, item=None):
        item = item if item is not None else (self.item or {})
        episode = titlepage.next_to_play(self.seasons) if models.is_series(item) else None
        self.action = titlepage.play_action(item, episode)
        if self.action is None:
            label = T(30005)
        else:
            kind, target, _ = self.action
            if models.is_series(item):
                label = (T(30157) if kind == "resume" else T(30156)) % self._code(target)
            else:
                label = T(30006) if kind == "resume" else T(30005)
        self.set_label(PLAY, label)
        watched = models.watched(item)
        self.setProperty("arc.watchedicon", "arc-osd-circle-check-filled.png" if watched else "arc-osd-circle-check.png")
        self.setProperty("arc.watchlisticon", "arc-osd-bookmark-check.png" if models.watchlisted(item) else "arc-osd-bookmark.png")
        self._hint(self.getFocusId())

    def onFocus(self, control_id):
        self._hint(control_id)

    def _hint(self, control_id):
        """The focused round button's name, beside the row."""
        item = self.item or {}
        names = {RESTART: T(30213),
                 WATCHED: T(30151) if models.watched(item) else T(30150),
                 WATCHLIST: T(30153) if models.watchlisted(item) else T(30152)}
        self.setProperty("arc.hint", names.get(control_id, ""))

    # MARK: - seasons / episodes

    def _load_seasons(self, show_missing=None):
        missing = self.show_missing if show_missing is None else show_missing
        self._seasons_request += 1
        request = self._seasons_request

        def loaded(data, error):
            if request != self._seasons_request:
                return
            if error is not None or not data:
                toast.show(T(30004))
                return
            self.show_missing = missing
            self._show_seasons(data, None)

        self.run_async(lambda: self.session.api.seasons(self.item_id, missing=missing), loaded)

    def _show_seasons(self, data, error):
        if error is not None or not data:
            return
        previous = self.tabs[self.season_index] if 0 <= self.season_index < len(self.tabs) else None
        selected = self.list_control(EPISODES).getSelectedPosition()
        old_episodes = self._tab_episodes()
        episode_id = old_episodes[selected].get("id") if 0 <= selected < len(old_episodes) else None
        shown = [(t.get("season_number"), self._tab_name(t)) for t in self.tabs]
        self.seasons, self.tabs = titlepage.season_tabs(data)
        same = shown == [(t.get("season_number"), self._tab_name(t)) for t in self.tabs]
        focus = self.getFocusId()
        ctrl = self.list_control(SEASONS)
        if same and focus == SEASONS and not self.focus_episode:
            # Fetched again while choosing a season (one just marked, or a change from elsewhere):
            # the same tabs, so leave them (emptying the focused list would send the focus to
            # Play) and show the season's episodes as they are now.
            self._show_episodes(self.season_index, episode_id)
            if self.item:
                self._render_actions()
            return
        ctrl.reset()
        for s in self.tabs:
            ctrl.addItem(list_item(self._tab_name(s), props={"season": "" if s.get("unplaced") else s.get("season_number")}))
        if self.tabs:
            # Open on the season of the episode Play would play, as Plex does, or of the episode
            # this page was opened for.
            target = self.action[1] if self.action else None
            target = titlepage.next_to_play(self.seasons) or target
            landing = self.focus_episode
            if landing:
                target = {"id": landing}
            start = 0
            if previous and not landing:
                for i, tab in enumerate(self.tabs):
                    if (tab.get("season_number"), bool(tab.get("unplaced"))) == (previous.get("season_number"), bool(previous.get("unplaced"))):
                        start = i
                        break
                target = None
                landing = episode_id
            for i, s in enumerate(self.tabs):
                if target and any(e.get("id") == target.get("id") for e in s.get("episodes") or []):
                    start = i
                    break
            ctrl.selectItem(start)
            self._show_episodes(start, landing)
            if self.focus_episode:
                self.focus_episode = None
                self.focus_when_visible(EPISODES)
            elif previous and focus in (SEASONS, EPISODES):
                # Resetting a focused Kodi list sends focus to Play; restore it after refill.
                self.focus_when_visible(focus)
        if self.item:
            self._render_actions()

    @staticmethod
    def _tab_name(tab):
        return T(30385) if tab.get("unplaced") else tab.get("name") or (T(30155) % tab.get("season_number", 0))

    def _with_show(self, ep):
        """An episode from the season list, with its show's name and pictures (the list's episodes
        carry neither), so the player's heading names the show."""
        ep = dict(ep)
        show = self.item or {}
        ep.setdefault("parent_id", show.get("id"))
        if not ep.get("series_title"):
            ep["series_title"] = show.get("title", "")
        images = {"series_" + k: v for k, v in models.images(show).items() if not k.startswith("series_")}
        images.update(models.images(ep))
        ep["images"] = images
        return ep

    def _tab_episodes(self):
        tab = self.tabs[self.season_index] if 0 <= self.season_index < len(self.tabs) else {}
        return tab.get("episodes") or []

    def _show_episodes(self, index, episode_id=None):
        if not (0 <= index < len(self.tabs)):
            return
        self.season_index = index
        tab = self.tabs[index]
        ctrl = self.list_control(EPISODES)
        ctrl.reset()
        episodes = tab.get("episodes") or []
        ctrl.addItems([self._episode_item(ep, tab.get("unplaced")) for ep in episodes])
        target = {"id": episode_id} if episode_id else titlepage.next_to_play([tab])
        for i, ep in enumerate(episodes):
            if target and ep.get("id") == target.get("id"):
                ctrl.selectItem(i)
                break

    def _episode_item(self, ep, unplaced=False):
        art = item_art(self.session, ep)
        sub = models.runtime_text(models.duration_ms(ep))
        release = models.upcoming_release(ep)
        props = {"item_id": ep.get("id"), "available": "true" if ep.get("available", True) else "",
                 "watched": "true" if models.watched(ep) else "",
                 "progress": "" if models.progress(ep) is None else str(int(models.progress(ep) * 100))}
        if release:
            props["releases"] = T(30154) % ("%d %s" % (release.day, release.strftime("%b")))
            sub = props["releases"]
        if not ep.get("available", True):
            props["tag"] = T(30602)
            # Reuse the existing unavailable-artwork treatment without changing card layouts.
            props["releases"] = props.get("releases") or T(30602)
            sub = " · ".join(x for x in (T(30602), sub) if x)
        label = titlepage.episode_label(ep, unplaced)
        thumb = models.images(ep).get("primary")
        fallback = art.get("thumb")
        overview = ep.get("overview") or ""
        if models.spoiler_hidden(self.session.prefs, ep):
            # Hide Spoilers: the show's picture and no description until the episode is started.
            thumb = models.images(self.item).get("backdrop") or models.images(ep).get("series_backdrop")
            fallback = ""
            overview = T(30440) if overview else ""
        li = list_item(label, sub, art={"thumb": self.session.art(thumb) if thumb else fallback}, props=props)
        li.setProperty("overview", overview)
        set_progress(li, ep)
        return li

    # MARK: - the rows: Related, Cast, Collections, Extras

    def _load_related(self):
        self.run_async(lambda: self.session.api.similar(self.item_id), self._show_related)

    def _show_related(self, items, error):
        if error is not None or not items:
            return
        self.related = items
        ctrl = self.list_control(RELATED)
        ctrl.reset()
        ctrl.addItems([item_list_item(self.session, it, "poster") for it in items])

    def _render_rows(self, item):
        # Cast: the actors in billing order, then directors and writers.
        actors = [c for c in item.get("credits") or [] if (c.get("role") or "actor") == "actor"]
        crew = [c for c in item.get("credits") or [] if c.get("role") in ("director", "writer", "screenplay")]
        seen, self.cast = set(), []
        for c in actors + crew:
            key = (c.get("person_id"), c.get("role"))
            if key in seen or not c.get("name"):
                continue
            seen.add(key)
            self.cast.append(c)
        roles = {"director": T(30147), "writer": T(30159), "screenplay": T(30159)}
        ctrl = self.list_control(CAST)
        ctrl.reset()
        ctrl.addItems([list_item(c.get("name", ""), c.get("character") or roles.get(c.get("role"), ""),
                                 art={"thumb": self.session.art(c.get("image")) if c.get("image") else ""},
                                 props={"initials": "".join(w[:1] for w in c.get("name", "").split()[:2]).upper()})
                       for c in self.cast])

        self.collections = [c for c in item.get("collections") or [] if c.get("id")]
        ctrl = self.list_control(COLLECTIONS)
        ctrl.reset()
        ctrl.addItems([list_item(c.get("title", ""), art={"thumb": self.session.art(
            "/api/collections/%s/images/primary" % c["id"])}) for c in self.collections])

        self.extras = [e for e in item.get("extras") or [] if e.get("stream_url")]
        kinds = {"trailer": T(30173), "behind_the_scenes": T(30174), "featurette": T(30174)}
        backdrop = item_art(self.session, item).get("fanart")
        ctrl = self.list_control(EXTRAS)
        ctrl.reset()
        ctrl.addItems([list_item(e.get("title") or kinds.get(e.get("kind"), T(30175)),
                                 "  ·  ".join(b for b in (kinds.get(e.get("kind"), T(30175)),
                                                          models.runtime_text(e.get("duration_ms"))) if b),
                                 art={"thumb": backdrop}) for e in self.extras])

    def _render_cards(self, item):
        def body(lines):
            return "\n".join("[COLOR FFF5F5F7]%s[/COLOR]  %s" % (T(CARD_KEYS[k]), self._value(k, v)) for k, v in lines)

        cards = []
        about = item.get("overview") or item.get("tagline") or ""
        if about:
            cards.append((T(30140), "[B]%s[/B]\n%s" % (item.get("title", ""), about)))
        details = titlepage.details_lines(item)
        if details:
            cards.append((T(30141), body(details)))
        crew = titlepage.crew_lines(item)
        if crew:
            cards.append((T(30142), body(crew)))
        if models.playable(item):
            profile = (self.session.profile or {}).get("name", "")
            cards.append((T(30144), body(titlepage.playback_lines(item, self.session.identity_name,
                                                                  self.session.local, profile))))
        ctrl = self.list_control(CARDS)
        ctrl.reset()
        ctrl.addItems([list_item(title, props={"body": text}) for title, text in cards])

    @staticmethod
    def _value(key, value):
        if key == "connection":
            return T(30164) if value == "home" else T(30165)
        if key == "released":
            parts = value.split("-")
            try:
                import datetime
                d = datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                return "%d %s %d" % (d.day, d.strftime("%b"), d.year)
            except Exception:
                return value
        return value

    # MARK: - input

    def on_click(self, control_id):
        if control_id == PLAY:
            self._play(from_start=False)
        elif control_id == RESTART:
            self._play(from_start=True)
        elif control_id == WATCHED:
            self._toggle_watched()
        elif control_id == WATCHLIST:
            self._toggle_watchlist()
        elif control_id == SEASONS:
            self._season_menu()
        elif control_id == EPISODES:
            pos = self.list_control(EPISODES).getSelectedPosition()
            eps = self._tab_episodes()
            if 0 <= pos < len(eps) and eps[pos].get("available", True) and self.nav:
                ep = self._with_show(eps[pos])
                self.nav("play", {"item": ep, "resume": models.resume_ms(ep)})
        elif control_id == RELATED and self.nav:
            self._open(self.related, RELATED, lambda it: ("card", homerows.card(it)))
        elif control_id == CAST and self.nav:
            self._open(self.cast, CAST, lambda c: ("person", c) if c.get("person_id") else None)
        elif control_id == COLLECTIONS and self.nav:
            self._open(self.collections, COLLECTIONS, lambda c: ("collection", c))
        elif control_id == EXTRAS and self.nav:
            self._open(self.extras, EXTRAS, lambda e: ("extra", dict(e, backdrop=(self.item or {}).get("images"))))

    def _open(self, entries, control_id, make):
        pos = self.list_control(control_id).getSelectedPosition()
        if 0 <= pos < len(entries):
            target = make(entries[pos])
            if target:
                self.nav(*target)

    def on_action(self, action, code):
        # Moving along the season tabs shows that season (no Select needed), as the Apple app does.
        if code in MOVE_ACTIONS and self.getFocusId() == SEASONS:
            pos = self.list_control(SEASONS).getSelectedPosition()
            if pos != self.season_index:
                self._show_episodes(pos)
        from .base import ACTION_CONTEXT, ACTION_PLAY
        if code in ACTION_CONTEXT and self.nav:
            return self._card_menu()
        if code in ACTION_PLAY and self.getFocusId() == RELATED and self.nav:
            pos = self.list_control(RELATED).getSelectedPosition()
            if 0 <= pos < len(self.related) and models.playable(self.related[pos]):
                it = self.related[pos]
                self.nav("play", {"item": it, "resume": models.resume_ms(it)})
                return True
        if code in ACTION_PLAY and self.getFocusId() == EPISODES:
            pos = self.list_control(EPISODES).getSelectedPosition()
            eps = self._tab_episodes()
            if 0 <= pos < len(eps) and eps[pos].get("available", True) and self.nav:
                ep = self._with_show(eps[pos])
                self.nav("play", {"item": ep, "resume": models.resume_ms(ep)})
                return True
        return False

    def _card_menu(self):
        """Context Menu: the focused episode's or related title's menu, or, elsewhere on the page,
        the title's own (Play and the like are the page's buttons, so it has the rest)."""
        focus = self.getFocusId()
        if focus == SEASONS:
            return self._season_menu()
        if focus == EPISODES:
            pos = self.list_control(EPISODES).getSelectedPosition()
            eps = self._tab_episodes()
            if 0 <= pos < len(eps) and eps[pos].get("available", True):
                self.nav("context", {"item": eps[pos], "in_show": True,
                                     "on_changed": lambda _it, _act: self._load_seasons()})
                return True
            return False
        if focus == RELATED:
            ctrl = self.list_control(RELATED)
            pos = ctrl.getSelectedPosition()
            if 0 <= pos < len(self.related):
                from .cards import update_list_item
                self.nav("context", {"item": self.related[pos],
                                     "on_changed": lambda it, _act: update_list_item(ctrl.getListItem(pos), it)})
                return True
            return False
        if self.item:
            def changed(_it, _act):
                if models.is_series(self.item):
                    self._load_seasons()
                self._render_actions()
            self.nav("context", {"item": self.item, "on_page": True, "on_changed": changed})
            return True
        return False

    # MARK: - a season's menu

    def _season_menu(self):
        """OK or Context Menu on a season tab, as the Android app's: Mark Season as Watched (or
        Unwatched), Shuffle Season and Show/Hide Missing Episodes. The visibility
        toggle also works on empty seasons and Not in This Order."""
        index = self.list_control(SEASONS).getSelectedPosition()
        if not 0 <= index < len(self.tabs):
            return False
        if index != self.season_index:
            self._show_episodes(index)
        tab = self.tabs[index]
        actions = titlepage.season_actions(tab) + ["hide_missing" if self.show_missing else "show_missing"]
        words = {"watched": 30430, "unwatched": 30431, "shuffle": 30432,
                 "show_missing": 30600, "hide_missing": 30601}
        choice = menu.choose(self._tab_name(tab), [T(words[a]) for a in actions])
        if not 0 <= choice < len(actions):
            return True
        if actions[choice] in ("show_missing", "hide_missing"):
            self._load_seasons(show_missing=actions[choice] == "show_missing")
        elif actions[choice] == "shuffle":
            ids = titlepage.season_episode_ids(tab)
            if self.nav and ids:
                self.nav("queue", {"item_ids": ids, "shuffle": True})
        else:
            self._mark_season(index, actions[choice] == "watched")
        return True

    def _mark_season(self, index, played):
        """Marks the season on Arc (the show's played route with the season's number in the order
        shown), showing the ticks at once and putting them back if Arc says no."""
        tab = self.tabs[index]
        number = tab.get("season_number")
        before = tab.get("episodes") or []
        tab["episodes"] = titlepage.mark_season(tab, played)
        if self.season_index == index:
            self._show_episodes(index)
        count = len(titlepage.season_episode_ids(tab))

        def done(_result, error):
            if error is not None:
                log.warning("season not marked: %s", type(error).__name__)
                tab["episodes"] = before
                if self.season_index == index:
                    self._show_episodes(index)
                menu.choose(self._tab_name(tab), [T(30000)], message=T(30433))
                return
            log.info("season marked %s (%d episodes)", "watched" if played else "unwatched", count)
            self.on_return()   # the show again (Play follows), and its seasons

        self.run_async(lambda: self.session.api.set_played(self.item_id, played, season_number=number), done)

    def _play(self, from_start):
        if not self.action or not self.nav:
            return
        _, target, resume = self.action
        self.nav("play", {"item": target, "resume": 0 if from_start else resume})

    def _toggle_watched(self):
        if self.item is None:
            return  # still loading
        now = not models.watched(self.item)

        def done(_result, error):
            if error is None:
                self.item.setdefault("user_data", {})["played"] = now
                if models.is_series(self.item):
                    self.item["unwatched_count"] = 0 if now else 1
                    self._load_seasons()
                self._render_actions()

        self.run_async(lambda: self.session.api.set_played(self.item_id, now), done)

    def _toggle_watchlist(self):
        if self.item is None:
            return  # still loading
        now = not models.watchlisted(self.item)

        def done(_result, error):
            if error is None:
                self.item.setdefault("user_data", {})["watchlisted"] = now
                self._render_actions()

        self.run_async(lambda: self.session.api.set_watchlist(self.item_id, now), done)

    def close(self):
        self.theme_music.stop()
        super().close()

    def on_back(self):
        self.result = "back"
        self.close()
