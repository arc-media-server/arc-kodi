"""The sign-in flow: connect to a server, sign in with a code (Link a Device), choose a profile.
Each is a full-screen window; together they take an unconfigured install to a chosen profile."""

import threading
import time

import xbmc
import xbmcgui

from arc.api import ArcAPI, APIError, Unreachable, normalise_address
from arc.discovery import DiscoveryState, scan
from arc.titlepage import plain_width

from .. import toast
from ..compat import T
from ..log import log
from . import keyboard
from . import menu
from . import pin as pin_pad
from .base import ArcWindow, list_item


class LoadingWindow(ArcWindow):
    """The Arc screen underneath the current page during navigation between windows."""

    xml = "script-arc-loading.xml"

    def on_back(self):
        # The active page owns Back. A gap between pages must not dismiss its background.
        pass


class ConnectWindow(ArcWindow):
    """Type the server address; checks it answers and is an Arc server."""

    xml = "script-arc-connect.xml"

    ADDRESS = 100
    CONNECT = 101
    STATUS = 102
    # Server discovery
    SERVERS, SEARCH, DISCOVERY_STATUS = 103, 104, 105

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self.address = ""
        self._discovery = DiscoveryState()

    def on_init(self):
        self.focus_id(self.ADDRESS)
        self._search()

    def on_click(self, control_id):
        if control_id == self.ADDRESS:
            if self._type_address():
                self._connect()
        elif control_id == self.SEARCH:
            self._search()
        elif control_id == self.SERVERS:
            pos = self.list_control(self.SERVERS).getSelectedPosition()
            if 0 <= pos < len(self._discovery.found):
                self.address = self._discovery.found[pos]["address"]
                self.set_label(self.ADDRESS, self.address)
                self._connect()
        elif control_id == self.CONNECT:
            if self.address or self._type_address():
                self._connect()

    def _type_address(self):
        self._discovery.typing = True
        try:
            typed = (keyboard.type_text(T(30020), self.address, kind="address") or "").strip()
        finally:
            self._discovery.typing = False
        if typed:
            self._discovery.manual = True
            self.address = typed
            self.set_label(self.ADDRESS, typed)
        return bool(typed)

    # Server discovery: reuse the Connect screen's list and pill controls.
    def _search(self):
        old = self._discovery
        old.stop.set()
        state = self._discovery = DiscoveryState()
        state.manual = bool(self.address)
        state.typing = old.typing
        self.list_control(self.SERVERS).reset()
        self.set_bool("servers", False)
        self.set_label(self.DISCOVERY_STATUS, T(30562))

        def found(server):
            if state is not self._discovery or state.stop.is_set() or self._closing:
                return
            focus = state.accept(server)
            self.list_control(self.SERVERS).addItem(list_item(server["name"], server["address"]))
            self.set_bool("servers", True)
            if focus:
                # Wait for the list to become visible; typing may start during that frame.
                def focus_first():
                    monitor = xbmc.Monitor()
                    for _ in range(40):
                        if (state is not self._discovery or state.stop.is_set()
                                or state.typing or state.manual or self._closing):
                            return
                        if self.is_visible(self.SERVERS):
                            self.focus_id(self.SERVERS)
                            return
                        if monitor.waitForAbort(0.05):
                            return
                threading.Thread(target=focus_first, daemon=True).start()

        def done(_result, _error):
            if state is self._discovery and not state.stop.is_set():
                self.set_label(self.DISCOVERY_STATUS, "" if state.found else T(30563))
                log.info("server discovery finished (%d found)", len(state.found))

        self.run_async(lambda: scan(xbmc.getIPAddress(), found, state.stop), done)

    def close(self):
        self._discovery.stop.set()
        ArcWindow.close(self)

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


class UnavailableWindow(ArcWindow):
    """Arc couldn't be reached as the add-on started (the server is off, asleep or restarting):
    say so, and try again every 15 seconds, going on by itself once Arc answers. Try Again
    checks at once; Change Server picks another; Back leaves the add-on. Its result is "retry",
    "change_server" or "exit"."""

    xml = "script-arc-unavailable.xml"

    RETRY, CHANGE, TITLE, MESSAGE, STATUS, EVERY = 101, 102, 200, 201, 202, 15

    def on_init(self):
        self.set_label(self.TITLE, T(30420) % (self.session.identity_name or "Arc"))
        self.set_text(self.MESSAGE, T(30004))
        self.set_label(self.STATUS, T(30421))
        self.focus_id(self.RETRY)
        self._checking = False
        threading.Thread(target=self._keep_trying, daemon=True).start()

    def _keep_trying(self):
        monitor = xbmc.Monitor()
        while not self._closing and not monitor.waitForAbort(self.EVERY):
            if not self._closing and not self._checking and self._reachable():
                log.info("Arc answered again")
                self._finish("retry")
                return

    def _reachable(self):
        try:
            return isinstance(self.session.api.health(), dict)
        except Exception:
            return False

    def _finish(self, result):
        if not self._closing:
            self.result = result
            self.close()

    def on_click(self, control_id):
        if control_id == self.RETRY and not self._checking:
            self._checking = True
            self.set_label(self.STATUS, T(30025))

            def done(ok, _error):
                self._checking = False
                if ok:
                    log.info("Arc answered again")
                    self._finish("retry")
                else:
                    self.set_label(self.STATUS, T(30422))

            self.run_async(self._reachable, done)
        elif control_id == self.CHANGE:
            self._finish("change_server")

    def on_back(self):
        self._finish("exit")


class SignInWindow(ArcWindow):
    """Shows a Link-a-Device code and polls until it's approved."""

    xml = "script-arc-signin.xml"

    CODE = 100
    STATUS = 101
    NEW_CODE = 102
    CHANGE_SERVER = 103
    PASSWORD = 104

    def __init__(self, *args, **kwargs):
        ArcWindow.__init__(self, *args, **kwargs)
        self._stop = threading.Event()
        self._poll = None

    LINK_STEP, SPINNER, SERVER = 105, 106, 107
    CODE_BOXES = (110, 111, 112, 113)

    def on_init(self):
        self.set_label(self.NEW_CODE, T(30045))
        self.set_label(self.CHANGE_SERVER, T(30046))
        server = display_address(self.session.base_url)
        self.set_label(self.LINK_STEP, T(30613) % (server + "/link"))
        self.set_label(self.SERVER, T(30200) % server)
        self._status(T(30043))
        self._begin()

    def _status(self, text, waiting=True):
        """The line under the code, with the spinner beside it while waiting, the two centred
        together as Android's row (Kodi can't centre a row of controls itself)."""
        self.set_text(self.STATUS, text)
        width = plain_width(text, 30) + (52 if waiting else 0)
        left = max(0, int((704 - width) / 2))
        self.set_visible(self.SPINNER, waiting)
        try:
            self.getControl(self.SPINNER).setPosition(left, 8)
            self.getControl(self.STATUS).setPosition(left + (52 if waiting else 0), 0)
        except Exception:
            pass

    def _show_digits(self, code):
        # Four characters go in Android's four boxes; any other code shows whole.
        boxed = len(code) == len(self.CODE_BOXES)
        self.set_bool("boxes", boxed)
        for i, cid in enumerate(self.CODE_BOXES):
            self.set_label(cid, code[i] if boxed else "")
        self.set_label(self.CODE, "" if boxed else code)

    def _begin(self):
        self.run_async(lambda: self.session.api.start_link("Kodi"), self._show_code)

    def _show_code(self, result, error):
        if error is not None or not isinstance(result, dict) or not result.get("code"):
            self._status(T(30047), waiting=False)
            return
        self._show_digits(result["code"])
        self._status(T(30043))
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
                self._status(T(30044))
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
        elif control_id == self.PASSWORD:
            self._password()

    def _password(self):
        """Signs in with the household password (POST /auth/login), for a keyboard; the code
        keeps working meanwhile. The password goes to Arc and nowhere else: not stored or logged."""
        password = keyboard.type_text(T(30312), kind="password")
        if not password:
            return
        self._status(T(30314))

        def done(token, error):
            if error is None and token:
                log.info("signed in with the password")
                self._stop.set()
                self.session.set_token(token)
                self.result = "signed_in"
                self.close()
                return
            wrong = isinstance(error, APIError) and error.status in (401, 403)
            log.info("password sign-in failed (%s)", "wrong password" if wrong else type(error).__name__)
            self._status(T(30313) if wrong else T(30004), waiting=False)

        self.run_async(lambda: self.session.api.login(password, "Kodi"), done)

    def on_back(self):
        self._stop.set()
        self.result = "change_server"
        self.close()

    def close(self):
        self._stop.set()
        ArcWindow.close(self)


def display_address(base_url):
    """The server as people type it: no scheme, no trailing slash (Android's display())."""
    text = base_url or ""
    for prefix in ("http://", "https://"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.rstrip("/")


# A profile's colour (web/src/components/Avatar.tsx; the deeper end of its gradient), as ARGB.
PROFILE_COLOURS = {
    "blue": "FF2563EB", "teal": "FF0891B2", "green": "FF15803D", "amber": "FFCA8A04",
    "orange": "FFDC2626", "rose": "FFE11D48", "slate": "FF334155", "violet": "FF4F46E5",
}


class ProfilesWindow(ArcWindow):
    """"Who's watching?" — pick a profile, with a PIN when one is set."""

    xml = "script-arc-profiles.xml"

    LIST = 100
    SIGN_OUT = 102

    def on_init(self):
        self._load()

    def _load(self):
        self.run_async(self.session.api.auth_status, self._show)

    def _show(self, status, error):
        if error is not None or not isinstance(status, dict):
            toast.show(T(30004))
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
        width = len(self._profiles) * 256 + max(0, len(self._profiles) - 1) * 64
        ctrl.setWidth(min(width, 1760))
        ctrl.setPosition(int((1920 - min(width, 1760)) / 2), 464)
        self.focus_id(self.LIST)

    def on_click(self, control_id):
        if control_id == self.SIGN_OUT:
            if menu.confirm(T(30063), T(30178) % (self.session.identity_name or "Arc"), T(30063)):
                self.result = "sign_out"
                self.close()
            return
        if control_id == self.LIST:
            pos = self.list_control(self.LIST).getSelectedPosition()
            if 0 <= pos < len(self._profiles):
                self._choose(self._profiles[pos])

    def _choose(self, profile, pin=None, wrong=False):
        if profile.get("has_pin") and pin is None:
            # Arc's PIN pad first, rather than a request Arc will refuse.
            pin = pin_pad.ask(T(30061) % profile.get("name", ""), T(30062) if wrong else "")
            if not pin:
                return

        def work():
            return self.session.api.choose_profile(profile.get("id"), pin=pin)

        def done(result, error):
            if error is None:
                self.session.set_profile(dict(profile, **result) if isinstance(result, dict) else profile)
                self.result = "chosen"
                self.close()
                return
            if isinstance(error, APIError) and error.needs == "pin":
                # No PIN sent, or the wrong one: the pad again, saying so if one was typed.
                self._choose(dict(profile, has_pin=True), wrong=pin is not None)
                return
            toast.show(getattr(error, "message", T(30004)))

        self.run_async(work, done)
