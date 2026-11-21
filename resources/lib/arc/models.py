"""Helpers over Arc's answers (plain dicts), as the Apple app's ArcKit models read them.

Every field is optional: read with .get() and fall back, since v1 only ever adds fields.
"""

import datetime


def images(item):
    return (item or {}).get("images") or {}


def is_episode(item):
    return (item or {}).get("kind") == "episode"


def is_series(item):
    return (item or {}).get("kind") == "series"


def playable(item):
    return (item or {}).get("kind") in ("movie", "episode")


def user_data(item):
    return (item or {}).get("user_data") or {}


def duration_ms(item):
    """How long it runs, as well as Arc knows: the file's length, or the listed runtime."""
    for f in (item or {}).get("files") or []:
        if not f.get("missing") and (f.get("duration_ms") or 0) > 0:
            return int(f["duration_ms"])
    return int((item or {}).get("runtime_min") or 0) * 60000


def resume_ms(item):
    """A resume point, if the profile is part-way through."""
    ud = user_data(item)
    if ud.get("played"):
        return 0
    return int(ud.get("position_ms") or 0)


def watched(item):
    if is_series(item):
        return item.get("unwatched_count") == 0
    return bool(user_data(item).get("played"))


def spoiler_hidden(prefs, item):
    """With the profile's Hide Spoilers on, whether an episode's still and description are kept
    back: an episode the profile hasn't started (as the web's spoiler guard)."""
    if not (prefs or {}).get("hide_spoilers") or not is_episode(item):
        return False
    ud = user_data(item)
    return not ud.get("played") and not ud.get("position_ms")


def watchlisted(item):
    return bool(user_data(item).get("watchlisted"))


def progress(item):
    """How far through, 0-1, or None when not started (at least a sliver once started)."""
    d = duration_ms(item)
    r = resume_ms(item)
    if r <= 0 or d <= 0:
        return None
    return min(1.0, max(0.02, float(r) / d))


def placed(item):
    """Whether an episode has a place in its show's order. Arc sends 0/0 for one outside it (Not
    in This Order), and those must never read "S0 · E0"."""
    s, e = (item or {}).get("season_number"), (item or {}).get("episode_number")
    return s is not None and bool(e)


def episode_code(item, code, special):
    """An episode's number as every Arc app writes it: `code` ("S%d · E%d") filled in as
    "S1 · E4", `special` ("Special %d") for season 0, or "" when Arc doesn't place it."""
    if not placed(item):
        return ""
    s, e = item.get("season_number"), item.get("episode_number")
    return special % e if s == 0 else code % (s, e)


def episode_heading(item, code, special, unplaced=False):
    """Where the episode itself is the subject (the player, episode lists, Up Next): its number
    then its title, "S1 · E4 · Pilot"; just the title outside the show's order (`unplaced`, or
    Arc's 0/0)."""
    title = (item or {}).get("title", "")
    number = "" if unplaced else episode_code(item, code, special)
    return " · ".join(x for x in (number, title) if x)


def main_file(item, file_id=None):
    files = [f for f in (item or {}).get("files") or [] if not f.get("missing")]
    if file_id is not None:
        for f in files:
            if f.get("id") == file_id:
                return f
    return files[0] if files else None


def video_stream(f):
    for st in (f or {}).get("streams") or []:
        if st.get("kind") == "video" and st.get("codec") not in ("mjpeg", "png", "bmp"):
            return st
    return None


def audio_stream(f):
    first = None
    for st in (f or {}).get("streams") or []:
        if st.get("kind") != "audio":
            continue
        if st.get("is_default") or st.get("default"):
            return st
        first = first or st
    return first


def versions(item):
    """A title's versions to choose from (as the player's Version list): its files on disk, the
    first part of each."""
    return [f for f in (item or {}).get("files") or []
            if not f.get("missing") and (f.get("part") or 0) <= 1]


AUDIO_CODECS = {"eac3": "DD+", "ac3": "DD", "truehd": "TrueHD", "aac": "AAC", "flac": "FLAC",
                "opus": "Opus", "mp3": "MP3"}


def quality_badges(item):
    """The title page's badges: resolution, dynamic range, sound ("4K", "DV", "Atmos"...)."""
    return file_badges(main_file(item))


def file_badges(f):
    """One file's resolution, dynamic range and sound, as quality_badges."""
    out = []
    v = video_stream(f)
    if v:
        h, w = v.get("height") or 0, v.get("width") or 0
        if h >= 1600 or w >= 3200:
            out.append("4K")
        elif h >= 900 or w >= 1700:
            out.append("1080p")
        elif h >= 650 or w >= 1200:
            out.append("720p")
        elif h > 0:
            out.append("SD")
        transfer = (v.get("color_transfer") or "").lower()
        if v.get("dolby_vision"):
            out.append("DV")
        if v.get("hdr10_plus"):
            out.append("HDR10+")
        elif transfer == "smpte2084":
            out.append("HDR10")
        elif transfer == "arib-std-b67":
            out.append("HLG")
        elif not v.get("dolby_vision"):
            out.append("SDR")
    a = audio_stream(f)
    if a:
        # As Android's capsules: the codec and its channels together ("DD+ 5.1", "AAC 2.0"),
        # then Atmos on its own.
        codec = (a.get("codec") or "").lower()
        profile = a.get("profile") or ""
        if codec == "dts":
            name = "DTS:X" if "dts:x" in profile.lower() else "DTS-HD MA" if "MA" in profile else "DTS"
        else:
            name = AUDIO_CODECS.get(codec, codec.upper())
        ch = a.get("channels") or 0
        channels = {1: "1.0", 2: "2.0", 6: "5.1", 8: "7.1"}.get(ch, "%dch" % ch if ch else "")
        sound = " ".join(x for x in (name, channels) if x)
        if sound:
            out.append(sound)
        if "atmos" in profile.lower() or codec == "truehd" and "atmos" in (a.get("title") or "").lower():
            out.append("Atmos")
    return out


def credits_by_role(item, roles):
    return [c for c in (item or {}).get("credits") or [] if (c.get("role") or "actor") in roles]


def actors(item):
    return [c for c in (item or {}).get("credits") or [] if c.get("role") in ("actor", "", None)]


def upcoming_release(item, today=None):
    """The day an episode not yet on the server airs, when that's after today; else None."""
    if (item or {}).get("available", True):
        return None
    iso = item.get("release_date") or ""
    try:
        day = datetime.date(*[int(p) for p in iso.split("-")[:3]])
    except (TypeError, ValueError):
        return None
    today = today or datetime.date.today()
    return day if day > today else None


def runtime_text(ms):
    """"1h 32m", "45m"; "" for nothing."""
    minutes = int(round((ms or 0) / 60000.0))
    if minutes <= 0:
        return ""
    if minutes < 60:
        return "%dm" % minutes
    return "%dh %dm" % (minutes // 60, minutes % 60) if minutes % 60 else "%dh" % (minutes // 60)


def clock(ms):
    """A time on the timeline: "1:02:03" or "2:03"."""
    s = max(0, int((ms or 0) // 1000))
    h, m, s = s // 3600, (s // 60) % 60, s % 60
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)
