"""Settings, as the Android and Apple apps': sections with headings (Playback, Subtitles, Watch
Together, Profile and Server, About), each row a dark pill with its name and value, the focused
one white. The profile's choices (Auto-Play, Skip Intros, Hide Spoilers, the audio language, when
and how subtitles show) are saved to Arc's prefs so every app follows them; then Switch Profile,
Sign Out and Change Server; then About. The entries are arc/settings.py's; this draws them, steps
over the headings and notes, and saves."""

import xbmc

from arc import settings

from ..compat import ADDON_VERSION, T
from ..log import log
from . import menu
from .base import ArcWindow, list_item
from .signin import PROFILE_COLOURS

SERVER = 100
PROFILE = 101
INITIALS = 102
ABOUT = 104
ROWS = 110

A_UP, A_DOWN, A_PAGE_UP, A_PAGE_DOWN = 3, 4, 5, 6

NAMES = {"auto_play": 30297, "auto_skip": 30298, "hide_spoilers": 30390, "audio_language": 30391,
         "subtitle_mode": 30393, "subtitle_language": 30394, "subtitle_size": 30395, "subtitle_color": 30396,
         "subtitle_background": 30397, "subtitle_position": 30398, "join_code": 30342,
         "switch_profile": 30202, "sign_out": 30063, "change_server": 30305, "about": 30307}
# Theme music
NAMES["theme_music"] = 30540
NAMES["show_missing_episodes"] = 30614
HEADINGS = {"playback": 30296, "subtitles": 30185, "together": 30330, "profile": 30308, "about": 30307}
NOTES = {"playback_note": 30410, "style_note": 30411}
VALUE_NAMES = {
    "subtitle_mode": {"": 30299, "foreign": 30300, "always": 30301, "manual": 30302},
    "subtitle_size": {"small": 30399, "medium": 30400, "large": 30401, "huge": 30402},
    "subtitle_color": {"white": 30403, "yellow": 30404},
    "subtitle_background": {"box": 30405, "solid": 30406, "none": 30407},
    "subtitle_position": {"bottom": 30408, "top": 30409},
}


def language_name(code):
    if not code:
        return ""
    try:
        name = xbmc.convertLanguage(code, xbmc.ENGLISH_NAME)
    except Exception:
        name = ""
    return name or code


class SettingsWindow(ArcWindow):
    xml = "script-arc-settings.xml"

    def on_init(self):
        self.entries = settings.layout(together=self.session.together.available)
        name = (self.session.profile or {}).get("name", "")
        self.set_label(PROFILE, name)
        self.set_label(INITIALS, name[:1].upper())
        self.set_label(SERVER, self.session.identity_name or "")
        self.setProperty("colorhex", PROFILE_COLOURS.get(
            (self.session.profile or {}).get("color"), PROFILE_COLOURS["violet"]))
        self.set_text(ABOUT, T(30309))
        self._fill()
        first = next(i for i, (kind, _) in enumerate(self.entries) if kind == "row")
        self.list_control(ROWS).selectItem(first)
        self._pos = first
        self.focus_id(ROWS)

    # MARK: - the list

    def _name(self, key, v):
        """A choice's words."""
        if key in ("audio_language", "subtitle_language"):
            if not v:
                return T(30392) if key == "audio_language" else T(30382)
            return language_name(v)
        return T(VALUE_NAMES[key][v]) if key in VALUE_NAMES and v in VALUE_NAMES[key] else (v or "")

    def _detail(self, key):
        v = settings.value(self.session.prefs, key)
        if key in settings.SWITCHES:
            return T(30303) if v else T(30304)
        if settings.choices(key) is not None:
            return self._name(key, v)
        if key == "about":
            return T(30203) % ADDON_VERSION
        if key == "change_server":
            return self.session.identity_name or ""
        return ""

    def _fill(self):
        """Fills the list once; after a change only the rows' values change, in place (refilling
        would move the focus and lose a key pressed meanwhile)."""
        ctrl = self.list_control(ROWS)
        if ctrl.size() == len(self.entries):
            for i, (kind, key) in enumerate(self.entries):
                if kind == "row":
                    ctrl.getListItem(i).setLabel2(self._detail(key))
            return
        ctrl.reset()
        items = []
        for kind, key in self.entries:
            if kind == "heading":
                items.append(list_item(T(HEADINGS[key]), props={"kind": "heading"}))
            elif kind == "note":
                items.append(list_item(T(NOTES[key]), props={"kind": "note"}))
            else:
                items.append(list_item(T(NAMES[key]), self._detail(key), props={"kind": "row"}))
        ctrl.addItems(items)

    def on_action(self, action, code):
        """Headings and notes can't be chosen: Kodi has already moved onto one, so step on to the
        next row that way (or back, at either end)."""
        if code not in (A_UP, A_DOWN, A_PAGE_UP, A_PAGE_DOWN) or self.getFocusId() != ROWS:
            return False
        ctrl = self.list_control(ROWS)
        pos = ctrl.getSelectedPosition()
        if pos != self._pos:
            down = pos > self._pos
        else:
            down = code in (A_DOWN, A_PAGE_DOWN)
        target = self._row_from(pos, 1 if down else -1)
        if target is None:
            target = self._row_from(pos, -1 if down else 1)
        if target is not None and target != pos:
            ctrl.selectItem(target)
        self._pos = target if target is not None else pos
        return False

    def _row_from(self, pos, step):
        i = pos
        while 0 <= i < len(self.entries):
            if self.entries[i][0] == "row":
                return i
            i += step
        return None

    # MARK: - choosing

    def on_live(self, change):
        # The app has fetched the profile's prefs again; show them.
        if change.personal():
            self._fill()

    def on_click(self, control_id):
        if control_id != ROWS:
            return
        pos = self.list_control(ROWS).getSelectedPosition()
        if not 0 <= pos < len(self.entries) or self.entries[pos][0] != "row":
            return
        key = self.entries[pos][1]
        values = settings.choices(key)
        if key in settings.SWITCHES:
            self._save(settings.change(self.session.prefs, key))
        elif values is not None:
            current = settings.value(self.session.prefs, key)
            choice = menu.choose(T(NAMES[key]), [self._name(key, v) for v in values],
                                 selected=values.index(current) if current in values else -1)
            if choice >= 0 and values[choice] != current:
                self._save(settings.change(self.session.prefs, key, values[choice]))
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
