"""Arc's on-screen keyboard (script-arc-keyboard.xml; the keys and editing are arc/keyboard.py's),
in place of Kodi's keyboard: for the server address, the household password and a Watch Together
code. `type_text(title, text, kind)` returns what was typed when Done is chosen, or None for
Back. A remote's number keys type digits."""

import xbmcgui

from arc import keyboard

from .. import compat
from ..compat import T
from ..log import log
from .base import ACTION_BACK

TITLE, KEYS, TEXT = 701, 702, 704
SHIFT, PAGE, SPACE, DELETE, CLEAR, DONE = 710, 711, 712, 713, 714, 715
A_REMOTE_0, A_REMOTE_9 = 58, 67   # a remote's number keys


class KeyboardDialog(xbmcgui.WindowXMLDialog):
    xml = "script-arc-keyboard.xml"

    def __new__(cls, *args, **kwargs):
        return super(KeyboardDialog, cls).__new__(cls, *args)

    def __init__(self, *args, **kwargs):
        self.title = kwargs.pop("title", "")
        self.text = kwargs.pop("text", "") or ""
        self.kind = kwargs.pop("kind", "address")
        self.page = keyboard.START.get(self.kind, "lower")
        self.result = None
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        try:
            self.getControl(TITLE).setLabel(self.title)
            self._show_page()
            self._show_text()
            self.setFocusId(KEYS)
        except Exception as e:
            log.error("keyboard failed: %s", e)

    def _show_page(self, keep=None):
        ctrl = self.getControl(KEYS)
        pos = ctrl.getSelectedPosition() if keep else 0
        ctrl.reset()
        ctrl.addItems([xbmcgui.ListItem(k) for k in keyboard.keys(self.page)])
        ctrl.selectItem(max(pos, 0))
        self.getControl(PAGE).setLabel(T(30452) if self.page == "symbols" else T(30451))

    def _show_text(self):
        self.getControl(TEXT).setLabel(keyboard.shown(self.text, hidden=self.kind == "password"))

    def _type(self, key):
        self.text = keyboard.edit(self.text, key)
        self._show_text()

    def onClick(self, control_id):
        if control_id == KEYS:
            pos = self.getControl(KEYS).getSelectedPosition()
            page = keyboard.keys(self.page)
            if 0 <= pos < len(page):
                self._type(page[pos])
        elif control_id == SHIFT:
            self.page = keyboard.shifted(self.page)
            self._show_page(keep=True)
        elif control_id == PAGE:
            self.page = keyboard.switched(self.page)
            self._show_page(keep=True)
        elif control_id == SPACE:
            self._type(keyboard.SPACE)
        elif control_id == DELETE:
            self._type(keyboard.DELETE)
        elif control_id == CLEAR:
            self._type(keyboard.CLEAR)
        elif control_id == DONE:
            self.result = self.text
            self.close()

    def onAction(self, action):
        code = action.getId()
        if code in ACTION_BACK:
            self.close()
        elif A_REMOTE_0 <= code <= A_REMOTE_9:
            self._type(str(code - A_REMOTE_0))


def type_text(title, text="", kind="address"):
    """What the viewer typed, once they chose Done; None if they went Back."""
    w = KeyboardDialog(KeyboardDialog.xml, compat.ADDON_PATH, "Main", "1080i", title=title,
                       text=text, kind=kind)
    w.doModal()
    result = w.result
    del w
    return result
