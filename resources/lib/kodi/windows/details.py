"""A title's page, as the Apple app's: the artwork over the title's own four colours, the hero
(logo, info line, badge capsules, overview, Starring and Directed by), Play (saying what it
plays) and round buttons (Play from the Beginning, Watched, Watchlist), a show's seasons and
episodes, Related, Cast, Collections, Trailers & Extras, and the About / Details / Crew /
Playback cards. The choices are arc/titlepage.py's; this draws them."""

import xbmcgui

from arc import home as homerows
from arc import models, titlepage

from ..compat import T
from ..log import log
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
BADGES = 114
BG = 115
PEOPLE = 116
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

MOVE_ACTIONS = (1, 2)  # left, right

# The Kodi side's words for arc/titlepage.py's card keys.
CARD_KEYS = {"released": 30145, "runtime": 30146, "rated": 30160, "genres": 30161, "directed": 30147,
             "written": 30159, "studios": 30148, "server": 30162, "connection": 30163, "profile": 30166,
             "quality": 30167, "bitrate": 30168, "size": 30169, "file": 30170}


class DetailsWindow(ArcWindow):
    xml = "script-arc-details.xml"

    def __init__(self, *args, **kwargs):
        self.item_id = kwargs.pop("item_id")
        self.initial = kwargs.pop("initial", None)
        ArcWindow.__init__(self, *args, **kwargs)
        self.item = None
        self.seasons = []
        self.season_index = 0
        self.related = []
        self.cast = []
        self.extras = []
        self.collections = []
        self.action = None      # what Play does: titlepage.play_action()
        self.nav = None

    def on_init(self):
        self.set_label(RELATED_TITLE, T(30143))
        self.set_label(CAST_TITLE, T(30171))
        self.set_label(COLLECTIONS_TITLE, T(30122))
        self.set_label(EXTRAS_TITLE, T(30149))
        if self.initial:
            self._render_hero(self.initial)
        self.run_async(lambda: self.session.api.item(self.item_id), self._loaded)
        self.run_async(lambda: self.session.api.palette(self.item_id), self._show_palette)

    def on_return(self):
        # Watched state and the resume point may have changed while playing.
        self.run_async(lambda: self.session.api.item(self.item_id), self._refreshed)
        if self.item and models.is_series(self.item):
            self._load_seasons()

    def _refreshed(self, item, error):
        if error is None and item:
            self.item = item
            self._render_actions()

    def _loaded(self, item, error):
        if error is not None or not item:
            xbmcgui.Dialog().notification("Arc", T(30004))
            self.on_back()
            return
        self.item = item
        self._render_hero(item)
        self._render_actions()
        self._render_rows(item)
        self._render_cards(item)
        if models.is_series(item):
            self._load_seasons()
        self._load_related()
        self.focus_id(PLAY)

    # MARK: - background and hero

    def _show_palette(self, palette, error):
        corners = titlepage.palette_corners(palette) if error is None else None
        for control_id, colour in zip(GLOWS, corners or [None] * 4):
            try:
                self.getControl(control_id).setColorDiffuse(colour or "00000000")
            except Exception:
                pass

    def _render_hero(self, item):
        art = item_art(self.session, item)
        self.set_image(BG, art.get("fanart") or art.get("thumb"))
        self.set_image(LOGO, art.get("clearlogo"))
        self.set_label(TITLE, "" if art.get("clearlogo") else item.get("title", ""))
        self.set_label(INFO, self._info_line(item))
        self.set_text(OVERVIEW, item.get("overview") or item.get("tagline") or "")
        badges = models.quality_badges(item)
        try:
            ctrl = self.list_control(BADGES)
            ctrl.reset()
            # The resolution is filled, the rest outlined, as the reference's capsules.
            ctrl.addItems([list_item(b, props={"filled": "1" if i == 0 and b in ("4K", "1080p", "720p", "SD") else ""})
                           for i, b in enumerate(badges)])
        except Exception:
            pass
        lines = []
        stars = titlepage.starring(item)
        if stars:
            lines.append("[COLOR FFF5F5F7]%s[/COLOR]\n%s" % (T(30158), ", ".join(stars)))
        directors = titlepage.people(item, ("director",), 2)
        if directors:
            lines.append("[COLOR FFF5F5F7]%s[/COLOR]\n%s" % (T(30147), ", ".join(directors)))
        self.set_text(PEOPLE, "\n\n".join(lines))

    def _info_line(self, item):
        bits = []
        if models.is_episode(item):
            code = self._code(item)
            if code:
                bits.append(code)
        if item.get("year"):
            bits.append(str(item["year"]))
        if item.get("content_rating"):
            bits.append(item["content_rating"])
        rt = models.runtime_text(models.duration_ms(item))
        if rt:
            bits.append(rt)
        for g in (item.get("genres") or [])[:3]:
            bits.append(g)
        return "  ·  ".join(bits)

    @staticmethod
    def _code(item):
        s, e = item.get("season_number"), item.get("episode_number")
        return T(30172) % (s, e) if s is not None and e is not None else ""

    # MARK: - Play and the round buttons

    def _render_actions(self):
        item = self.item
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

    def _load_seasons(self):
        self.run_async(lambda: self.session.api.seasons(self.item_id), self._show_seasons)

    def _show_seasons(self, data, error):
        if error is not None or not data:
            return
        self.seasons = data.get("seasons") or []
        ctrl = self.list_control(SEASONS)
        ctrl.reset()
        for s in self.seasons:
            name = s.get("name") or (T(30155) % s.get("season_number", 0))
            ctrl.addItem(list_item(name, props={"season": s.get("season_number")}))
        if self.seasons:
            # Open on the season of the episode Play would play, as Plex does.
            target = self.action[1] if self.action else None
            target = titlepage.next_to_play(self.seasons) or target
            start = 0
            for i, s in enumerate(self.seasons):
                if target and any(e.get("id") == target.get("id") for e in s.get("episodes") or []):
                    start = i
                    break
            ctrl.selectItem(start)
            self._show_episodes(start)
        if self.item:
            self._render_actions()

    def _show_episodes(self, index):
        if not (0 <= index < len(self.seasons)):
            return
        self.season_index = index
        ctrl = self.list_control(EPISODES)
        ctrl.reset()
        episodes = self.seasons[index].get("episodes") or []
        ctrl.addItems([self._episode_item(ep) for ep in episodes])
        target = titlepage.next_to_play([self.seasons[index]])
        for i, ep in enumerate(episodes):
            if target and ep.get("id") == target.get("id"):
                ctrl.selectItem(i)
                break

    def _episode_item(self, ep):
        art = item_art(self.session, ep)
        sub = models.runtime_text(models.duration_ms(ep))
        release = models.upcoming_release(ep)
        props = {"item_id": ep.get("id"), "available": "true" if ep.get("available", True) else "",
                 "watched": "true" if models.watched(ep) else "",
                 "progress": "" if models.progress(ep) is None else str(int(models.progress(ep) * 100))}
        if release:
            props["releases"] = T(30154) % ("%d %s" % (release.day, release.strftime("%b")))
            sub = props["releases"]
        label = "%d. %s" % (ep.get("episode_number") or 0, ep.get("title", ""))
        thumb = models.images(ep).get("primary")
        li = list_item(label, sub, art={"thumb": self.session.art(thumb) if thumb else art.get("thumb")}, props=props)
        li.setProperty("overview", ep.get("overview") or "")
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
        elif control_id == EPISODES:
            pos = self.list_control(EPISODES).getSelectedPosition()
            eps = self.seasons[self.season_index].get("episodes") if self.seasons else []
            if 0 <= pos < len(eps) and eps[pos].get("available", True) and self.nav:
                self.nav("play", {"item": eps[pos], "resume": models.resume_ms(eps[pos])})
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
            eps = self.seasons[self.season_index].get("episodes") if self.seasons else []
            if 0 <= pos < len(eps) and eps[pos].get("available", True) and self.nav:
                self.nav("play", {"item": eps[pos], "resume": models.resume_ms(eps[pos])})
                return True
        return False

    def _card_menu(self):
        """Context Menu: the focused episode's or related title's menu, or, elsewhere on the page,
        the title's own (Play and the like are the page's buttons, so it has the rest)."""
        focus = self.getFocusId()
        if focus == EPISODES:
            pos = self.list_control(EPISODES).getSelectedPosition()
            eps = self.seasons[self.season_index].get("episodes") if self.seasons else []
            if 0 <= pos < len(eps):
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

    def _play(self, from_start):
        if not self.action or not self.nav:
            return
        _, target, resume = self.action
        self.nav("play", {"item": target, "resume": 0 if from_start else resume})

    def _toggle_watched(self):
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
        now = not models.watchlisted(self.item)

        def done(_result, error):
            if error is None:
                self.item.setdefault("user_data", {})["watchlisted"] = now
                self._render_actions()

        self.run_async(lambda: self.session.api.set_watchlist(self.item_id, now), done)

    def on_back(self):
        self.result = "back"
        self.close()
