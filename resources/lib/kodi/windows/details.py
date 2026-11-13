"""A title's page: the hero (logo, year/length, quality badges, overview), Play/Resume and the
round actions (Watched, Watchlist), then — for a show — season tabs and episodes, and Related and
Cast. Follows the Apple app's title page; the player opens from Play."""

import xbmc
import xbmcgui

from arc import home as homerows
from arc import models

from ..compat import T
from ..log import log
from .base import ArcWindow, list_item
from .cards import item_art, item_list_item, set_progress

PLAY = 100
WATCHED = 101
WATCHLIST = 102
LOGO = 110
TITLE = 111
INFO = 112
OVERVIEW = 113
BADGES = 114
BG = 115
META = 116

SEASONS = 200
EPISODES = 201
RELATED = 300
RELATED_TITLE = 311

MOVE_ACTIONS = (1, 2)  # left, right


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
        self.nav = None

    def on_init(self):
        self.set_label(RELATED_TITLE, T(30143))
        if self.initial:
            self._render_hero(self.initial)
        self.run_async(lambda: self.session.api.item(self.item_id), self._loaded)

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
        if models.is_series(item):
            self._load_seasons()
        self._load_related()
        self.focus_id(PLAY)

    # MARK: - hero

    def _render_hero(self, item):
        art = item_art(self.session, item)
        self.set_image(BG, art.get("fanart") or art.get("thumb"))
        self.set_image(LOGO, art.get("clearlogo"))
        self.set_label(TITLE, "" if art.get("clearlogo") else item.get("title", ""))
        self.set_label(INFO, self._info_line(item))
        self.set_text(OVERVIEW, item.get("overview") or item.get("tagline") or "")
        self.set_label(BADGES, "   ".join(models.quality_badges(item)))

    def _info_line(self, item):
        bits = []
        if item.get("year"):
            bits.append(str(item["year"]))
        rt = models.runtime_text(models.duration_ms(item))
        if rt:
            bits.append(rt)
        if item.get("content_rating"):
            bits.append(item["content_rating"])
        for g in (item.get("genres") or [])[:3]:
            bits.append(g)
        return "  ·  ".join(bits)

    def _render_actions(self):
        item = self.item
        resume = models.resume_ms(item)
        self.set_label(PLAY, T(30006) if resume > 0 else T(30005))
        self.set_label(WATCHED, T(30151) if models.watched(item) else T(30150))
        self.set_label(WATCHLIST, T(30153) if models.watchlisted(item) else T(30152))
        self.set_bool("watched", models.watched(item))
        self.set_bool("watchlisted", models.watchlisted(item))
        meta = []
        directors = [c.get("name") for c in models.credits_by_role(item, ("director",))][:2]
        if directors:
            meta.append("%s %s" % (T(30147), ", ".join(directors)))
        if item.get("studio"):
            meta.append("%s %s" % (T(30148), item["studio"]))
        self.set_text(META, "\n".join(meta))

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
            # Open on the season of the first episode left to watch, as Plex does.
            start = 0
            for i, s in enumerate(self.seasons):
                if any(e.get("available", True) and not models.watched(e) for e in s.get("episodes") or []):
                    start = i
                    break
            ctrl.selectItem(start)
            self._show_episodes(start)

    def _show_episodes(self, index):
        if not (0 <= index < len(self.seasons)):
            return
        self.season_index = index
        ctrl = self.list_control(EPISODES)
        ctrl.reset()
        episodes = self.seasons[index].get("episodes") or []
        ctrl.addItems([self._episode_item(ep) for ep in episodes])
        for i, ep in enumerate(episodes):
            if ep.get("available", True) and not models.watched(ep):
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
        label = "%d. %s" % (ep.get("episode_number") or 0, ep.get("title", ""))
        if release:
            sub = props["releases"]
        thumb = models.images(ep).get("primary")
        li = list_item(label, sub, art={"thumb": self.session.art(thumb) if thumb else art.get("thumb")}, props=props)
        li.setProperty("overview", ep.get("overview") or "")
        set_progress(li, ep)
        return li

    # MARK: - related

    def _load_related(self):
        self.run_async(lambda: self.session.api.similar(self.item_id), self._show_related)

    def _show_related(self, items, error):
        if error is not None or not items:
            return
        self.related = items
        ctrl = self.list_control(RELATED)
        ctrl.reset()
        ctrl.addItems([item_list_item(self.session, it, "poster") for it in items])

    # MARK: - input

    def on_click(self, control_id):
        if control_id == PLAY:
            self._play(self.item)
        elif control_id == WATCHED:
            self._toggle_watched()
        elif control_id == WATCHLIST:
            self._toggle_watchlist()
        elif control_id == EPISODES:
            pos = self.list_control(EPISODES).getSelectedPosition()
            eps = self.seasons[self.season_index].get("episodes") if self.seasons else []
            if 0 <= pos < len(eps) and eps[pos].get("available", True):
                self._play(eps[pos])
        elif control_id == RELATED and self.nav:
            pos = self.list_control(RELATED).getSelectedPosition()
            if 0 <= pos < len(self.related):
                self.nav("card", homerows.card(self.related[pos]))

    def on_action(self, action, code):
        # Moving along the season tabs shows that season (no Select needed), as the Apple app does.
        if code in MOVE_ACTIONS and self.getFocusId() == SEASONS:
            pos = self.list_control(SEASONS).getSelectedPosition()
            if pos != self.season_index:
                self._show_episodes(pos)
        return False

    def _play(self, item):
        if not item or not models.playable(item):
            # a series: play its next-up / first episode
            if self.seasons:
                for s in self.seasons:
                    for ep in s.get("episodes") or []:
                        if ep.get("available", True) and not models.watched(ep):
                            item = ep
                            break
                    if models.playable(item):
                        break
        if item and models.playable(item) and self.nav:
            self.nav("play", {"item": item, "resume": models.resume_ms(item)})

    def _toggle_watched(self):
        now = not models.watched(self.item)

        def done(_result, error):
            if error is None:
                self.item.setdefault("user_data", {})["played"] = now
                if models.is_series(self.item):
                    self.item["unwatched_count"] = 0 if now else 1
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
