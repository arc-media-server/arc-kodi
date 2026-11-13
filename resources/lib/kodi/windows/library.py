"""A library's grid: its titles in a chosen sort and filter, six posters across (Browse). Sort and
Filter are Arc menus; paging loads more as you reach the end. A library's Collections tab, a
collection, a playlist and a person's titles reuse GridWindow with a loader. A library's tabs
(Recommended, Browse, Collections) are a pill row at the top; choosing another closes this window
with ("tab", name) and the app opens that one in its place."""

import xbmcgui

from arc import home as homerows
from arc import models

from ..compat import T
from ..log import log
from . import menu
from .base import ACTION_CONTEXT, ACTION_PLAY, ArcWindow
from .cards import item_list_item, update_list_item

GRID = 100
TITLE = 101
SORT = 102
FILTER = 103
COUNT = 104
EMPTY = 105
TABS = 120
TABS_BACK = 119

PAGE_SIZE = 60

SORTS = [("added", T(30127)), ("title", T(30128)), ("year", T(30129)), ("rating", T(30130))]


def library_tabs(library):
    """A library's tabs, as the Apple app's: Recommended (not for Other videos), Browse, Collections."""
    tabs = [] if library.get("kind") == "videos" else [("recommended", T(30120))]
    return tabs + [("browse", T(30121)), ("collections", T(30122))]


class TabsMixin(object):
    """The tab pills for a window showing one of a library's tabs (`self.library`, `self.tab`)."""

    def show_tabs(self):
        from .base import list_item
        self.tabs = library_tabs(self.library)
        ctrl = self.list_control(TABS)
        ctrl.reset()
        for key, name in self.tabs:
            ctrl.addItem(list_item(name, props={"current": "1" if key == self.tab else ""}))
        ctrl.selectItem([k for k, _ in self.tabs].index(self.tab))
        try:
            self.getControl(TABS_BACK).setWidth(len(self.tabs) * 240 + (len(self.tabs) - 1) * 12)
        except Exception:
            pass

    def tab_clicked(self):
        key = self.tabs[self.list_control(TABS).getSelectedPosition()][0]
        if key != self.tab:
            self.result = ("tab", key)
            self.close()


class GridWindow(TabsMixin, ArcWindow):
    """A grid filled by a `loader(offset, limit) -> (items, total)` callback; with `library` and
    `tab`, one of that library's tabs (its Collections), with the tab pills."""

    xml = "script-arc-grid.xml"

    def __init__(self, *args, **kwargs):
        self.title = kwargs.pop("title", "")
        self.loader = kwargs.pop("loader", None)
        self.style = kwargs.pop("style", "poster")
        self.paged = kwargs.pop("paged", False)
        self.library = kwargs.pop("library", None)
        self.tab = kwargs.pop("tab", None)
        self.open_item = kwargs.pop("open_item", None)  # for cards that aren't titles (collections)
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
        if self.library is not None:
            self.show_tabs()
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
            text = str(count) if count else ""
            if self.library is not None:
                text = "  ·  ".join(t for t in (self.library.get("name", ""), text) if t)
            self.set_label(COUNT, text)

        self.run_async(lambda: self.loader(offset, PAGE_SIZE), done)

    def _show_empty(self):
        self.set_label(EMPTY, T(30106))

    def on_action(self, action, code):
        if code in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN) and self.getFocusId() == GRID:
            pos = self.list_control(GRID).getSelectedPosition()
            if self.total is not None and len(self.items) < self.total and pos >= len(self.items) - 12:
                self._load_more()
        if self.getFocusId() == GRID and self.nav and (code in ACTION_CONTEXT or code in ACTION_PLAY):
            ctrl = self.list_control(GRID)
            pos = ctrl.getSelectedPosition()
            if 0 <= pos < len(self.items):
                item = self.items[pos]
                if code in ACTION_CONTEXT:
                    self.nav("context", {"item": item,
                                         "on_changed": lambda it, _act: update_list_item(ctrl.getListItem(pos), it)})
                    return True
                if models.playable(item):
                    self.nav("play", {"item": item, "resume": models.resume_ms(item)})
                    return True
        return False

    def on_click(self, control_id):
        if control_id == TABS:
            self.tab_clicked()
        elif control_id == GRID and self.nav:
            pos = self.list_control(GRID).getSelectedPosition()
            if 0 <= pos < len(self.items):
                if self.open_item:
                    self.open_item(self.items[pos])
                else:
                    self.nav("card", homerows.card(self.items[pos]))

    def on_back(self):
        self.result = "back"
        self.close()


class LibraryWindow(GridWindow):
    """A library's Browse grid with Sort and Filter."""

    def __init__(self, *args, **kwargs):
        self.sort = "added"
        self.filter = {}
        kwargs["title"] = kwargs["library"].get("name", "")
        kwargs["paged"] = True
        kwargs["tab"] = "browse"
        GridWindow.__init__(self, *args, loader=self._items, **kwargs)

    def on_init(self):
        self.set_label(TITLE, self.library.get("name", ""))
        self.show_tabs()
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
            current = [key for key, _ in SORTS].index(self.sort) if self.sort in dict(SORTS) else -1
            choice = menu.choose(T(30123), [name for _, name in SORTS], selected=current)
            if choice >= 0:
                self.sort = SORTS[choice][0]
                self._refresh_pills()
                self._reset()
        elif control_id == FILTER:
            choice = menu.choose(T(30124), [T(30125), T(30126)], selected=1 if self.filter.get("unwatched") else 0)
            if choice >= 0:
                self.filter = {} if choice == 0 else {"unwatched": True}
                self._refresh_pills()
                self._reset()
        else:
            GridWindow.on_click(self, control_id)
