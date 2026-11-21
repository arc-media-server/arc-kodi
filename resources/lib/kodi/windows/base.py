"""The base for Arc's full-screen windows: loaded from the skin (resources/skins/Main), carrying
the Session, with helpers for controls, lists, background work and the artwork proxy. Mirrors
PM4K's kodigui base in spirit, kept small."""

import threading

import xbmc
import xbmcgui

from arc.focus import FocusMemory

from .. import compat
from ..log import log

ACTION_BACK = (9, 10, 92)        # Backspace, Escape, Nav Back
ACTION_CONTEXT = (117,)          # Context menu (C / long OK)
ACTION_PLAY = (79, 229)          # Play, Play/Pause on a remote
ACTION_PREVIOUS_MENU = 10
ACTION_UP, ACTION_DOWN = 3, 4


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
        self._focus_memory = FocusMemory()
        xbmcgui.WindowXML.__init__(self)

    @classmethod
    def open(cls, session, **kwargs):
        return _open(cls, cls.xml, session, **kwargs)

    # Kodi callbacks

    def onInit(self):
        # Kodi calls onInit again whenever the window becomes active again (after the video, or a
        # window opened over it): the first time builds the screen, later times only refresh it.
        first = not getattr(self, "_inited", False)
        self._inited = True
        try:
            if first:
                self.on_init()
            else:
                self.on_return()
        except Exception as e:
            log.error("%s onInit failed: %s", type(self).__name__, e)

    # A window whose rows are groups (a title and its list as one unit) in a vertical grouplist
    # lists them here, top to bottom, each as a tuple of the ids that count as being on it (the
    # first is focused). Kodi's grouplist won't move the focus into a group, so Up/Down that leave
    # the focus where it was move to the next visible row here.
    ROW_STOPS = ()

    def onAction(self, action):
        code = action.getId()
        before = getattr(self, "_last_focus", None)
        try:
            if code in (ACTION_UP, ACTION_DOWN) and before == self.getFocusId():
                control = self.getFocusId()
                columns = self.grid_columns(control)
                if columns:
                    ctrl = self.list_control(control)
                    ctrl.selectItem(self._focus_memory.vertical(control, ctrl.getSelectedPosition(), ctrl.size(), columns))
            handled = self.on_action(action, code)
            if not handled and self.ROW_STOPS:
                handled = self._step_rows(code, before)
            if handled:
                return
        except Exception as e:
            log.error("%s onAction failed: %s", type(self).__name__, e)
        finally:
            # Where the focus is now: a focus just asked for (Kodi applies it a moment later), or
            # where Kodi has put it.
            moved_to, self._moved_to = getattr(self, "_moved_to", None), None
            try:
                self._last_focus = moved_to if moved_to is not None else self.getFocusId()
                ctrl = self.list_control(self.getFocusId())
                self._focus_memory.remember(self.getFocusId(), ctrl.getSelectedPosition(), self.grid_columns(self.getFocusId()))
            except Exception:
                pass
        if code in ACTION_BACK:
            self.on_back()

    def grid_columns(self, control_id):
        return 0

    def restore_focus(self, control_id):
        """Restore a list before the window updates its artwork or season from the selection."""
        try:
            ctrl = self.list_control(control_id)
            pos = self._focus_memory.enter(control_id, ctrl.getSelectedPosition(), ctrl.size())
            ctrl.selectItem(pos)
        except (AttributeError, RuntimeError):
            self._focus_memory.enter(control_id, -1, 0)  # a button/section, not a list

    def _step_rows(self, code, before):
        """Up/Down between ROW_STOPS when Kodi didn't move the focus (see ROW_STOPS)."""
        if code not in (ACTION_UP, ACTION_DOWN):
            return False
        now = self.getFocusId()
        if now != before:
            return False
        at = next((i for i, ids in enumerate(self.ROW_STOPS) if now in ids), None)
        if at is None:
            return False
        step = 1 if code == ACTION_DOWN else -1
        i = at + step
        while 0 <= i < len(self.ROW_STOPS):
            target = self.ROW_STOPS[i][0]
            if self.is_visible(target):
                self.focus_id(target)
                self._moved_to = target
                return True
            i += step
        return False

    def onClick(self, control_id):
        log.debug("%s: click on %d", type(self).__name__, control_id)
        try:
            self.on_click(control_id)
        except Exception as e:
            log.error("%s onClick failed: %s", type(self).__name__, e)

    # Overridable

    def on_init(self):
        pass

    def on_return(self):
        """Back on this window after another one (or the video) closed; refresh what may change."""
        pass

    def on_live(self, change):
        """Something this window may show changed on Arc (an arc.events.Change, from the live
        updates thread): refresh it in place, keeping the focus. Most windows do nothing."""
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
        """Sets a textbox's text, or a label's (the windows use both for messages)."""
        try:
            control = self.getControl(control_id)
        except Exception:
            return
        if hasattr(control, "setText"):
            control.setText(text or "")
        else:
            control.setLabel(text or "")

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

    def focus_when_visible(self, control_id, timeout=2.0):
        """Focuses a control whose visibility depends on its content (a row that shows once it has
        cards). Kodi re-evaluates that on its next frame and refuses focus to a hidden control, so
        wait until it's visible, then check the focus took."""
        def run():
            monitor = xbmc.Monitor()
            waited = 0.0
            while waited < timeout and not self._closing:
                if xbmc.getCondVisibility("Control.IsVisible(%d)" % control_id):
                    self.focus_id(control_id)
                    if self.getFocusId() == control_id:
                        return
                if monitor.waitForAbort(0.05):
                    return
                waited += 0.05
            log.debug("couldn't focus control %d", control_id)

        threading.Thread(target=run, daemon=True).start()

    def is_visible(self, control_id):
        return xbmc.getCondVisibility("Control.IsVisible(%d)" % control_id)

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
