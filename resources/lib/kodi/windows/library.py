"""A library's grid: its titles in a chosen sort and filter, six posters across (Browse). Sort and
Filter are dialogs; paging loads more as you reach the end. Collections, a playlist, a person's
titles and search results reuse GridWindow with a loader."""

import xbmc
import xbmcgui

from arc import home as homerows

from ..compat import T
from ..log import log
from .base import ArcWindow
from .cards import item_list_item

GRID = 100
TITLE = 101
SORT = 102
FILTER = 103
COUNT = 104
EMPTY = 105

PAGE_SIZE = 60

SORTS = [("added", T(30127)), ("title", T(30128)), ("year", T(30129)), ("rating", T(30130))]


class GridWindow(ArcWindow):
    """A grid filled by a `loader(offset, limit) -> (items, total)` callback."""

    xml = "script-arc-grid.xml"

    def __init__(self, *args, **kwargs):
        self.title = kwargs.pop("title", "")
        self.loader = kwargs.pop("loader", None)
        self.style = kwargs.pop("style", "poster")
        self.paged = kwargs.pop("paged", False)
        ArcWindow.__init__(self, *args, **kwargs)
        self.items = []
        self.total = None
        self.offset = 0
        self.loading = False
        self.nav = None

    def on_init(self):
        self.set_label(TITLE, self.title)
        self.set_visible(SORT, False)
        self.set_visible(FILTER, False)
        self._load_more()

    def _load_more(self):
        if self.loading or (self.total is not None and len(self.items) >= self.total):
            return
        self.loading = True
        offset = self.offset

        def done(result, error):
            self.loading = False
            if error is not None:
                log.debug("grid load failed: %s", type(error).__name__)
                self._show_empty()
                return
            items, total = result
            self.total = total
            self.offset = offset + len(items)
            self.items += items
            ctrl = self.list_control(GRID)
            for it in items:
                ctrl.addItem(item_list_item(self.session, it, self.style))
            if not self.items:
                self._show_empty()
            else:
                self.set_label(EMPTY, "")
                if offset == 0:
                    self.focus_id(GRID)
            count = self.total or len(self.items)
            self.set_label(COUNT, str(count) if count else "")

        self.run_async(lambda: self.loader(offset, PAGE_SIZE), done)

    def _show_empty(self):
        self.set_label(EMPTY, T(30106))

    def on_action(self, action, code):
        if code in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN) and self.getFocusId() == GRID:
            pos = self.list_control(GRID).getSelectedPosition()
            if self.total is not None and len(self.items) < self.total and pos >= len(self.items) - 12:
                self._load_more()
        return False

    def on_click(self, control_id):
        if control_id == GRID and self.nav:
            pos = self.list_control(GRID).getSelectedPosition()
            if 0 <= pos < len(self.items):
                self.nav("card", homerows.card(self.items[pos]))

    def on_back(self):
        self.result = "back"
        self.close()


class LibraryWindow(GridWindow):
    """A library's Browse grid with Sort and Filter."""

    def __init__(self, *args, **kwargs):
        self.library = kwargs.pop("library")
        self.sort = "added"
        self.filter = {}
        kwargs["title"] = self.library.get("name", "")
        kwargs["paged"] = True
        GridWindow.__init__(self, *args, loader=self._items, **kwargs)

    def on_init(self):
        self.set_label(TITLE, self.library.get("name", ""))
        self._refresh_pills()
        self.set_visible(SORT, True)
        self.set_visible(FILTER, True)
        self._load_more()

    def _refresh_pills(self):
        self.set_label(SORT, "%s: %s" % (T(30123), dict(SORTS).get(self.sort, "")))
        self.set_label(FILTER, "%s: %s" % (T(30124), T(30126) if self.filter.get("unwatched") else T(30125)))

    def _items(self, offset, limit):
        q = homerows.library_query(self.library, self.sort, limit, offset=offset,
                                   extra={"unwatched": "1"} if self.filter.get("unwatched") else None)
        page = self.session.api.items(q)
        return page.get("items", []), page.get("total", 0)

    def _reset(self):
        self.items, self.total, self.offset = [], None, 0
        self.list_control(GRID).reset()
        self._load_more()

    def on_click(self, control_id):
        if control_id == SORT:
            choice = xbmcgui.Dialog().select(T(30123), [name for _, name in SORTS])
            if choice >= 0:
                self.sort = SORTS[choice][0]
                self._refresh_pills()
                self._reset()
        elif control_id == FILTER:
            choice = xbmcgui.Dialog().select(T(30124), [T(30125), T(30126)])
            if choice >= 0:
                self.filter = {} if choice == 0 else {"unwatched": True}
                self._refresh_pills()
                self._reset()
        else:
            GridWindow.on_click(self, control_id)
