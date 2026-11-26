"""A person's page, as the Apple app's PersonView: their photo, name and "Acting · 14 titles in
your libraries", their part in the focused title over its background, and rows of their Movies,
TV Shows and work Behind the Camera (arc/people.py). It's Home's window with its own skin: the
header stays put, and moving along the rows changes the background and the part."""

from arc import home as homerows
from arc import people

from ..compat import T
from ..log import log
from . import home

PHOTO = 62
NAME = 63
SUMMARY = 64
PART = 65
INITIALS = 66

ROW_TITLES = {"movies": 30279, "shows": 30280, "crew": 30281}
ROLE_NAMES = {"director": 30282, "writer": 30283, "producer": 30284}


class PersonWindow(home.HomeWindow):
    xml = "script-arc-person.xml"
    HERO_SPOT = None    # its rows have no hero above them
    episode_titles = False

    def __init__(self, *args, **kwargs):
        self.person = kwargs.pop("person")   # {"person_id" or "id", "name", "image"?}
        home.HomeWindow.__init__(self, *args, **kwargs)

    def on_init(self):
        name = self.person.get("name", "")
        self.set_label(NAME, name)
        self.set_label(INITIALS, "".join(w[:1] for w in name.split()[:2]).upper())
        if self.person.get("image"):
            self.set_image(PHOTO, self.session.art(self.person["image"]))
        person_id = self.person.get("person_id") or self.person.get("id")
        self.run_async(lambda: self.session.api.person(person_id), self._loaded)

    def on_return(self):
        pass  # their credits don't change while their page is open

    def on_live(self, change):
        pass

    def _loaded(self, page, error):
        if error is not None or not page:
            log.warning("person failed: %s", type(error).__name__ if error else "empty")
            page = {}
        person = page.get("person") or {}
        if person.get("image"):
            self.set_image(PHOTO, self.session.art(person["image"]))
        count = people.title_count(page)
        bits = [person.get("known_for")] if person.get("known_for") else []
        bits.append(T(30276) if count == 1 else T(30277) % count)
        self.set_label(SUMMARY, "  ·  ".join(bits))
        rows = []
        for key, credits in people.rows(page)[:home.MAX_ROWS]:
            rows.append({"id": key, "source": ("person", key), "style": homerows.POSTER, "season_posters": False,
                         "title": key, "credits": credits,
                         "cards": [homerows.card(c.get("item") or {}) for c in credits]})
        if not rows:
            self.set_label(PART, T(30285))
            return
        self.rows = rows
        self._layout_rows()
        for i, row in enumerate(rows):
            self._fill_row(i, row["cards"], None)

    def _row_title(self, row):
        return T(ROW_TITLES.get(row.get("title"), 30279))

    def _update_hero(self, idx):
        """The header stays; the background and the part line follow the focused title."""
        if idx >= len(self.rows):
            return
        row = self.rows[idx]
        pos = self.list_control(self._list_id(idx)).getSelectedPosition()
        if not (0 <= pos < len(row["cards"])):
            return
        self.set_image(home.BG_FANART, self.session.art(row["cards"][pos].get("backdrop")))
        title, character, role = people.part(row["credits"][pos])
        if character:
            title += "  ·  " + T(30278) % character
        elif role:
            title += "  ·  " + (T(ROLE_NAMES[role]) if role in ROLE_NAMES else role.capitalize())
        self.set_label(PART, title)

    def on_back(self):
        self.result = "back"
        self.close()
