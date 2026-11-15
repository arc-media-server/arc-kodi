"""Settings: the server and profile, Switch Profile and Sign Out. The real viewing preferences
(subtitles, audio, auto-play) live on the server (the profile's prefs), set in Arc's own apps;
this screen is only what Kodi needs."""

from ..compat import ADDON_VERSION, T
from . import menu
from .base import ArcWindow

SERVER = 100
PROFILE = 101
SWITCH = 102
SIGN_OUT = 103
VERSION = 104


class SettingsWindow(ArcWindow):
    xml = "script-arc-settings.xml"

    def on_init(self):
        self.set_label(SERVER, T(30200) % (self.session.identity_name or ""))
        name = (self.session.profile or {}).get("name", "")
        self.set_label(PROFILE, T(30201) % name)
        self.set_label(SWITCH, T(30202))
        self.set_label(SIGN_OUT, T(30063))
        self.set_label(VERSION, T(30203) % ADDON_VERSION)
        self.focus_id(SWITCH)

    def on_click(self, control_id):
        if control_id == SWITCH:
            self.result = "switch_profile"
            self.close()
        elif control_id == SIGN_OUT:
            if menu.confirm(T(30063), T(30178) % (self.session.identity_name or "Arc"), T(30063)):
                self.result = "sign_out"
                self.close()

    def on_back(self):
        self.result = "back"
        self.close()
