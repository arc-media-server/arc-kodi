"""Search: a box and a grid of matches (movies, shows, episodes), as Arc returns them."""

import xbmcgui

from arc import home as homerows

from ..compat import T
from .base import ArcWindow
from .cards import item_list_item

BOX = 100
GRID = 101
EMPTY = 102


class SearchWindow(ArcWindow):
    xml = "script-arc-search.xml"

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self.items = []
        self.nav = None

    def on_init(self):
        self.focus_id(BOX)
        self._ask()

    def _ask(self):
        query = xbmcgui.Dialog().input(T(30080))
        if not query:
            if not self.items:
                self.on_back()
            return
        self.set_label(BOX, query)
        self.run_async(lambda: self.session.api.search(query), self._show)

    def _show(self, data, error):
        self.items = []
        if error is None and isinstance(data, dict):
            for key in ("movies", "shows", "episodes"):
                self.items += data.get(key) or []
        ctrl = self.list_control(GRID)
        ctrl.reset()
        for it in self.items:
            ctrl.addItem(item_list_item(self.session, it, "poster"))
        self.set_label(EMPTY, "" if self.items else T(30106))
        if self.items:
            self.focus_id(GRID)

    def on_click(self, control_id):
        if control_id == BOX:
            self._ask()
        elif control_id == GRID and self.nav:
            pos = self.list_control(GRID).getSelectedPosition()
            if 0 <= pos < len(self.items):
                self.nav("card", homerows.card(self.items[pos]))

    def on_back(self):
        self.result = "back"
        self.close()
