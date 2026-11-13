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
from .base import ArcWindow, list_item
from .cards import card_list_item

MAX_ROWS = 12
ROW_BASE = 3000      # row list control ids: 3001..3012
TITLE_BASE = 3100    # row title label ids:  3101..3112
GROUP_BASE = 3200    # row group ids:         3201..3212

SIDEBAR = 50
BG_PRIMARY = 60
BG_FANART = 61
HERO_LOGO = 62
HERO_TITLE = 63
HERO_INFO = 64


class HomeWindow(ArcWindow):
    xml = "script-arc-home.xml"

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self.rows = []            # resolved row specs with their loaded cards
        self.places = []
        self.nav = None           # a callback the app sets: nav(kind, payload)

    def on_init(self):
        self._build_sidebar()
        self.rows = self.session.home_rows()[:MAX_ROWS]
        self._layout_rows()
        self._load_rows()
        self.focus_id(ROW_BASE + 1)

    # MARK: - sidebar

    def _build_sidebar(self):
        libs = self.session.ordered_libraries()
        watchlist_at = min(max(int((self.session.prefs or {}).get("watchlist_position") or 0), 0), len(libs))
        places = [("search", T(30080), "search"), ("home", T(30081), "home")]
        middle = []
        for lib in libs:
            icon = {"shows": "tv", "videos": "video"}.get(lib.get("kind"), "film")
            middle.append(("library:%s" % lib.get("id"), lib.get("name", ""), icon, lib))
        middle.insert(watchlist_at, ("watchlist", T(30082), "bookmark", None))
        places += middle
        places += [("playlists", T(30083), "list"), ("settings", T(30084), "settings")]
        self.places = places
        ctrl = self.list_control(SIDEBAR)
        ctrl.reset()
        for place in places:
            ctrl.addItem(list_item(place[1], props={"icon": place[2], "place": place[0]}))

    # MARK: - rows

    def _layout_rows(self):
        for i in range(MAX_ROWS):
            group = GROUP_BASE + 1 + i
            if i < len(self.rows):
                self.set_label(TITLE_BASE + 1 + i, self._row_title(self.rows[i]))
                self.set_visible(group, True)
            else:
                self.set_visible(group, False)

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
        ctrl = self.list_control(ROW_BASE + 1 + idx)
        ctrl.reset()
        for card in cards or []:
            ctrl.addItem(card_list_item(self.session, card, row["style"], row.get("season_posters", False)))
        self.rows[idx]["cards"] = cards or []
        if not cards:
            self.set_visible(GROUP_BASE + 1 + idx, False)

    # MARK: - background follows focus

    def onFocus(self, control_id):
        if ROW_BASE < control_id <= ROW_BASE + MAX_ROWS:
            self._update_hero(control_id - ROW_BASE - 1)

    def _update_hero(self, idx):
        if idx >= len(self.rows):
            return
        cards = self.rows[idx].get("cards") or []
        pos = self.list_control(ROW_BASE + 1 + idx).getSelectedPosition()
        if not (0 <= pos < len(cards)):
            return
        card = cards[pos]
        item = card["item"]
        self.set_image(BG_FANART, self.session.art(card.get("backdrop")))
        self.set_image(HERO_LOGO, self.session.art(card.get("logo")))
        self.set_label(HERO_TITLE, "" if card.get("logo") else (item.get("series_title") or item.get("title", "")))
        self.set_text(HERO_INFO, self._hero_info(item))

    def _hero_info(self, item):
        bits = []
        if item.get("year"):
            bits.append(str(item["year"]))
        for g in (item.get("genres") or [])[:3]:
            bits.append(g)
        return "  ·  ".join(bits)

    # MARK: - input

    def on_click(self, control_id):
        if control_id == SIDEBAR:
            self._open_place(self.list_control(SIDEBAR).getSelectedPosition())
        elif ROW_BASE < control_id <= ROW_BASE + MAX_ROWS:
            self._open_card(control_id - ROW_BASE - 1)

    def _open_place(self, pos):
        if not (0 <= pos < len(self.places)) or not self.nav:
            return
        place = self.places[pos]
        pid = place[0]
        if pid == "home":
            self.focus_id(ROW_BASE + 1)
        elif pid.startswith("library:"):
            self.nav("library", place[3])
        else:
            self.nav(pid, None)

    def _open_card(self, idx):
        if idx >= len(self.rows) or not self.nav:
            return
        cards = self.rows[idx].get("cards") or []
        pos = self.list_control(ROW_BASE + 1 + idx).getSelectedPosition()
        if 0 <= pos < len(cards):
            self.nav("card", cards[pos])

    def on_action(self, action, code):
        from .base import ACTION_CONTEXT
        if code in ACTION_CONTEXT:
            cid = self.getFocusId()
            if ROW_BASE < cid <= ROW_BASE + MAX_ROWS and self.nav:
                idx = cid - ROW_BASE - 1
                cards = self.rows[idx].get("cards") or []
                pos = self.list_control(cid).getSelectedPosition()
                if 0 <= pos < len(cards):
                    self.nav("context", cards[pos])
                return True
        return False

    def on_back(self):
        # Back from a row goes to the sidebar; from the sidebar, leaves the add-on.
        if self.getFocusId() != SIDEBAR:
            self.focus_id(SIDEBAR)
        else:
            self.result = "exit"
            self.close()
