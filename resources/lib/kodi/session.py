"""The app's state: the server, the device token, the chosen profile, prefs and libraries. One of
these is made at start-up and passed to every window. It owns the ArcAPI and the artwork proxy."""

from arc import home as homerows
from arc.api import ArcAPI, APIError, Unreachable

from . import storage
from .artwork import ArtworkProxy
from .compat import ADDON_VERSION
from .log import log


class Session(object):
    def __init__(self):
        saved = storage.load()
        self.base_url = saved.get("base_url")
        self._token = saved.get("token")
        self.profile = None
        if saved.get("profile_id"):
            self.profile = {"id": saved["profile_id"], "name": saved.get("profile_name", ""),
                            "is_admin": saved.get("profile_admin", False)}
        self.prefs = {}
        self.libraries = []
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
        self.base_url = base_url
        self.identity_name = name
        self.api.base_url = base_url.rstrip("/")
        storage.update(base_url=base_url, server_name=name)

    def set_token(self, token):
        self._token = token
        storage.update(token=token)

    def set_profile(self, profile):
        self.profile = {"id": profile.get("id"), "name": profile.get("name", ""),
                        "is_admin": profile.get("is_admin", False)}
        storage.update(profile_id=profile.get("id"), profile_name=profile.get("name", ""),
                       profile_admin=profile.get("is_admin", False))

    def forget_profile(self):
        self.profile = None
        self.recommended = {}
        storage.update(profile_id=None, profile_name=None, profile_admin=False)

    def sign_out(self):
        self.api.sign_out()
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
            self.local = (self.api.auth_status() or {}).get("local")  # on the server's home network
        except Exception:
            self.local = None
        self.prefs = self.api.prefs() or {}
        self.libraries = self.api.libraries() or []
        log.info("loaded %d libraries", len(self.libraries))

    def ordered_libraries(self):
        return homerows.ordered_libraries(self.libraries, (self.prefs or {}).get("library_order") or [])

    def home_rows(self):
        return homerows.resolve_home_rows(self.prefs, self.ordered_libraries())

    def art(self, api_path):
        """A Kodi-loadable URL for an Arc image path."""
        return self.artwork.url_for(api_path)
