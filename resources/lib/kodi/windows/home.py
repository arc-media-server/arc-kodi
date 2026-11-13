"""Home: the sidebar and the profile's rows (Continue Watching, each library's newest, the
Watchlist, collections and playlists), arranged as the web does. The focused card's artwork fills
the background, as on the Apple TV. Rows are stacked horizontal lists filled from the server.
"""

import xbmc
import xbmcgui

from arc import home as homerows
from arc import models

from ..compat import T
from ..log import log
from .base import ACTION_CONTEXT, ACTION_PLAY, ArcWindow, list_item
from .cards import card_list_item

MAX_ROWS = 12
# Each row slot exists twice in the skin: as posters and as wide cards. Ids are base + slot (1..12).
# A slot's title and list show themselves once the list has cards (a skin condition).
POSTER_LIST_BASE, POSTER_TITLE_BASE = 3000, 3100
THUMB_LIST_BASE, THUMB_TITLE_BASE = 3400, 3500

SIDEBAR = 50
ROWS = 900
BG_FANART = 61
HERO_LOGO = 62
HERO_TITLE = 63
HERO_INFO = 64
HERO_OVERVIEW = 65

MOVE_ACTIONS = (1, 2, 5, 6)  # left, right, page up, page down
ACTION_UP, ACTION_DOWN = 3, 4


class HomeWindow(ArcWindow):
    xml = "script-arc-home.xml"

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self.rows = []            # resolved row specs with their loaded cards
        self.places = []
        self._focused_once = False
        self._refreshing = False
        self._row = None  # the row with the focus, as of the last key (see on_action)
        self.nav = None           # a callback the app sets: nav(kind, payload)

    def on_init(self):
        self._build_sidebar()
        self.rows = self.session.home_rows()[:MAX_ROWS]
        self.list_control(SIDEBAR).selectItem(1)  # Home is the chosen place
        self._layout_rows()
        # Home starts on its rows: the first row with cards takes focus when it arrives (_fill_row).
        self._load_rows()

    # MARK: - sidebar

    def _build_sidebar(self):
        libs = self.session.ordered_libraries()
        watchlist_at = min(max(int((self.session.prefs or {}).get("watchlist_position") or 0), 0), len(libs))
        places = [("search", T(30080), "search"), ("home", T(30081), "home")]
        middle = []
        for lib in libs:
            # The web and Android apps' icons (Lucide): film, tv, clapperboard for other videos.
            icon = {"shows": "tv", "videos": "clapperboard"}.get(lib.get("kind"), "film")
            middle.append(("library:%s" % lib.get("id"), lib.get("name", ""), icon, lib))
        middle.insert(watchlist_at, ("watchlist", T(30082), "bookmark", None))
        places += middle
        places += [("playlists", T(30083), "list-video"), ("settings", T(30084), "settings")]
        self.places = places
        ctrl = self.list_control(SIDEBAR)
        ctrl.reset()
        for place in places:
            ctrl.addItem(list_item(place[1], props={"icon": place[2], "place": place[0]}))

    # MARK: - rows

    @staticmethod
    def _wide(row):
        return row.get("style") in (homerows.THUMB, homerows.BACKDROP)

    def _list_id(self, idx):
        wide = idx < len(self.rows) and self._wide(self.rows[idx])
        return (THUMB_LIST_BASE if wide else POSTER_LIST_BASE) + 1 + idx

    def _row_at(self, control_id):
        """The row index a list control belongs to, or None."""
        for base in (POSTER_LIST_BASE, THUMB_LIST_BASE):
            if base < control_id <= base + MAX_ROWS:
                return control_id - base - 1
        return None

    def _layout_rows(self):
        for i in range(MAX_ROWS):
            if i < len(self.rows):
                wide = self._wide(self.rows[i])
                self.set_label((THUMB_TITLE_BASE if wide else POSTER_TITLE_BASE) + 1 + i, self._row_title(self.rows[i]))

    def on_return(self):
        # Refresh the rows in place (Continue Watching changes after playing), keeping the focus.
        self._refreshing = True
        self._load_rows()

    def _row_title(self, row):
        source = row["source"]
        kind = source[0]
        titles = {"continue": T(30100), "next-up": T(30101), "watchlist": T(30082)}
        if kind in titles:
            return titles[kind]
        if kind == "recent":
            return T(30102) % source[1].get("name", "")
        if kind == "seasonal":
            return {"romance": T(30103), "horror": T(30104), "christmas": T(30105)}.get(source[1], "")
        if kind in ("custom", "collection", "playlist"):
            return source[1] if kind == "custom" else source[2]
        return ""

    def _load_rows(self):
        for i, row in enumerate(self.rows):
            self.run_async(lambda r=row: self._fetch_row(r), lambda cards, err, idx=i: self._fill_row(idx, cards, err))

    def _fetch_row(self, row):
        api = self.session.api
        kind = row["source"]
        name = kind[0]
        if name == "continue":
            return [homerows.with_show_art(homerows.card(it)) for it in api.continue_watching(with_up_next=kind[1])]
        if name == "next-up":
            return [homerows.card(it) for it in api.next_up()]
        if name == "watchlist":
            return [homerows.card(it) for it in api.watchlist()]
        if name == "recent":
            lib = kind[1]
            if lib.get("kind") == "shows":
                return [homerows.recent_card(rc) for rc in api.recent_shows(lib.get("id"))]
            page = api.items(homerows.library_query(lib, "added", 24))
            return [homerows.card(it) for it in page.get("items", [])]
        if name == "seasonal":
            page = api.items(dict(kind[2], limit="24"))
            return [homerows.card(it) for it in page.get("items", [])]
        if name == "custom":
            page = api.items(homerows.custom_row_query(kind[3], kind[2]))
            return [homerows.card(it) for it in page.get("items", [])]
        if name == "collection":
            data = api.collection(kind[1]) or {}
            return [homerows.card(it) for it in data.get("items", [])]
        if name == "playlist":
            data = api.playlist(kind[1]) or {}
            return [homerows.card(entry.get("item", {})) for entry in data.get("entries", [])]
        return []

    def _fill_row(self, idx, cards, error):
        if error is not None:
            log.debug("row %d failed: %s", idx, type(error).__name__)
            cards = []
        if idx >= len(self.rows):
            return
        row = self.rows[idx]
        ctrl = self.list_control(self._list_id(idx))
        keep = ctrl.getSelectedPosition() if self._refreshing else 0
        had_focus = self._refreshing and self._focused_once and self._row == idx
        ctrl.reset()
        ctrl.addItems([card_list_item(self.session, card, row["style"], row.get("season_posters", False))
                       for card in cards or []])
        row["cards"] = cards or []
        if keep > 0 and cards:
            ctrl.selectItem(min(keep, len(cards) - 1))
        if had_focus:
            # Kodi drops the focus from a list while it's emptied and refilled (it hides when
            # empty): give it back, or, if the row is now empty (its last card was removed from
            # Continue Watching), to the nearest row with cards.
            order = [idx] + [j for d in range(1, len(self.rows)) for j in (idx + d, idx - d)
                             if 0 <= j < len(self.rows)]
            for j in order:
                if self.rows[j].get("cards"):
                    self._row = j
                    self.focus_when_visible(self._list_id(j))
                    self._update_hero(j)
                    return
        if not self._focused_once:
            # Rows arrive in any order; the first row (in Home's order) with cards takes focus once
            # every row above it has answered.
            for i, r in enumerate(self.rows):
                if "cards" not in r:
                    break
                if r["cards"]:
                    self._focused_once = True
                    self._row = i
                    self.focus_when_visible(self._list_id(i))
                    self._update_hero(i)
                    return
        focused = self._row_at(self.getFocusId())
        if focused is not None:
            self._update_hero(focused)

    # MARK: - background follows focus

    def onFocus(self, control_id):
        idx = self._row_at(control_id)
        if idx is not None:
            self._update_hero(idx)

    def _update_hero(self, idx):
        if idx >= len(self.rows):
            return
        cards = self.rows[idx].get("cards") or []
        pos = self.list_control(self._list_id(idx)).getSelectedPosition()
        if not (0 <= pos < len(cards)):
            return
        card = cards[pos]
        item = card["item"]
        self.set_image(BG_FANART, self.session.art(card.get("backdrop")))
        self.set_image(HERO_LOGO, self.session.art(card.get("logo")))
        self.set_label(HERO_TITLE, "" if card.get("logo") else (item.get("series_title") or item.get("title", "")))
        self.set_label(HERO_INFO, self._hero_info(item))
        self.set_text(HERO_OVERVIEW, item.get("overview") or "")

    def _hero_info(self, item):
        bits = []
        if models.is_episode(item):
            code = models.episode_code(item)
            bits.append(("%s  %s" % (code, item.get("title", ""))).strip())
        if item.get("year"):
            bits.append(str(item["year"]))
        for g in (item.get("genres") or [])[:3]:
            bits.append(g)
        return "  ·  ".join(bits)

    # MARK: - input

    def on_click(self, control_id):
        if control_id == SIDEBAR:
            self._open_place(self.list_control(SIDEBAR).getSelectedPosition())
        elif self._row_at(control_id) is not None:
            self._open_card(self._row_at(control_id))

    def _open_place(self, pos):
        if not (0 <= pos < len(self.places)) or not self.nav:
            return
        place = self.places[pos]
        pid = place[0]
        if pid == "home":
            self.focus_id(ROWS)
        elif pid.startswith("library:"):
            self.nav("library", place[3])
        else:
            self.nav(pid, None)

    def _open_card(self, idx):
        if idx >= len(self.rows) or not self.nav:
            return
        card = self._focused_card(idx)
        if card:
            self.nav("card", card)

    def _focused_card(self, idx):
        cards = self.rows[idx].get("cards") or []
        pos = self.list_control(self._list_id(idx)).getSelectedPosition()
        return cards[pos] if 0 <= pos < len(cards) else None

    def on_action(self, action, code):
        # Kodi handles the key before the add-on hears of it, so the focus here is already where
        # Kodi put it. `self._row` is the row the focus was on before this key.
        before, self._row = self._row, self._row_at(self.getFocusId())
        idx = self._row
        if idx is None:
            return False
        if code in (ACTION_UP, ACTION_DOWN):
            if before is not None and idx != before:
                # Kodi's own navigation already moved to another row (it does on some Kodi
                # versions): just follow it, or Down would move twice.
                self._update_hero(idx)
                return True
            # Kodi didn't move (it doesn't skip the empty slots everywhere): go to the nearest
            # row with cards ourselves; the grouplist scrolls to it.
            step = 1 if code == ACTION_DOWN else -1
            i = idx + step
            while 0 <= i < len(self.rows):
                if self.rows[i].get("cards"):
                    self._row = i
                    self.focus_when_visible(self._list_id(i))
                    self._update_hero(i)
                    break
                i += step
            return True
        if code in MOVE_ACTIONS:
            # Kodi has already moved the focus; the background follows it.
            self._update_hero(idx)
            return False
        card = self._focused_card(idx)
        if card and self.nav and code in ACTION_CONTEXT:
            self.nav("context", {"item": card["item"], "continue_row": self.rows[idx]["source"][0] == "continue",
                                 "on_changed": lambda _item, _act: self.on_return()})
            return True
        if card and self.nav and code in ACTION_PLAY and models.playable(card["item"]):
            self.nav("play", {"item": card["item"], "resume": models.resume_ms(card["item"])})
            return True
        return False

    def on_back(self):
        # Back from a row goes to the sidebar; from the sidebar, leaves the add-on.
        if self.getFocusId() != SIDEBAR:
            self.focus_id(SIDEBAR)
        else:
            self.result = "exit"
            self.close()
