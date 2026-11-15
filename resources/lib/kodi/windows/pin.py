"""Arc's PIN pad, in place of Kodi's number dialog: four dots, round keys 1-9, 0 and Delete, and
the remote's own number keys. The fourth digit sends it (Arc's PINs are four digits). `ask()`
returns the PIN, or None for Back."""

import xbmcgui

from .. import compat
from ..compat import T
from .base import ACTION_BACK, list_item

KEYS, TITLE, ERROR = 300, 301, 302
PIN_LENGTH, DELETE_AT = 4, 11                # four digits; the keys are 1-9, a gap, 0, Delete
A_REMOTE_0, A_REMOTE_9, A_BACKSPACE = 58, 67, 110   # the remote's number keys, and Backspace


class PinPad(xbmcgui.WindowXMLDialog):
    xml = "script-arc-pin.xml"

    def __new__(cls, *args, **kwargs):
        return super(PinPad, cls).__new__(cls, *args)

    def __init__(self, *args, **kwargs):
        self.title = kwargs.pop("title", "")
        self.error = kwargs.pop("error", "")
        self.digits = ""
        self.result = None
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        self.getControl(TITLE).setLabel(self.title)
        self.getControl(ERROR).setLabel(self.error)
        ctrl = self.getControl(KEYS)
        ctrl.reset()
        labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", T(30310)]
        ctrl.addItems([list_item(k, props={"small": "1" if i == DELETE_AT else ""}) for i, k in enumerate(labels)])
        self._show()
        self.setFocusId(KEYS)

    def _show(self):
        self.setProperty("arc.digits", str(len(self.digits)))

    def _type(self, digit):
        if len(self.digits) >= PIN_LENGTH:
            return
        self.digits += digit
        self._show()
        if len(self.digits) == PIN_LENGTH:
            self.result = self.digits
            self.close()

    def _delete(self):
        self.digits = self.digits[:-1]
        self._show()

    def onClick(self, control_id):
        if control_id != KEYS:
            return
        pos = self.getControl(KEYS).getSelectedPosition()
        if pos == DELETE_AT:
            self._delete()
        elif pos == 10:
            self._type("0")
        elif 0 <= pos < 9:
            self._type(str(pos + 1))

    def onAction(self, action):
        code = action.getId()
        if A_REMOTE_0 <= code <= A_REMOTE_9:
            self._type(str(code - A_REMOTE_0))
        elif code == A_BACKSPACE:
            self._delete()
        elif code in ACTION_BACK:
            self.close()


def ask(title, error=""):
    """Shows the PIN pad; the four digits typed, or None if it was closed."""
    w = PinPad(PinPad.xml, compat.ADDON_PATH, "Main", "1080i", title=title, error=error)
    w.doModal()
    result = w.result
    del w
    return result
