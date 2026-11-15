"""Settings, as the Apple app's SettingsView: the profile's playback choices (Auto-Play, Skip
Intros, Subtitles), saved to Arc's prefs so every app follows them; then Switch Profile, Sign Out
and Change Server; then About. The rows are arc/settings.py's; this draws them and saves."""

from arc import settings

from ..compat import ADDON_VERSION, T
from ..log import log
from . import menu
from .base import ArcWindow, list_item

SERVER = 100
PROFILE = 101
ABOUT = 104
ROWS = 110

NAMES = {"auto_play": 30297, "auto_skip": 30298, "subtitle_mode": 30185, "join_code": 30342,
         "switch_profile": 30202, "sign_out": 30063, "change_server": 30305, "about": 30307}
SECTIONS = {"auto_play": 30296, "join_code": 30330, "switch_profile": 30308, "about": 30307}
MODE_NAMES = {"": 30299, "foreign": 30300, "always": 30301, "manual": 30302}


class SettingsWindow(ArcWindow):
    xml = "script-arc-settings.xml"

    def on_init(self):
        self.rows = settings.rows(together=self.session.together.available)
        self.set_label(PROFILE, (self.session.profile or {}).get("name", ""))
        self.set_label(SERVER, self.session.identity_name or "")
        self.set_text(ABOUT, T(30309))
        self._fill()
        self.focus_id(ROWS)

    def _detail(self, key):
        v = settings.value(self.session.prefs, key)
        if key in ("auto_play", "auto_skip"):
            return T(30303) if v else T(30304)
        if key == "subtitle_mode":
            return T(MODE_NAMES[v])
        if key == "about":
            return T(30203) % ADDON_VERSION
        if key == "change_server":
            return self.session.identity_name or ""
        return ""

    def _fill(self):
        """Fills the rows once; after a change only their values change, in place (refilling the
        list would move the focus and lose a key pressed meanwhile)."""
        ctrl = self.list_control(ROWS)
        if ctrl.size() == len(self.rows):
            for i, key in enumerate(self.rows):
                ctrl.getListItem(i).setLabel2(self._detail(key))
            return
        ctrl.reset()
        for key in self.rows:
            section = T(SECTIONS[key]) if key in SECTIONS else ""
            ctrl.addItem(list_item(T(NAMES[key]), self._detail(key), props={"section": section}))

    def on_live(self, change):
        # The app has fetched the profile's prefs again; show them.
        if change.personal():
            self._fill()

    def on_click(self, control_id):
        if control_id != ROWS:
            return
        pos = self.list_control(ROWS).getSelectedPosition()
        if not 0 <= pos < len(self.rows):
            return
        key = self.rows[pos]
        if key in ("auto_play", "auto_skip"):
            self._save(settings.change(self.session.prefs, key))
        elif key == "subtitle_mode":
            modes = settings.SUBTITLE_MODES
            current = modes.index(settings.value(self.session.prefs, key))
            choice = menu.choose(T(30185), [T(MODE_NAMES[m]) for m in modes], selected=current)
            if choice >= 0 and choice != current:
                self._save(settings.change(self.session.prefs, key, modes[choice]))
        elif key == "join_code":
            self.result = "join_code"
            self.close()
        elif key == "switch_profile":
            self.result = "switch_profile"
            self.close()
        elif key == "sign_out":
            if menu.confirm(T(30063), T(30178) % (self.session.identity_name or "Arc"), T(30063)):
                self.result = "sign_out"
                self.close()
        elif key == "change_server":
            if menu.confirm(T(30305), T(30178) % (self.session.identity_name or "Arc"), T(30305)):
                self.result = "change_server"
                self.close()

    def _save(self, change):
        """Saves a change to the profile's prefs on Arc, then shows it; says so if it wasn't saved."""
        if not change:
            return

        def done(_result, error):
            if error is not None:
                log.warning("settings change not saved: %s", type(error).__name__)
                menu.choose(T(30084), [T(30000)], message=T(30306))
                return
            self.session.prefs.update(change)
            log.info("settings changed: %s", ", ".join(sorted(change)))
            self._fill()

        self.run_async(lambda: self.session.api.patch_prefs(change), done)

    def on_back(self):
        self.result = "back"
        self.close()
