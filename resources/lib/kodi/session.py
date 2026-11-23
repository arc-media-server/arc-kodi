"""The app's state: the server, the device token, the chosen profile, prefs and libraries. One of
these is made at start-up and passed to every window. It owns the ArcAPI and the artwork proxy."""

from arc import home as homerows
from arc.api import ArcAPI, APIError
from arc.launch import launch_profile

from . import storage
from .artwork import ArtworkProxy
from .compat import ADDON_VERSION
from .device_logs import journal
from .log import log


class Session(object):
    def __init__(self):
        saved = storage.load()
        self.base_url = saved.get("base_url")
        self._token = saved.get("token")
        self.auto_profile_id = saved.get("auto_profile_id")
        self.profile = None
        if saved.get("profile_id"):
            self.profile = {"id": saved["profile_id"], "name": saved.get("profile_name", ""),
                            "is_admin": saved.get("profile_admin", False),
                            "color": saved.get("profile_color", "")}
        self.prefs = {}
        self.libraries = []
        self.features = {}   # GET /capabilities' features (Watch Together's availability)
        self.identity_name = saved.get("server_name", "")
        self.local = None
        # The last Recommended page per library id, shown at once on the next visit while a fresh
        # one loads (dropped with the profile).
        self.recommended = {}
        self.api = ArcAPI(self.base_url or "", token=lambda: self._token,
                          user_agent="Arc for Kodi/%s" % ADDON_VERSION)
        self.artwork = ArtworkProxy(self.api)

    # MARK: - state

    @property
    def signed_in(self):
        return bool(self.base_url and self._token)

    @property
    def has_profile(self):
        return self.signed_in and self.profile is not None

    def set_server(self, base_url, name=""):
        if self.base_url != base_url:
            journal().clear()
        self.base_url = base_url
        self.identity_name = name
        self.api.base_url = base_url.rstrip("/")
        storage.update(base_url=base_url, server_name=name)

    def set_token(self, token):
        self._token = token
        storage.update(token=token)

    def set_profile(self, profile):
        self.profile = {"id": profile.get("id"), "name": profile.get("name", ""),
                        "is_admin": profile.get("is_admin", False), "color": profile.get("color", ""), "has_pin": profile.get("has_pin", False)}
        storage.update(profile_id=profile.get("id"), profile_name=profile.get("name", ""),
                       profile_admin=profile.get("is_admin", False), profile_color=profile.get("color", ""))

    def set_auto_profile(self, profile_id):
        saved = storage.load()
        saved["auto_profile_id"] = profile_id
        if not storage.save(saved):
            return False
        self.auto_profile_id = profile_id
        return True

    def prepare_launch(self):
        status = self.api.auth_status()
        if not status.get("signed_in"):
            self.clear_sign_in()
            return
        profile = launch_profile(status, self.auto_profile_id)
        current = status.get("profile") or {}
        if profile and profile.get("id") != current.get("id"):
            try:
                answer = self.api.choose_profile(profile["id"])
                if isinstance(answer, dict):
                    profile = dict(profile, **answer)
            except APIError as error:
                log.warning("automatic profile sign-in failed (HTTP %s)", error.status)
                profile = None
        if profile:
            self.set_profile(profile)
            if not status.get("friend") and profile.get("id") == self.auto_profile_id:
                log.info("signing in automatically as the saved profile")
        else:
            if current and not status.get("friend"):
                self.api.leave_profile()
            self.forget_profile()
            log.info("starting at Who's watching")

    def forget_profile(self):
        self.profile = None
        self.recommended = {}
        storage.update(profile_id=None, profile_name=None, profile_admin=False, profile_color=None)

    def forget_server(self):
        self.base_url = None
        self.identity_name = ""
        self.api.base_url = ""
        storage.clear()

    def sign_out(self):
        self.api.sign_out()
        self.clear_sign_in()

    def clear_sign_in(self):
        journal().clear()
        self.auto_profile_id = None
        self._token = None
        self.profile = None
        storage.clear()
        if self.base_url:
            storage.update(base_url=self.base_url, server_name=self.identity_name)

    # MARK: - loading

    def start_proxy(self):
        self.artwork.start()

    def refresh(self):
        """Loads the identity, prefs and libraries once a profile is chosen. Raises on failure."""
        ident = self.api.identity()
        if ident and ident.get("name"):
            self.identity_name = ident["name"]
            storage.update(server_name=self.identity_name)
        try:
            status = self.api.auth_status() or {}
            self.local = status.get("local")
            current = status.get("profile") or {}
            if self.profile and current.get("id") == self.profile.get("id"):
                self.profile["has_pin"] = current.get("has_pin", False)
        except Exception:
            self.local = None
        self.prefs = self.api.prefs() or {}
        self.libraries = self.api.libraries() or []
        try:
            self.features = (self.api.capabilities() or {}).get("features") or {}
        except Exception:
            self.features = {}
        # The server's version, so a log shows which Arc build answered (e.g. after an update).
        log.info("loaded %d libraries from Arc %s", len(self.libraries), (ident or {}).get("version") or "?")

    def ordered_libraries(self):
        return homerows.ordered_libraries(self.libraries, (self.prefs or {}).get("library_order") or [])

    def home_rows(self):
        return homerows.resolve_home_rows(self.prefs, self.ordered_libraries())

    def art(self, api_path):
        """A Kodi-loadable URL for an Arc image path."""
        return self.artwork.url_for(api_path)
