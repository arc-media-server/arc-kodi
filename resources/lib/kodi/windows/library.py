"""A library's grid: its titles in a chosen sort and filter, six posters across (Browse). Sort and
Filter are Arc menus; paging loads more as you reach the end. A library's Collections tab, a
collection, a playlist and a person's titles reuse GridWindow with a loader. A library's tabs
(Recommended, Browse, Collections) are a pill row at the top; choosing another closes this window
with ("tab", name) and the app opens that one in its place."""

import xbmcgui

from arc import browse
from arc import home as homerows
from arc import models

from ..compat import T
from ..log import log
from . import menu
from .base import ACTION_CONTEXT, ACTION_PLAY, ArcWindow
from .cards import item_list_item, set_progress, update_list_item

GRID = 100
TITLE = 101
SORT = 102
FILTER = 103
COUNT = 104
EMPTY = 105
OVERVIEW = 107
PLAY_ALL = 108
SHUFFLE = 109
TABS = 120
TAB_BASE = 121          # slot i: "current" button 121 + 2i, "other" button 122 + 2i
TAB_SLOTS = 3

PAGE_SIZE = 60

# The Kodi side's words for arc/browse.py's sorts.
SORT_NAMES = {"title": 30128, "added": 30250, "released": 30251, "year": 30129, "rating": 30130,
              "runtime": 30252, "watched": 30253}
DIRECTION_NAMES = {"a_to_z": 30263, "z_to_a": 30264, "newest": 30265, "oldest": 30266, "highest": 30267,
                   "lowest": 30268, "longest": 30269, "shortest": 30270, "recent": 30271, "least_recent": 30272}


def library_tabs(library):
    """A library's tabs, as the Apple app's: Recommended (not for Other videos), Browse, Collections,
    and for Other videos, Folders."""
    videos = library.get("kind") == "videos"
    tabs = [] if videos else [("recommended", T(30120))]
    tabs += [("browse", T(30121)), ("collections", T(30122))]
    return tabs + ([("folders", T(30273))] if videos else [])


def library_style(library):
    """Other videos show as wide cards (their pictures are stills), the rest as posters."""
    return "thumb" if library.get("kind") == "videos" else "poster"


class TabsMixin(object):
    """The tab pills for a window showing one of a library's tabs (`self.library`, `self.tab`)."""

    def show_tabs(self):
        self.tabs = library_tabs(self.library)
        for slot in range(TAB_SLOTS):
            if slot < len(self.tabs):
                key, name = self.tabs[slot]
                self.set_label(TAB_BASE + 2 * slot, name)
                self.set_label(TAB_BASE + 2 * slot + 1, name)
                self.setProperty("arc.tab%d" % slot, "current" if key == self.tab else "other")
            else:
                self.setProperty("arc.tab%d" % slot, "")

    def tab_at(self, control_id):
        """The tab key a tab button stands for, or None."""
        slot = (control_id - TAB_BASE) // 2
        if TAB_BASE <= control_id < TAB_BASE + 2 * TAB_SLOTS and slot < len(getattr(self, "tabs", [])):
            return self.tabs[slot][0]
        return None

    def tab_clicked(self, control_id):
        key = self.tab_at(control_id)
        if key and key != self.tab:
            self.result = ("tab", key)
            self.close()

    def tab_focused(self, control_id):
        """Coming up into the tabs lands on the one showing, as the Apple app's pill bar."""
        into = self.tab_at(control_id) is not None
        if into and not getattr(self, "_in_tabs", False):
            slot = [k for k, _ in self.tabs].index(self.tab)
            current = TAB_BASE + 2 * slot
            if control_id != current:
                self.focus_id(current)
        self._in_tabs = into


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
        # Play All and Shuffle: play(shuffle, item_ids) plays the grid's titles, in the order
        # shown, through a play queue.
        self.play = kwargs.pop("play", None)
        ArcWindow.__init__(self, *args, **kwargs)
        self.items = []
        self.total = None
        self.offset = 0
        self.loading = False
        self.nav = None

    def on_init(self):
        self.setProperty("arc.style", self.style)
        self.set_label(TITLE, self.title)
        self.set_visible(SORT, False)
        self.set_visible(FILTER, False)
        self.set_visible(PLAY_ALL, False)
        self.set_visible(SHUFFLE, False)
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
                if offset == 0 and self.getFocusId() not in (SORT, FILTER) and self.tab_at(self.getFocusId()) is None:
                    # The first page takes the focus, unless it's on the pills (a new sort or
                    # filter keeps it there). Kodi refuses focus until the cards are drawn.
                    self.focus_when_visible(GRID)
            self.page_loaded(offset)
            self._show_count()

        self.run_async(lambda: self.loader(offset, PAGE_SIZE), done)

    def _show_count(self):
        count = self.total or len(self.items)
        text = str(count) if count else ""
        if self.library is not None:
            text = "  ·  ".join(t for t in (self.library.get("name", ""), text) if t)
        self.set_label(COUNT, text)

    # MARK: - refreshing

    def on_return(self):
        # Back from a title or the video: watched state and progress may have changed.
        self.refresh()

    def on_live(self, change):
        library = self.library or getattr(self, "folder_library", None)
        if change.touches((library or {}).get("id")):
            self.refresh()

    def forget(self):
        """Drops anything a loader keeps, before a refresh (CollectionWindow keeps its titles)."""

    def refresh(self):
        """Loads the titles shown again and updates the grid in place, keeping the focus: the same
        titles get their new state (watched, progress, new episodes); a changed list (a title
        added or gone) is redrawn on the title that had the focus."""
        if self.loading or not self.loader or not self.items:
            return
        self.loading = True
        self.forget()
        wanted = max(len(self.items), PAGE_SIZE)

        def work():
            if not self.paged:
                return self.loader(0, PAGE_SIZE)
            items, total = [], None
            while len(items) < wanted:
                page, total = self.loader(len(items), PAGE_SIZE)
                items += page
                if not page or (total is not None and len(items) >= total):
                    break
            return items, total

        def done(result, error):
            self.loading = False
            if error is not None or not result:
                log.debug("grid refresh failed: %s", type(error).__name__ if error else "empty")
                return
            items, total = result
            ctrl = self.list_control(GRID)
            old_ids = [it.get("id") for it in self.items]
            new_ids = [it.get("id") for it in items]
            if new_ids == old_ids:
                for i, it in enumerate(items):
                    li = ctrl.getListItem(i)
                    update_list_item(li, it)
                    set_progress(li, it)
                self.items, self.total = items, total
                return
            pos = ctrl.getSelectedPosition()
            focused = old_ids[pos] if 0 <= pos < len(old_ids) else None
            had_focus = self.getFocusId() == GRID
            self.items, self.total, self.offset = items, total, len(items)
            ctrl.reset()
            ctrl.addItems([item_list_item(self.session, it, self.style) for it in items])
            if items:
                ctrl.selectItem(new_ids.index(focused) if focused in new_ids else min(max(pos, 0), len(items) - 1))
                self.set_label(EMPTY, "")
                if had_focus:
                    # Kodi drops the focus from a list while it's emptied and refilled.
                    self.focus_when_visible(GRID)
            else:
                self._show_empty()
            self._show_count()
            log.debug("grid redrawn: %d titles", len(items))

        self.run_async(work, done)

    def _show_empty(self):
        self.set_label(EMPTY, T(30106))

    def page_loaded(self, offset):
        """Called on the UI side once a page of the grid has arrived (for a page's header)."""
        if offset == 0 and self.play and self.items:
            self.set_visible(PLAY_ALL, True)
            self.set_visible(SHUFFLE, True)
            try:
                self.getControl(TITLE).setWidth(880)  # the name stops short of the pills
            except Exception:
                pass

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

    def onFocus(self, control_id):
        if self.library is not None:
            self.tab_focused(control_id)

    def on_click(self, control_id):
        if control_id in (PLAY_ALL, SHUFFLE) and self.play:
            self.play(control_id == SHUFFLE, [it.get("id") for it in self.items if it.get("id")])
        elif self.tab_at(control_id):
            self.tab_clicked(control_id)
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
    """A library's Browse grid with Sort and Filter, as the Apple app's (arc/browse.py)."""

    def __init__(self, *args, **kwargs):
        self.query = browse.LibraryQuery()
        self.query.genre = kwargs.pop("genre", None) or None
        self.facets = {}
        kwargs["title"] = kwargs["library"].get("name", "")
        kwargs["paged"] = True
        kwargs["tab"] = "browse"
        kwargs["style"] = library_style(kwargs["library"])
        GridWindow.__init__(self, *args, loader=self._items, **kwargs)

    def on_init(self):
        self.setProperty("arc.style", self.style)
        self.set_label(TITLE, self.library.get("name", ""))
        self.show_tabs()
        self._refresh_pills()
        self.set_visible(SORT, True)
        self.set_visible(FILTER, True)
        self._load_more()
        self.run_async(lambda: self.session.api.facets(self.library.get("id")), self._got_facets)

    def _got_facets(self, facets, error):
        if error is not None:
            log.debug("library facets failed: %s", type(error).__name__)
            return
        self.facets = facets or {}

    # MARK: - the pills

    def _sort_name(self, key):
        return T(SORT_NAMES[dict(browse.SORTS)[key]]) if key in dict(browse.SORTS) else key

    def _refresh_pills(self):
        self.set_label(SORT, "%s: %s" % (T(30123), self._sort_name(self.query.sort)))
        kind, value = self.query.filter_name()
        names = {"all": T(30125), "filtered": T(30261), "unwatched": T(30126), "genre": value,
                 "decade": T(30257) % value if value else "", "resolution": browse.resolution_name(value or "")}
        self.set_label(FILTER, "%s: %s" % (T(30124), names[kind]))

    def _items(self, offset, limit):
        page = self.session.api.items(self.query.parameters(self.library, offset, limit))
        return page.get("items", []), page.get("total", 0)

    def _show_empty(self):
        self.set_label(EMPTY, T(30262) if self.query.filtered else T(30106))

    def _reset(self):
        self._refresh_pills()
        self.items, self.total, self.offset = [], None, 0
        self.list_control(GRID).reset()
        self.set_label(EMPTY, "")
        self._load_more()

    # MARK: - the menus

    def _sort_menu(self):
        keys = [key for key, _ in browse.SORTS]
        # The sort in use names its direction; choosing it again turns it round.
        options = [(self._sort_name(k), T(DIRECTION_NAMES[self.query.direction()]) if k == self.query.sort else "")
                   for k in keys]
        choice = menu.choose(T(30123), options, selected=keys.index(self.query.sort))
        if choice >= 0:
            self.query.choose_sort(keys[choice])
            self._reset()

    def _filter_menu(self):
        q = self.query
        rows = [("unwatched", T(30254), "")]
        facet_rows = [("genre", T(30255), "genres", lambda v: v), ("decade", T(30256), "decades", lambda v: T(30257) % v)]
        if browse.shows_resolution(self.library):
            facet_rows.append(("resolution", T(30258), "resolutions", browse.resolution_name))
        namers = {}
        for key, title, facet, name in facet_rows:
            if browse.facet_values(self.facets, facet):
                current = getattr(q, key)
                rows.append((key, title, name(current) if current else T(30259)))
                namers[key] = (title, facet, name)
        if q.filtered:
            rows.append(("clear", T(30260), ""))
        choice = menu.choose(T(30124), [(title, detail) for _, title, detail in rows],
                             selected=0 if q.unwatched else -1, focus=0)
        if choice < 0:
            return
        key = rows[choice][0]
        if key == "unwatched":
            q.unwatched = not q.unwatched
        elif key == "clear":
            q.clear_filters()
        else:
            title, facet, name = namers[key]
            values = browse.facet_values(self.facets, facet)
            current = getattr(q, key)
            options = [T(30259)] + [(name(v), str(n)) for v, n in values]
            at = 1 + [v for v, _ in values].index(current) if current in [v for v, _ in values] else 0
            pick = menu.choose(title, options, selected=at)
            if pick < 0:
                return
            setattr(q, key, None if pick == 0 else values[pick - 1][0])
        self._reset()

    def on_click(self, control_id):
        if control_id == SORT:
            self._sort_menu()
        elif control_id == FILTER:
            self._filter_menu()
        else:
            GridWindow.on_click(self, control_id)


class FolderWindow(GridWindow):
    """An Other videos library's folders, as the Apple app's Folders tab: a folder's subfolders,
    then its videos. At the top it's the library's Folders tab, with the tab pills; a folder
    opens in a window of its own, so Back goes up a level."""

    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop("path", "")
        library = kwargs["library"]
        kwargs.setdefault("title", library.get("name", ""))
        kwargs["style"] = "thumb"
        if self.path:
            kwargs["library"] = None  # inside a folder: its name, no tabs
            self.folder_library = library
        else:
            kwargs["tab"] = "folders"
            self.folder_library = library
        GridWindow.__init__(self, *args, loader=self._items, **kwargs)

    def _items(self, offset, limit):
        page = self.session.api.folders(self.folder_library.get("id"), self.path)
        folders = [{"id": "folder:" + (f.get("path") or ""), "kind": "folder", "title": f.get("name", ""),
                    "count": f.get("count") or 0, "path": f.get("path") or "",
                    "images": {"primary": f.get("cover")} if f.get("cover") else {}}
                   for f in page.get("folders") or []]
        items = folders + list(page.get("items") or [])
        return items, len(items)

    def on_click(self, control_id):
        if control_id == GRID and self.nav:
            pos = self.list_control(GRID).getSelectedPosition()
            if 0 <= pos < len(self.items) and self.items[pos].get("kind") == "folder":
                folder = self.items[pos]
                self.nav("folder", {"library": self.folder_library, "path": folder["path"], "title": folder["title"]})
                return
        GridWindow.on_click(self, control_id)


class CollectionWindow(GridWindow):
    """A collection's page, as the Apple app's: its name, its overview, and its titles in release
    order or by title (the Sort pill)."""

    def __init__(self, *args, **kwargs):
        self.collection_id = kwargs.pop("collection_id")
        self.by_title = False
        self.overview = ""
        self.loaded = None      # the collection's titles, in the server's (release) order
        kwargs["paged"] = False
        GridWindow.__init__(self, *args, loader=self._items, **kwargs)

    def on_init(self):
        GridWindow.on_init(self)
        self._refresh_sort()

    def forget(self):
        self.loaded = None

    def _items(self, offset, limit):
        if self.loaded is None:
            page = self.session.api.collection(self.collection_id) or {}
            self.loaded = list(page.get("items") or [])
            info = page.get("collection") or {}
            self.overview = info.get("overview") or ""
            if info.get("title"):
                self.title = info["title"]
        items = sorted(self.loaded, key=lambda it: (it.get("sort_title") or it.get("title") or "").lower()) \
            if self.by_title else list(self.loaded)
        return items, len(items)

    def page_loaded(self, offset):
        GridWindow.page_loaded(self, offset)
        if offset == 0:
            self._show_header()

    def _show_header(self):
        self.set_label(TITLE, self.title)
        if self.overview:
            self.set_text(OVERVIEW, self.overview)
            try:
                # Room for the overview: the grid starts under it.
                self.getControl(GRID).setPosition(72, 250)
                self.getControl(GRID).setHeight(800)
            except Exception:
                pass
        if len(self.loaded) > 1:
            try:
                self.getControl(SORT).setPosition(1460, 40)  # in Filter's place, right of Shuffle
            except Exception:
                pass
        self.set_visible(SORT, len(self.loaded) > 1)

    def _show_empty(self):
        self.set_label(EMPTY, T(30286))

    def _refresh_sort(self):
        self.set_label(SORT, "%s: %s" % (T(30123), T(30128) if self.by_title else T(30251)))

    def on_click(self, control_id):
        if control_id == SORT:
            choice = menu.choose(T(30123), [T(30251), T(30128)], selected=1 if self.by_title else 0)
            if choice >= 0 and (choice == 1) != self.by_title:
                self.by_title = choice == 1
                self._refresh_sort()
                self.items, self.total, self.offset = [], None, 0
                self.list_control(GRID).reset()
                GridWindow._load_more(self)
        else:
            GridWindow.on_click(self, control_id)
