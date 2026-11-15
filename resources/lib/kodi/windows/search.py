"""Search, as the Apple app's, with PM4K's keyboard: Arc's own keys at the left for a remote, and
above them the search box, a Kodi text field (a keyboard types straight into it while it has focus,
OK opens Kodi's keyboard, phone remotes type into it). The matches are in rows at the right:
Movies, TV Shows, Episodes, Collections, People and Genres. Arc searches once typing pauses. The
words and rows are arc/search.py's; this draws them.

Kodi reports each change to the box as a click on it. (Keys can't be caught in the window instead:
Kodi runs its own shortcuts for some letters, S for the power menu among them, before a window
hears of them; a text field with focus gets them all.)"""

import xbmc

from arc import home as homerows
from arc import models
from arc import search

from ..compat import T
from ..log import log
from .base import ACTION_BACK, ACTION_CONTEXT, ACTION_PLAY, ArcWindow, list_item
from .cards import item_list_item, update_list_item

BOX = 100
MESSAGE = 102
KEYS = 200
SPACE_KEY, DELETE_KEY, CLEAR_KEY = 210, 211, 212
RESULTS = 300

# Each row's list and title, in arc/search.py's ROWS order.
ROW_IDS = {"movies": (310, 311, 30279), "shows": (320, 321, 30280), "episodes": (330, 331, 30292),
           "collections": (340, 341, 30122), "people": (350, 351, 30319), "genres": (360, 361, 30161)}

A_REMOTE_0, A_REMOTE_9 = 58, 67     # a remote's number keys
PAUSE = 0.35                        # seconds of quiet before searching, as the Apple app


class SearchWindow(ArcWindow):
    xml = "script-arc-search.xml"

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self.text = ""
        self.rows = {}          # list id -> (kind, entries)
        self.searched = None    # the query the rows show
        self.generation = 0
        self.nav = None

    def on_init(self):
        keys = self.list_control(KEYS)
        keys.reset()
        keys.addItems([list_item(k) for k in search.KEYS])
        for kind, (_list_id, title_id, name) in ROW_IDS.items():
            self.set_label(title_id, T(name))
        self._show_text()
        self.focus_id(KEYS)

    # MARK: - typing

    def _type(self, key):
        text = search.edit(self.text, key)
        if text == self.text:
            return
        self.text = text
        self._show_text()
        self._search_soon()

    def _show_text(self):
        try:
            self.getControl(BOX).setText(self.text)
        except Exception:
            pass

    def on_live(self, change):
        # The same search again: watched marks, new titles or ones gone.
        if self.searched and change.touches():
            self._search_soon()

    def _box_changed(self):
        """What's typed into the search box (a keyboard, Kodi's keyboard, a phone)."""
        try:
            text = self.getControl(BOX).getText()[:search.MAX_LENGTH]
        except Exception:
            return
        if text != self.text:
            self.text = text
            self._search_soon()

    def _search_soon(self):
        """Searches once typing has paused; a newer key cancels the wait (and ignores the answer
        to an older one)."""
        self.generation += 1
        generation = self.generation
        q = search.query(self.text)
        if q is None:
            self._show(None, None, None)
            return

        def work():
            if xbmc.Monitor().waitForAbort(PAUSE) or generation != self.generation:
                return None
            return self.session.api.search(q)

        def done(data, error):
            if generation == self.generation:
                self._show(q, data, error)

        self.run_async(work, done)

    # MARK: - the matches

    def _show(self, q, data, error):
        self.searched = q
        self.rows = {}
        rows = search.rows(data) if error is None else []
        if error is not None:
            log.warning("search failed: %s", type(error).__name__)
        elif q:
            log.debug("search: %d rows", len(rows))
        filled = {}
        for kind, style, entries in rows:
            list_id = ROW_IDS[kind][0]
            filled[list_id] = (kind, style, entries)
        focused_row = self.getFocusId() if self.getFocusId() in filled else None
        for kind, (list_id, _title, _name) in ROW_IDS.items():
            ctrl = self.list_control(list_id)
            ctrl.reset()
            if list_id in filled:
                _kind, style, entries = filled[list_id]
                ctrl.addItems([self._list_item(kind, style, e) for e in entries])
                self.rows[list_id] = (kind, entries)
        if error is not None:
            self.set_label(MESSAGE, T(30004))
        elif q and not rows:
            self.set_label(MESSAGE, T(30315) % q)
        else:
            self.set_label(MESSAGE, "")
        if focused_row is None and self.getFocusId() >= 300:
            # The row that had focus went away: back to the keys.
            self.focus_id(KEYS)

    def _list_item(self, kind, style, entry):
        if kind == "people":
            image = entry.get("image")
            return list_item(entry.get("name", ""), search.known_for(entry),
                             art={"thumb": self.session.art(image) if image else ""},
                             props={"initials": search.initials(entry.get("name"))})
        if kind == "genres":
            return list_item(entry.get("name", ""), entry.get("library_name") or "")
        if kind == "collections":
            count = entry.get("count") or len(entry.get("item_ids") or [])
            return list_item(entry.get("title", ""), T(30320) % count if count else "",
                             art={"poster": self.session.art(search.collection_image(entry)),
                                  "thumb": self.session.art(search.collection_image(entry))})
        return item_list_item(self.session, entry, style)

    def _selected(self, list_id):
        if list_id not in self.rows:
            return None, None, -1
        kind, entries = self.rows[list_id]
        pos = self.list_control(list_id).getSelectedPosition()
        if not 0 <= pos < len(entries):
            return None, None, -1
        return kind, entries[pos], pos

    # MARK: - keys and clicks

    def on_click(self, control_id):
        if control_id == BOX:
            self._box_changed()
        elif control_id == KEYS:
            pos = self.list_control(KEYS).getSelectedPosition()
            if 0 <= pos < len(search.KEYS):
                self._type(search.KEYS[pos])
        elif control_id == SPACE_KEY:
            self._type(search.SPACE)
        elif control_id == DELETE_KEY:
            self._type(search.DELETE)
        elif control_id == CLEAR_KEY:
            self._type(search.CLEAR)
        elif self.nav:
            kind, entry, _pos = self._selected(control_id)
            if entry is None:
                return
            if kind == "people":
                self.nav("person", {"person_id": entry.get("id"), "name": entry.get("name", ""),
                                    "image": entry.get("image")})
            elif kind == "collections":
                self.nav("collection", entry)
            elif kind == "genres":
                self.nav("genre", entry)
            else:
                self.nav("card", homerows.card(entry))

    def on_action(self, action, code):
        focus = self.getFocusId()
        if focus in (BOX, KEYS, SPACE_KEY, DELETE_KEY, CLEAR_KEY):
            if focus == KEYS and A_REMOTE_0 <= code <= A_REMOTE_9:
                self._type(str(code - A_REMOTE_0))   # a remote's number keys type digits
                return True
            return False
        if code in ACTION_BACK:
            # Back from the matches returns to the keys first, as the Apple app's.
            self.focus_id(KEYS)
            return True
        if not self.nav or (code not in ACTION_CONTEXT and code not in ACTION_PLAY):
            return False
        kind, item, pos = self._selected(focus)
        if item is None or kind not in ("movies", "shows", "episodes"):
            return False
        if code in ACTION_CONTEXT:
            ctrl = self.list_control(focus)
            self.nav("context", {"item": item, "on_changed": lambda it, _act: update_list_item(ctrl.getListItem(pos), it)})
            return True
        if models.playable(item):
            self.nav("play", {"item": item, "resume": models.resume_ms(item)})
            return True
        return False

    def on_back(self):
        self.result = "back"
        self.close()
