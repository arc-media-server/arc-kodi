"""Arc's own menu: one dialog in place of Kodi's context menu, select and yes/no dialogs, so every
menu in the add-on looks like the player's (a dark panel, white focused row, a tick for the
chosen option). `choose()` picks from a list; `confirm()` asks a question.

Opened modal on the calling thread, as Kodi's own dialogs are; Back or Context Menu closes it
without a choice."""

import xbmcgui

from .. import compat
from ..compat import T
from ..log import log
from .base import ACTION_BACK, ACTION_CONTEXT

PANEL, TITLE, LIST, BACKGROUND, MESSAGE = 600, 601, 602, 603, 604
ROW, ROWS_SHOWN = 64, 8       # rows 64 high, up to 8 showing (the list scrolls past that)
PANEL_WIDTH, LINE = 580, 40   # the message's lines, at arc-body, ~34 characters each


class MenuDialog(xbmcgui.WindowXMLDialog):
    xml = "script-arc-menu.xml"

    def __new__(cls, *args, **kwargs):
        return super(MenuDialog, cls).__new__(cls, *args)

    def __init__(self, *args, **kwargs):
        self.title = kwargs.pop("title", "")
        self.options = kwargs.pop("options", [])
        self.selected = kwargs.pop("selected", -1)
        self.focus = kwargs.pop("focus", None)
        self.message = kwargs.pop("message", "")
        self.result = -1
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        try:
            self._fill()
        except Exception as e:
            log.error("MenuDialog onInit failed: %s", e)

    def _fill(self):
        self.getControl(TITLE).setLabel(self.title or "")
        ctrl = self.getControl(LIST)
        ctrl.reset()
        items = []
        for i, opt in enumerate(self.options):
            label, detail = (opt, "") if not isinstance(opt, (tuple, list)) else (opt[0], opt[1])
            li = xbmcgui.ListItem(label, detail)
            li.setProperty("selected", "1" if i == self.selected else "")
            items.append(li)
        # The panel fits the message and the rows, centred on the screen. The list is sized
        # before it's filled: filled first, Kodi lays the rows out for the old height and scrolls
        # the first one away.
        msg_h = 0
        if self.message:
            lines = max(1, sum(-(-max(1, len(p)) // 34) for p in self.message.split("\n")))
            msg_h = lines * LINE + 16
            self.getControl(MESSAGE).setText(self.message)
            self.getControl(MESSAGE).setHeight(msg_h)
        top = 76 + msg_h
        rows = max(1, min(len(items), ROWS_SHOWN))
        height = top + rows * ROW + 16
        ctrl.setPosition(16, top)
        ctrl.setHeight(rows * ROW)
        ctrl.addItems(items)
        self.getControl(BACKGROUND).setHeight(height)
        self.getControl(PANEL).setPosition((1920 - PANEL_WIDTH) // 2, (1080 - height) // 2)
        focus = self.focus if self.focus is not None else max(self.selected, 0)
        if 0 <= focus < len(items):
            ctrl.selectItem(focus)
        self.setFocusId(LIST)

    def onClick(self, control_id):
        if control_id == LIST:
            self.result = self.getControl(LIST).getSelectedPosition()
            self.close()

    def onAction(self, action):
        if action.getId() in ACTION_BACK or action.getId() in ACTION_CONTEXT:
            self.close()


def choose(title, options, selected=-1, focus=None, message=""):
    """Shows a menu and returns the chosen option's index, or -1 for none. Options are labels or
    (label, detail) pairs; `selected` ticks the current one."""
    if not options:
        return -1
    w = MenuDialog(MenuDialog.xml, compat.ADDON_PATH, "Main", "1080i", title=title, options=options,
                   selected=selected, focus=focus, message=message)
    w.doModal()
    result = w.result
    del w
    return result


def confirm(title, message, yes):
    """Asks a question; True for `yes`. Cancel is the other choice, and Back."""
    return choose(title, [yes, T(30001)], message=message) == 0
