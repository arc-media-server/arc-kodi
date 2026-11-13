"""The sign-in flow: connect to a server, sign in with a code (Link a Device), choose a profile.
Each is a full-screen window; together they take an unconfigured install to a chosen profile."""

import threading
import time

import xbmc
import xbmcgui

from arc.api import ArcAPI, APIError, Unreachable, normalise_address

from ..compat import T
from ..log import log
from .base import ArcWindow, list_item


class ConnectWindow(ArcWindow):
    """Type the server address; checks it answers and is an Arc server."""

    xml = "script-arc-connect.xml"

    ADDRESS = 100
    CONNECT = 101
    STATUS = 102

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self.address = ""

    def on_init(self):
        self.focus_id(self.ADDRESS)

    def on_click(self, control_id):
        if control_id == self.ADDRESS:
            if self._type_address():
                self._connect()
        elif control_id == self.CONNECT:
            if self.address or self._type_address():
                self._connect()

    def _type_address(self):
        typed = (xbmcgui.Dialog().input(T(30020), self.address) or "").strip()
        if typed:
            self.address = typed
            self.set_label(self.ADDRESS, typed)
        return bool(typed)

    def _connect(self):
        base = normalise_address(self.address)
        if not base:
            self.set_text(self.STATUS, T(30026))
            return
        self.set_text(self.STATUS, T(30025))
        self.run_async(lambda: self._check(base), self._connected)

    def _check(self, base):
        api = ArcAPI(base, user_agent="Arc for Kodi")
        health = api.health()
        if not isinstance(health, dict) or not health.get("api_version"):
            raise ValueError("not-arc")
        return base, health.get("name", "")

    def _connected(self, result, error):
        if error is not None:
            if isinstance(error, Unreachable):
                self.set_text(self.STATUS, T(30028))
            else:
                self.set_text(self.STATUS, T(30027))
            return
        base, name = result
        self.session.set_server(base, name)
        self.result = "connected"
        self.close()


class SignInWindow(ArcWindow):
    """Shows a Link-a-Device code and polls until it's approved."""

    xml = "script-arc-signin.xml"

    CODE = 100
    STATUS = 101
    NEW_CODE = 102
    CHANGE_SERVER = 103

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self._stop = threading.Event()
        self._poll = None

    def on_init(self):
        self.set_label(self.NEW_CODE, T(30045))
        self.set_label(self.CHANGE_SERVER, T(30046))
        self.set_text(self.STATUS, T(30043))
        self._begin()

    def _begin(self):
        self.run_async(lambda: self.session.api.start_link("Kodi"), self._show_code)

    def _show_code(self, result, error):
        if error is not None or not isinstance(result, dict) or not result.get("code"):
            self.set_text(self.STATUS, T(30047))
            return
        self.set_label(self.CODE, result["code"])
        self.set_text(self.STATUS, T(30043))
        self._stop.clear()
        self._poll = threading.Thread(target=self._poll_loop, args=(result["poll"],), daemon=True)
        self._poll.start()

    def _poll_loop(self, poll):
        while not self._stop.is_set():
            if xbmc.Monitor().waitForAbort(3):
                return
            try:
                state, token = self.session.api.poll_link(poll)
            except Exception:
                continue
            if state == "approved":
                self.session.set_token(token)
                self.result = "signed_in"
                self.close()
                return
            if state == "expired":
                self.set_text(self.STATUS, T(30044))
                self._begin()
                return

    def on_click(self, control_id):
        if control_id == self.NEW_CODE:
            self._stop.set()
            self._begin()
        elif control_id == self.CHANGE_SERVER:
            self._stop.set()
            self.result = "change_server"
            self.close()

    def on_back(self):
        self._stop.set()
        self.result = "change_server"
        self.close()

    def close(self):
        self._stop.set()
        ArcWindow.close(self)


# A profile's colour (web/src/components/Avatar.tsx; the deeper end of its gradient), as ARGB.
PROFILE_COLOURS = {
    "blue": "FF2563EB", "teal": "FF0891B2", "green": "FF15803D", "amber": "FFCA8A04",
    "orange": "FFDC2626", "rose": "FFE11D48", "slate": "FF334155", "violet": "FF4F46E5",
}


class ProfilesWindow(ArcWindow):
    """"Who's watching?" — pick a profile, with a PIN when one is set."""

    xml = "script-arc-profiles.xml"

    LIST = 100
    SERVER = 101

    def on_init(self):
        self.set_label(self.SERVER, T(30200) % (self.session.identity_name or ""))
        self._load()

    def _load(self):
        self.run_async(self.session.api.auth_status, self._show)

    def _show(self, status, error):
        if error is not None or not isinstance(status, dict):
            xbmcgui.Dialog().notification("Arc", T(30004))
            self.result = "failed"
            self.close()
            return
        self._profiles = status.get("profiles") or []
        ctrl = self.list_control(self.LIST)
        ctrl.reset()
        for p in self._profiles:
            name = p.get("name", "")
            ctrl.addItem(list_item(name, props={
                "colorhex": PROFILE_COLOURS.get(p.get("color"), PROFILE_COLOURS["violet"]),
                "initial": name[:1].upper(), "haspin": p.get("has_pin"), "admin": p.get("is_admin")}))
        # Centre the row of avatars (a Kodi list can't centre its own items).
        width = len(self._profiles) * 240 + max(0, len(self._profiles) - 1) * 40
        ctrl.setWidth(min(width, 1760))
        ctrl.setPosition(int((1920 - min(width, 1760)) / 2), 420)
        self.focus_id(self.LIST)

    def on_click(self, control_id):
        if control_id == self.LIST:
            pos = self.list_control(self.LIST).getSelectedPosition()
            if 0 <= pos < len(self._profiles):
                self._choose(self._profiles[pos])

    def _choose(self, profile, pin=None):
        def work():
            return self.session.api.choose_profile(profile.get("id"), pin=pin)

        def done(result, error):
            if error is None:
                self.session.set_profile(result if isinstance(result, dict) else profile)
                self.result = "chosen"
                self.close()
                return
            if isinstance(error, APIError) and error.needs == "pin":
                entered = xbmcgui.Dialog().input(T(30061) % profile.get("name", ""),
                                                 type=xbmcgui.INPUT_NUMERIC,
                                                 option=xbmcgui.ALPHANUM_HIDE_INPUT)
                if entered:
                    self._choose(profile, pin=entered)
                return
            xbmcgui.Dialog().notification("Arc", getattr(error, "message", T(30004)))

        self.run_async(work, done)
