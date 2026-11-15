"""The Settings screen's rows, as the Apple app's SettingsView: the profile's playback choices,
saved to Arc (PATCH /me/prefs) so every app follows them, then the profile and server, then
About. Plain Python; the Kodi side words and draws it."""

# The Subtitles choice: the value Arc stores, as the Apple app offers them.
SUBTITLE_MODES = ["", "foreign", "always", "manual"]

ROWS = ["auto_play", "auto_skip", "subtitle_mode", "join_code", "switch_profile", "sign_out", "change_server", "about"]


def rows(together=False):
    """The rows shown: Join with a Code (Watch Together) only where Arc allows Watch Together."""
    return [r for r in ROWS if r != "join_code" or together]


def value(prefs, key):
    """The row's current value: True/False for a switch, the mode for Subtitles, None otherwise."""
    prefs = prefs or {}
    if key == "auto_play":
        return prefs.get("auto_play", True) is not False
    if key == "auto_skip":
        return bool(prefs.get("auto_skip"))
    if key == "subtitle_mode":
        mode = prefs.get("subtitle_mode") or ""
        return mode if mode in SUBTITLE_MODES else ""
    return None


def change(prefs, key, choice=None):
    """The prefs change choosing a row makes: a switch turns over; Subtitles takes `choice`."""
    if key in ("auto_play", "auto_skip"):
        return {key: not value(prefs, key)}
    if key == "subtitle_mode":
        return {key: choice or ""}
    return {}
