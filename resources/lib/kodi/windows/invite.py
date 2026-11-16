"""Watch Together's invite screen: what to do, the people to invite in a box of their own (Select
ticks one; someone who can't watch the title can't be ticked), and under the box Send Invite and,
for a new room, Use a Code Instead. `ask()` returns ("invite", [profile ids]), ("code", []) or
None for Back."""

import xbmcgui

from .. import compat
from ..compat import T
from ..log import log
from .base import ACTION_BACK, ACTION_CONTEXT

PANEL, TITLE, PEOPLE, BACKGROUND, MESSAGE, BOX = 700, 701, 702, 703, 704, 705
SEND, CODE = 710, 711
ROW, ROWS_SHOWN = 72, 5           # people rows; the box scrolls past five
WIDTH, LINE, CHARS = 800, 40, 46  # the panel, and the message's lines at arc-body
SEND_W, CODE_W, GAP, BUTTON_H = 280, 340, 24, 64


class InviteDialog(xbmcgui.WindowXMLDialog):
    xml = "script-arc-invite.xml"

    def __new__(cls, *args, **kwargs):
        return super(InviteDialog, cls).__new__(cls, *args)

    def __init__(self, *args, **kwargs):
        self.people = kwargs.pop("people", [])
        self.message = kwargs.pop("message", "")
        self.offer_code = kwargs.pop("offer_code", True)
        self.chosen = set()
        self.result = None
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        try:
            self._lay_out()
        except Exception as e:
            log.error("invite screen failed: %s", e)

    def _lay_out(self):
        self.getControl(TITLE).setLabel(T(30330))
        lines = max(1, sum(-(-max(1, len(p)) // CHARS) for p in self.message.split("\n")))
        msg_h = lines * LINE + 8
        self.getControl(MESSAGE).setText(self.message)
        self.getControl(MESSAGE).setHeight(msg_h)
        top = 80 + msg_h + 16
        people = self.getControl(PEOPLE)
        if self.people:
            rows = min(len(self.people), ROWS_SHOWN)
            box_h = rows * ROW + 32
            self.getControl(BOX).setPosition(32, top)
            self.getControl(BOX).setHeight(box_h)
            # Sized before it's filled, or Kodi lays the rows out for the old height.
            people.setPosition(48, top + 16)
            people.setHeight(rows * ROW)
            people.addItems([self._row(p) for p in self.people])
            top += box_h + 32
        else:
            self.getControl(BOX).setVisible(False)
            people.setVisible(False)
        send, code = self.getControl(SEND), self.getControl(CODE)
        send.setVisible(bool(self.people))
        code.setVisible(self.offer_code)
        shown = [(c, w) for c, w, on in ((send, SEND_W, bool(self.people)), (code, CODE_W, self.offer_code)) if on]
        x = (WIDTH - sum(w for _, w in shown) - GAP * (len(shown) - 1)) // 2
        for c, w in shown:
            c.setPosition(x, top)
            x += w + GAP
        height = top + BUTTON_H + 32
        self.getControl(BACKGROUND).setHeight(height)
        self.getControl(PANEL).setPosition((1920 - WIDTH) // 2, (1080 - height) // 2)
        self._update_send()
        self.setFocusId(PEOPLE if self.people else CODE)

    def _row(self, p):
        locked = p.get("can_watch") is False
        detail = T(30346) if locked else T(30353) if p.get("friend") else ""
        li = xbmcgui.ListItem(p.get("name", ""), detail)
        li.setProperty("locked", "1" if locked else "")
        return li

    def _update_send(self):
        """Send Invite only once someone is ticked; until then Down from the box goes to Use a
        Code Instead."""
        if not self.people:
            return
        send, code, people = self.getControl(SEND), self.getControl(CODE), self.getControl(PEOPLE)
        send.setEnabled(bool(self.chosen))
        if self.chosen:
            people.controlDown(send)
        elif self.offer_code:
            people.controlDown(code)

    def onClick(self, control_id):
        if control_id == PEOPLE:
            pos = self.getControl(PEOPLE).getSelectedPosition()
            if not 0 <= pos < len(self.people) or self.people[pos].get("can_watch") is False:
                return
            self.chosen ^= {pos}
            self.getControl(PEOPLE).getListItem(pos).setProperty("ticked", "1" if pos in self.chosen else "")
            self._update_send()
        elif control_id == SEND and self.chosen:
            self.result = ("invite", [self.people[i].get("id") for i in sorted(self.chosen)])
            self.close()
        elif control_id == CODE:
            self.result = ("code", [])
            self.close()

    def onAction(self, action):
        if action.getId() in ACTION_BACK or action.getId() in ACTION_CONTEXT:
            self.close()


def ask(people, message, offer_code=True):
    w = InviteDialog(InviteDialog.xml, compat.ADDON_PATH, "Main", "1080i", people=people,
                     message=message, offer_code=offer_code)
    w.doModal()
    result = w.result
    del w
    return result
