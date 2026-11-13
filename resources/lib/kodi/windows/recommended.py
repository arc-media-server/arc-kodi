"""A library's Recommended tab, as the Apple app's: Home's hero and rows, filled with the
server's Recommended rows (arc/recommended.py), under the library's tab pills, without the
sidebar. It is Home's window with a different skin and a different source of rows."""

from arc import recommended

from ..compat import T
from ..log import log
from . import home
from .library import TABS, TabsMixin

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

    def __init__(self, *args, **kwargs):
        self.library = kwargs.pop("library")
        self.tab = "recommended"
        home.HomeWindow.__init__(self, *args, **kwargs)

    def on_init(self):
        self.show_tabs()
        self._load()

    def on_return(self):
        # Progress and watched state may have changed: load the rows again, keeping the focus.
        self._refreshing = True
        self._load()

    def _load(self):
        self.run_async(lambda: self.session.api.recommended(self.library.get("id")), self._loaded)

    def _loaded(self, page, error):
        if error is not None:
            log.warning("library recommended failed: %s", type(error).__name__)
            page = {}
        rows = recommended.rows(page, self.library)[:home.MAX_ROWS]
        if not rows and not self._refreshing:
            # Nothing to recommend yet: say so, and leave the focus on the tabs.
            self.set_label(home.HERO_TITLE, T(30231))
            self.focus_id(TABS)
            return
        self.rows = rows
        self._layout_rows()
        for i, row in enumerate(rows):
            self._fill_row(i, row["cards"], None)
        self._refreshing = False

    def _row_title(self, row):
        key, name = row.get("title") or (None, "")
        if key is None:
            return name or ""
        text = T(TITLE_STRINGS[key])
        return text % name if "%s" in text else text

    def on_click(self, control_id):
        if control_id == TABS:
            self.tab_clicked()
        else:
            home.HomeWindow.on_click(self, control_id)

    def on_back(self):
        self.result = "back"
        self.close()
