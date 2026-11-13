"""The base for Arc's full-screen windows: loaded from the skin (resources/skins/Main), carrying
the Session, with helpers for controls, lists, background work and the artwork proxy. Kept small."""

import threading

import xbmc
import xbmcgui

from .. import compat
from ..log import log

ACTION_BACK = (9, 10, 92)        # Backspace, Escape, Nav Back
ACTION_CONTEXT = (117,)          # Context menu (C / long OK)
ACTION_PREVIOUS_MENU = 10


def _open(window_cls, xml, session, **kwargs):
    w = window_cls(xml, compat.ADDON_PATH, "Main", "1080i", session=session, **kwargs)
    w.doModal()
    result = getattr(w, "result", None)
    del w
    return result


class ArcWindow(xbmcgui.WindowXML):
    """A full-screen window. Subclasses set `xml` and implement on_init / on_click / on_action."""

    xml = None

    def __new__(cls, *args, **kwargs):
        # Kodi's WindowXML.__new__ takes only the positional skin args (xml, path, skin, res);
        # our own kwargs (session, library, ...) are read in __init__ and must not reach it.
        return super(ArcWindow, cls).__new__(cls, *args)

    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop("session")
        self.result = None
        self._closing = False
        xbmcgui.WindowXML.__init__(self)

    @classmethod
    def open(cls, session, **kwargs):
        return _open(cls, cls.xml, session, **kwargs)

    # Kodi callbacks

    def onInit(self):
        try:
            self.on_init()
        except Exception as e:
            log.error("%s onInit failed: %s", type(self).__name__, e)

    def onAction(self, action):
        code = action.getId()
        try:
            if self.on_action(action, code):
                return
        except Exception as e:
            log.error("%s onAction failed: %s", type(self).__name__, e)
        if code in ACTION_BACK:
            self.on_back()

    def onClick(self, control_id):
        try:
            self.on_click(control_id)
        except Exception as e:
            log.error("%s onClick failed: %s", type(self).__name__, e)

    # Overridable

    def on_init(self):
        pass

    def on_click(self, control_id):
        pass

    def on_action(self, action, code):
        return False

    def on_back(self):
        self.close()

    # Helpers

    def set_label(self, control_id, text):
        try:
            self.getControl(control_id).setLabel(text or "")
        except Exception:
            pass

    def set_text(self, control_id, text):
        try:
            self.getControl(control_id).setText(text or "")
        except Exception:
            pass

    def set_image(self, control_id, path):
        try:
            self.getControl(control_id).setImage(path or "")
        except Exception:
            pass

    def set_bool(self, name, value):
        self.setProperty(name, "true" if value else "")

    def set_visible(self, control_id, visible):
        try:
            self.getControl(control_id).setVisible(bool(visible))
        except Exception:
            pass

    def focus_id(self, control_id):
        try:
            self.setFocusId(control_id)
        except Exception:
            pass

    def list_control(self, control_id):
        return self.getControl(control_id)

    def run_async(self, work, done=None):
        """Runs `work()` off the UI thread; calls `done(result, error)` back via a short poll."""
        box = {}

        def runner():
            try:
                box["result"] = work()
            except Exception as e:  # surfaced to `done`
                box["error"] = e

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        if done is None:
            return t

        def waiter():
            t.join()
            if not self._closing:
                done(box.get("result"), box.get("error"))

        threading.Thread(target=waiter, daemon=True).start()
        return t

    def close(self):
        self._closing = True
        xbmcgui.WindowXML.close(self)


def list_item(label="", label2="", art=None, props=None):
    li = xbmcgui.ListItem(label, label2)
    if art:
        li.setArt(art)
    for k, v in (props or {}).items():
        li.setProperty(k, "" if v is None else str(v))
    return li
