"""The Settings screen's rows, as the Android and Apple apps' Settings: sections with headings
(Playback, Subtitles, Watch Together, Profile and Server, About), each row a name and its value.
The profile's choices are saved to Arc (PATCH /me/prefs) so every app follows them. Plain Python;
the Kodi side words and draws it.

Only keys GET /me/prefs already has (the server's docs/api-v1-contract.txt)."""

# Show Subtitles: the value Arc stores, as the apps offer them.
SUBTITLE_MODES = ["", "foreign", "always", "manual"]

# The languages offered for audio and subtitles (the apps' list), as Arc stores them; "" is the
# file's default (audio) or none (subtitles).
LANGUAGES = ["eng", "fra", "deu", "spa", "ita", "por", "nld", "swe", "nor", "dan", "fin", "pol", "ces",
             "hun", "ell", "tur", "rus", "ukr", "ara", "heb", "hin", "jpn", "kor", "zho", "tha", "vie"]

# subtitle_style: each field's choices (the first is the default) as the Android app offers them.
STYLE = {
    "subtitle_size": ("size", ["medium", "small", "large", "huge"]),
    "subtitle_color": ("color", ["white", "yellow"]),
    "subtitle_background": ("background", ["box", "solid", "none"]),
    "subtitle_position": ("position", ["bottom", "top"]),
}

SWITCHES = ("auto_play", "auto_skip", "hide_spoilers")
# Theme music
SWITCHES += ("theme_music",)
# Show missing episodes on show pages (one profile setting, as Android and the web)
SWITCHES += ("show_missing_episodes",)

# Sections in order: (heading, rows, note after them or None).
SECTIONS = [
    ("playback", ["auto_play", "auto_skip", "theme_music", "hide_spoilers", "show_missing_episodes",
                  "audio_language"], "playback_note"),
    ("subtitles", ["subtitle_mode", "subtitle_language", "subtitle_size", "subtitle_color",
                   "subtitle_background", "subtitle_position"], "style_note"),
    ("together", ["join_code"], None),
    ("profile", ["switch_profile", "sign_out", "change_server"], None),
    ("about", ["about"], None),
]


def layout(together=False):
    """The list's entries, top to bottom: ("heading", section), ("row", key) and ("note", key).
    Watch Together shows only where Arc allows it."""
    out = []
    for section, rows, note in SECTIONS:
        if section == "together" and not together:
            continue
        out.append(("heading", section))
        out += [("row", key) for key in rows]
        if note:
            out.append(("note", note))
    return out


def rows(together=False):
    """Just the rows' keys, in order."""
    return [key for kind, key in layout(together) if kind == "row"]


def choices(key):
    """The values a choice row offers, or None for a switch or an action."""
    if key == "subtitle_mode":
        return list(SUBTITLE_MODES)
    if key in ("audio_language", "subtitle_language"):
        return [""] + LANGUAGES
    if key in STYLE:
        return list(STYLE[key][1])
    return None


def style(prefs):
    """The profile's subtitle_style with every field filled in (missing or unknown ones default)."""
    have = (prefs or {}).get("subtitle_style") or {}
    out = {}
    for field, values in STYLE.values():
        v = have.get(field) if isinstance(have, dict) else None
        out[field] = v if v in values else values[0]
    return out


def value(prefs, key):
    """The row's current value: True/False for a switch, the stored value for a choice, None for
    an action."""
    prefs = prefs or {}
    # Theme music defaults on, as Android.
    if key == "theme_music":
        return prefs.get("theme_music", True) is not False
    if key == "auto_play":
        return prefs.get("auto_play", True) is not False
    if key in ("auto_skip", "hide_spoilers", "show_missing_episodes"):
        return bool(prefs.get(key))
    if key == "subtitle_mode":
        mode = prefs.get("subtitle_mode") or ""
        return mode if mode in SUBTITLE_MODES else ""
    if key in ("audio_language", "subtitle_language"):
        return prefs.get(key) or ""
    if key in STYLE:
        return style(prefs)[STYLE[key][0]]
    return None


def change(prefs, key, choice=None):
    """The prefs change choosing a row makes: a switch turns over; a choice takes `choice`. A
    subtitle style field sends the whole style, as the apps do."""
    if key in SWITCHES:
        return {key: not value(prefs, key)}
    if key in ("subtitle_mode", "audio_language", "subtitle_language"):
        return {key: choice or ""}
    if key in STYLE and choice in STYLE[key][1]:
        whole = style(prefs)
        whole[STYLE[key][0]] = choice
        return {"subtitle_style": whole}
    return {}
