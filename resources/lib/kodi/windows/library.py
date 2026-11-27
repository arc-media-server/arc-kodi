"""A library's grid: its titles in a chosen sort and filter, six posters across (its Library tab).
Sort and Filters are Arc menus; paging loads more as you reach the end. A library's Collections
tab, a collection, a playlist, the Watchlist and a person's titles reuse GridWindow with a loader.
The top bar is the Android app's: the heading on the left, with a library's tabs (Recommended,
Library, Collections) beside it; the count and the page's pills on the right. Choosing another tab
closes this window with ("tab", name) and the app opens that one in its place. Sorted by Title, a
library has the Apple and Android apps' A–Z bar down the right."""

import xbmcgui

from arc import browse
from arc.browse import WATCHLIST_SHOWS, WATCHLIST_SORTS
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
PILLS = 110             # the right of the top bar: the count and the pills
TAB_BASE = 121          # slot i: "current" button 121 + 2i, "other" button 122 + 2i
TAB_SLOTS = 3
LETTERS = 140           # the A–Z bar

PAGE_SIZE = 60

# The Kodi side's words for arc/browse.py's sorts.
SORT_NAMES = {"title": 30128, "added": 30250, "released": 30251, "year": 30129, "rating": 30130,
              "runtime": 30252, "watched": 30253, "shuffle": 30288}
DIRECTION_NAMES = {"a_to_z": 30263, "z_to_a": 30264, "newest": 30265, "oldest": 30266, "highest": 30267,
                   "lowest": 30268, "longest": 30269, "shortest": 30270, "recent": 30271, "least_recent": 30272}


def library_tabs(library):
    """A library's tabs, as the Android and Apple apps': Recommended (not for Other videos), Library,
    Collections, and for Other videos, Folders. Always three: the skin draws a first, a middle and
    a last tab (skin/includes.xml, PageHeader)."""
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
        self.set_label(TITLE, self.library.get("name", ""))
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
        # "24 titles" at the right of the top bar, as the Android app's: not on a library's
        # Collections tab (nor the Watchlist, which sets it off).
        self.counted = kwargs.pop("counted", self.tab in (None, "browse"))
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
        text = (T(30604) if count == 1 else T(30605)) % count if count and self.counted else ""
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
            self.refreshed()

        self.run_async(work, done)

    def _show_empty(self):
        self.set_label(EMPTY, T(30106))

    def refreshed(self):
        """Called on the UI side once a refresh has redrawn a changed list."""

    def page_loaded(self, offset):
        """Called on the UI side once a page of the grid has arrived (for a page's header)."""
        if offset == 0 and self.play and self.items:
            self.set_visible(PLAY_ALL, True)
            self.set_visible(SHUFFLE, True)

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

    def grid_columns(self, control_id):
        return (3 if self.style == "thumb" else 6) if control_id == GRID else 0

    def onFocus(self, control_id):
        self.restore_focus(control_id)
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


def channels_name(n):
    """Mono, Stereo, 5.1, 7.1, as the player's audio list words them."""
    n = int(n or 0)
    return T(30214) if n == 1 else T(30215) if n == 2 else ("%d.1" % (n - 1)) if n > 2 else ""


def filter_value_name(key, value):
    """A filter's value as the Filters list and pill show it."""
    if key == "watch_state":
        return T(30581) if value == "played" else T(30582)
    if key == "decade":
        return T(30257) % value if value else ""
    if key == "resolution":
        return browse.resolution_name(value or "")
    if key == "dynamic_range":
        return T(30584) if value == "unknown" else browse.dynamic_range_name(value)
    if key == "video_codec":
        return browse.video_codec_name(value)
    if key == "audio_codec":
        return browse.audio_codec_name(value)
    if key == "audio_channels":
        return channels_name(value)
    return value or ""


class LibraryWindow(GridWindow):
    """A library's Browse grid with Sort and Filter, as the Apple app's (arc/browse.py)."""

    def __init__(self, *args, **kwargs):
        self.query = browse.LibraryQuery()
        self.query.genre = kwargs.pop("genre", None) or None
        self.facets = {}
        self.letter_counts = []     # /items' letters, from the first page
        self.letters = []           # the A–Z bar: (letter, offset of its first title)
        self.generation = 0         # a new sort or filter starts a new one
        kwargs["title"] = kwargs["library"].get("name", "")
        kwargs["paged"] = True
        kwargs["tab"] = "browse"
        kwargs["style"] = library_style(kwargs["library"])
        GridWindow.__init__(self, *args, loader=self._items, **kwargs)

    def on_init(self):
        self.setProperty("arc.style", self.style)
        self.show_tabs()
        # No Play All or Shuffle here, as the Android app's library: Shuffle is a sort.
        self.set_visible(PLAY_ALL, False)
        self.set_visible(SHUFFLE, False)
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
        """As the Android app's: the sort's name ("Title"), and "Filters" ("Filters, 2 on")."""
        self.set_label(SORT, self._sort_name(self.query.sort))
        n = self.query.filter_count
        self.set_label(FILTER, T(30606) % n if n else T(30124))

    def _items(self, offset, limit):
        page = self.session.api.items(self.query.parameters(self.library, offset, limit, letters=offset == 0))
        if offset == 0:
            self.letter_counts = page.get("letters") or []
        return page.get("items", []), page.get("total", 0)

    # MARK: - the A–Z bar

    def page_loaded(self, offset):
        GridWindow.page_loaded(self, offset)
        if offset == 0:
            self._show_letters()

    def refreshed(self):
        self._show_letters()

    def _show_letters(self):
        """Fills the A–Z bar from the first page's counts: only the letters that have titles, in
        the list's order. The skin shows it when there's more than one."""
        jumps = browse.letter_jumps(self.letter_counts, self.query.reversed) if self.query.shows_letters else []
        if jumps == self.letters:
            return
        self.letters = jumps
        ctrl = self.list_control(LETTERS)
        ctrl.reset()
        ctrl.addItems([xbmcgui.ListItem(letter) for letter, _ in jumps])

    def _letter_at(self, position):
        """The bar's letter for a place in the grid: the last whose first title is at or before it."""
        at = 0
        for i, (_, offset) in enumerate(self.letters):
            if offset <= position:
                at = i
        return at

    def _jump(self, index):
        """Select on a letter: loads the titles up to its first one, and a page past it, if the grid
        hasn't reached them (up to 500 a request), then moves the focus there, as the Apple app."""
        if not 0 <= index < len(self.letters):
            return
        target = self.letters[index][1]
        if self.total:
            target = min(target, self.total - 1)
        if target < len(self.items):
            self._land(target)
            return
        if self.loading or self.total is None:
            return
        plan = browse.pages_to_reach(target, len(self.items), self.total, PAGE_SIZE)
        self.loading = True
        generation, have = self.generation, len(self.items)

        def work():
            got = []
            for offset, limit in plan:
                page, _ = self._items(offset, limit)
                got += page
                if not page:
                    break
            return got

        def done(got, error):
            self.loading = False
            if generation != self.generation:
                self._load_more()   # a new sort or filter came while this loaded
                return
            if error is not None:
                log.debug("letter jump failed: %s", type(error).__name__)
                return
            if len(self.items) != have:
                return
            self.items += got
            self.offset = len(self.items)
            self.list_control(GRID).addItems([item_list_item(self.session, it, self.style) for it in got])
            log.debug("letter jump: loaded %d titles in %d requests", len(got), len(plan))
            if target < len(self.items):
                self._land(target)

        self.run_async(work, done)

    def _land(self, position):
        self.list_control(GRID).selectItem(position)
        self._focus_memory.remember(GRID, position, self.grid_columns(GRID))
        self.focus_id(GRID)

    def onFocus(self, control_id):
        GridWindow.onFocus(self, control_id)
        if control_id == LETTERS and self.letters:
            # Onto the bar from the grid: on the letter of the title that had the focus.
            at = self._letter_at(max(self.list_control(GRID).getSelectedPosition(), 0))
            self.list_control(LETTERS).selectItem(at)
            self._focus_memory.remember(LETTERS, at)

    def _show_empty(self):
        self.set_label(EMPTY, T(30262) if self.query.filtered else T(30106))

    def _reset(self):
        self._refresh_pills()
        self.generation += 1
        self.letter_counts = []
        self._show_letters()
        self.items, self.total, self.offset = [], None, 0
        self.list_control(GRID).reset()
        self.set_label(EMPTY, "")
        self._load_more()

    # MARK: - the menus

    def _sort_menu(self):
        keys = [key for key, _ in browse.SORTS]
        # The sort in use names its direction; choosing it again turns it round.
        direction = DIRECTION_NAMES.get(self.query.direction())
        options = [(self._sort_name(k), T(direction) if k == self.query.sort and direction else "")
                   for k in keys]
        choice = menu.choose(T(30123), options, selected=keys.index(self.query.sort))
        if choice >= 0:
            self.query.choose_sort(keys[choice])
            self._reset()

    def _filter_menu(self):
        """Filters, as the web's and the other TV apps': Unwatched Only, then each filter with what
        it's set to, opening its own list (Any, then the choices). The media filters (HDR, formats,
        channels) show only when they'd narrow something (browse.offered)."""
        q = self.query
        any_name = T(30259)
        rows = [("unwatched", T(30254), "")]

        def add(key, title, values, facet=None):
            current = getattr(q, key)
            # How many titles each value has, shown beside it as before.
            counts = {str(v): n for v, n in browse.facet_values(self.facets, facet)} if facet else {}
            rows.append((key, title, filter_value_name(key, current) if current else any_name, values, counts))

        add("watch_state", T(30580), list(browse.WATCH_STATES))
        for key, title, facet in (("genre", T(30255), "genres"), ("decade", T(30256), "decades")):
            if browse.facet_values(self.facets, facet):
                add(key, title, browse.choices(self.facets, facet, getattr(q, key)), facet)
        if browse.shows_resolution(self.library) and browse.facet_values(self.facets, "resolutions"):
            add("resolution", T(30258), browse.choices(self.facets, "resolutions", q.resolution), "resolutions")
        media_titles = {"dynamic_range": T(30583), "video_codec": T(30585), "audio_codec": T(30586),
                        "audio_channels": T(30587)}
        for key, facet in browse.MEDIA_FILTERS:
            if browse.offered(self.facets, facet, getattr(q, key)):
                add(key, media_titles[key], browse.choices(self.facets, facet, getattr(q, key)), facet)
        if q.filtered:
            rows.append(("clear", T(30260), ""))
        choice = menu.choose(T(30124), [(row[1], row[2]) for row in rows],
                             selected=0 if q.unwatched else -1, focus=0)
        if choice < 0:
            return
        key = rows[choice][0]
        if key == "unwatched":
            q.set_unwatched(not q.unwatched)
        elif key == "clear":
            q.clear_filters()
        else:
            title, values, counts = rows[choice][1], rows[choice][3], rows[choice][4]
            current = getattr(q, key)
            options = [any_name] + [(filter_value_name(key, v), str(counts.get(str(v), ""))) for v in values]
            at = 1 + values.index(current) if current in values else 0
            pick = menu.choose(title, options, selected=at)
            if pick < 0:
                return
            value = None if pick == 0 else values[pick - 1]
            if key == "watch_state":
                q.set_watch_state(value)
            else:
                setattr(q, key, value)
        self._reset()

    def on_click(self, control_id):
        if control_id == SORT:
            self._sort_menu()
        elif control_id == FILTER:
            self._filter_menu()
        elif control_id == LETTERS:
            self._jump(self.list_control(LETTERS).getSelectedPosition())
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
        self.set_visible(SORT, len(self.loaded) > 1)

    def _show_empty(self):
        self.set_label(EMPTY, T(30286))

    def _refresh_sort(self):
        self.set_label(SORT, T(30128) if self.by_title else T(30251))

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


class WatchlistWindow(GridWindow):
    """The Watchlist, as the Android app's: its heading, then two pills on the right, what it shows
    (All, Movies, TV Shows) and its order (Date Added, Title, Release Date); no count."""

    SHOW_NAMES = {"all": 30125, "movies": 30279, "shows": 30280}
    SORT_NAMES = {"added": 30250, "title": 30128, "released": 30251}

    def __init__(self, *args, **kwargs):
        self.show, self.sort = "all", "added"
        self.loaded = None      # the Watchlist as Arc sends it, newest first
        kwargs.update(title=T(30082), style="poster", counted=False)
        GridWindow.__init__(self, *args, loader=self._items, **kwargs)

    def forget(self):
        self.loaded = None

    def _items(self, offset, limit):
        if self.loaded is None:
            self.loaded = list(self.session.api.watchlist() or [])
        items = browse.watchlist_view(self.loaded, self.show, self.sort)
        return items, len(items)

    def page_loaded(self, offset):
        if offset == 0:
            self._refresh_pills()

    def _refresh_pills(self):
        self.set_label(SORT, T(self.SHOW_NAMES[self.show]))
        self.set_label(FILTER, T(self.SORT_NAMES[self.sort]))
        shown = bool(self.loaded)
        self.set_visible(SORT, shown)
        self.set_visible(FILTER, shown)

    def _show_empty(self):
        self.set_label(EMPTY, T(30106))

    def on_click(self, control_id):
        if control_id in (SORT, FILTER):
            keys, names = (WATCHLIST_SHOWS, self.SHOW_NAMES) if control_id == SORT else (WATCHLIST_SORTS, self.SORT_NAMES)
            current = self.show if control_id == SORT else self.sort
            choice = menu.choose(T(30082), [T(names[k]) for k in keys], selected=keys.index(current))
            if choice < 0 or keys[choice] == current:
                return
            if control_id == SORT:
                self.show = keys[choice]
            else:
                self.sort = keys[choice]
            self._refresh_pills()
            self.items, self.total, self.offset = [], None, 0
            self.list_control(GRID).reset()
            self.set_label(EMPTY, "")
            self._load_more()
        else:
            GridWindow.on_click(self, control_id)
