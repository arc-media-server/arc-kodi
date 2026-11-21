"""A library's Recommended tab, as the Apple app's: Home's hero and rows, filled with the
server's Recommended rows (arc/recommended.py), under the library's tab pills, without the
sidebar. It is Home's window with a different skin and a different source of rows."""

import time

from arc import recommended

from ..compat import T
from ..log import log
from . import home
from .library import TAB_BASE, TABS, TabsMixin

# The Kodi side's words for arc/recommended.py's title keys.
TITLE_STRINGS = {
    "continue": 30232, "recently_released": 30233, "recently_added": 30234, "start_watching": 30235,
    "because_you_watched": 30236, "top_rated_movies": 30237, "top_rated_shows": 30238,
    "recently_watched": 30239, "recently_watched_episodes": 30240, "rediscover": 30241,
    "more_in_genre": 30242, "top_movies_in_genre": 30243, "top_shows_in_genre": 30244,
    "top_movies_with": 30245, "top_movies_by": 30246, "top_shows_with": 30247, "top_shows_by": 30248,
    "top_unwatched": 30249,
}


class RecommendedWindow(TabsMixin, home.HomeWindow):
    xml = "script-arc-library-rows.xml"
    SIZE_HERO = False   # the hero keeps the skin's height: the tabs sit above it
    ABOVE_ROWS = TABS   # Up from the first row: the library's tabs

    def __init__(self, *args, **kwargs):
        self.library = kwargs.pop("library")
        self.tab = "recommended"
        home.HomeWindow.__init__(self, *args, **kwargs)

    def on_init(self):
        self.show_tabs()
        cached = self.session.recommended.get(self.library.get("id"))
        if cached is not None:
            # Shown at once from the last visit; the fresh rows replace them in place.
            self._show(cached)
            self._refreshing = True
        else:
            self.set_label(home.HERO_TITLE, T(30007))
        self._load()

    def on_live(self, change):
        if change.touches(self.library.get("id")):
            self.on_return()

    def on_return(self):
        # Progress and watched state may have changed: load the rows again, keeping the focus.
        self._refreshing = True
        self._load()

    def _load(self):
        def fetch():
            started = time.time()
            page = self.session.api.recommended(self.library.get("id"))
            return page, int((time.time() - started) * 1000)

        self.run_async(fetch, self._loaded)

    def _loaded(self, result, error):
        if error is not None:
            log.warning("library recommended failed: %s", type(error).__name__)
            if self.rows:
                return  # keep what's showing
            result = ({}, 0)
        page, took = result
        if took >= 1000:
            # Arc took a while: the server's own log says why (its "recommended rows" line).
            log.info("library recommended took %d ms", took)
        started = time.time()
        rows = recommended.rows(page, self.library)[:home.MAX_ROWS]
        self.session.recommended[self.library.get("id")] = rows
        self._show(rows)
        log.debug("library recommended: %d rows, fetched in %d ms, shown in %d ms",
                  len(rows), took, int((time.time() - started) * 1000))

    def _show(self, rows):
        if not rows and not self._refreshing:
            # Nothing to recommend yet: say so, and leave the focus on the tabs.
            self.set_label(home.HERO_TITLE, T(30231))
            self.focus_id(TAB_BASE)
            return
        if self.rows and [r["id"] for r in rows] != [r["id"] for r in self.rows]:
            # Different rows than the ones showing: lay them out afresh.
            self._refreshing = False
            self._focused_once = False
        self.rows = rows
        self._layout_rows()
        for i, row in enumerate(rows):
            self._clear_slot(i, keep=self._bases(row)[0])  # a slot that changed style
            self._fill_row(i, [dict(c) for c in row["cards"]], None)
        for i in range(len(rows), home.MAX_ROWS):
            self._clear_slot(i)
        self._refreshing = False

    def _row_title(self, row):
        key, name = row.get("title") or (None, "")
        if key is None:
            return name or ""
        text = T(TITLE_STRINGS[key])
        return text % name if "%s" in text else text

    def onFocus(self, control_id):
        self.tab_focused(control_id)
        home.HomeWindow.onFocus(self, control_id)

    def on_click(self, control_id):
        if self.tab_at(control_id):
            self.tab_clicked(control_id)
        else:
            home.HomeWindow.on_click(self, control_id)

    def on_back(self):
        self.result = "back"
        self.close()
