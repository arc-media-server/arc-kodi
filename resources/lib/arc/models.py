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


def watchlisted(item):
    return bool(user_data(item).get("watchlisted"))


def progress(item):
    """How far through, 0-1, or None when not started (at least a sliver once started)."""
    d = duration_ms(item)
    r = resume_ms(item)
    if r <= 0 or d <= 0:
        return None
    return min(1.0, max(0.02, float(r) / d))


def episode_code(item):
    """"S1 · E4" style numbers, or "" when Arc doesn't place it."""
    s, e = (item or {}).get("season_number"), (item or {}).get("episode_number")
    if s is None or e is None:
        return ""
    return "S%d · E%d" % (s, e)


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


def quality_badges(item):
    """The title page's badges: resolution, dynamic range, sound ("4K", "DV", "Atmos"...)."""
    f = main_file(item)
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
    a = audio_stream(f)
    if a:
        codec = a.get("codec") or ""
        profile = (a.get("profile") or "").lower()
        if "atmos" in profile or codec == "truehd" and "atmos" in (a.get("title") or "").lower():
            out.append("Atmos")
        elif codec in ("truehd",):
            out.append("TrueHD")
        elif codec == "dts":
            out.append("DTS-HD" if "hd" in profile else "DTS")
        elif codec == "eac3":
            out.append("DD+")
        elif codec == "ac3":
            out.append("DD")
        ch = a.get("channels") or 0
        if ch >= 8:
            out.append("7.1")
        elif ch >= 6:
            out.append("5.1")
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
