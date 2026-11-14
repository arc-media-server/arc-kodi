"""The title page's choices, as the Apple and Android apps make them: what Play plays and how
its button reads, the background's four colours, and the About / Details / Crew / Playback
cards. Plain Python (no Kodi), so the tests cover it; the Kodi side only words and draws it.
"""

import colorsys

from . import models


# MARK: - the background's colours

def toned(hex_colour):
    """A palette colour calmer and darker, so white text stays readable on it (the Apple app's
    RGB.toned()): the hue is kept, the saturation is at most 0.55, the brightness 0.12-0.30.
    "#rrggbb" in, Kodi's "FFRRGGBB" out; None for something unreadable."""
    h = (hex_colour or "").strip().lstrip("#")
    if len(h) != 6:
        return None
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return None
    mx, mn = max(r, g, b), min(r, g, b)
    hue, _, _ = colorsys.rgb_to_hsv(r, g, b)
    sat = 0.0 if mx == 0 else min((mx - mn) / mx * 0.8, 0.55)
    val = min(max(mx * 0.6, 0.12), 0.30)
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return "FF%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


# The wash when a title has no palette (the Apple app's ArcColor.wash), as the corners are listed.
WASH = ["FF25282D", "FF222429", "FF1B1B1D", "FF1E1F1E"]


def palette_corners(palette):
    """The four toned corner colours (top left, top right, bottom left, bottom right) from
    GET /items/{id}/artwork/palette, or None when there's no palette."""
    if not palette or not palette.get("available"):
        return None
    c = palette.get("colors") or {}
    out = [toned(c.get(k)) for k in ("top_left", "top_right", "bottom_left", "bottom_right")]
    return out if all(out) else None


# MARK: - what Play plays

def next_to_play(seasons):
    """For a show: the episode to play, as Plex's Play button picks it: the first one part-way
    through, else the first not yet watched (in the profile's order, specials last), else the
    first. None when nothing is on disk."""
    regular = [s for s in seasons or [] if (s.get("season_number") or 0) > 0]
    specials = [s for s in seasons or [] if (s.get("season_number") or 0) == 0]
    episodes = [e for s in regular + specials for e in s.get("episodes") or [] if e.get("available", True)]
    for e in episodes:
        if models.resume_ms(e) > 0:
            return e
    for e in episodes:
        if not models.watched(e):
            return e
    return episodes[0] if episodes else None


def play_action(item, episode=None):
    """What the Play button does: ("resume" | "play", the playable item, its resume point).
    `episode` is next_to_play() for a show."""
    target = episode if models.is_series(item) else item
    if not target or not models.playable(target):
        return None
    resume = models.resume_ms(target)
    return ("resume" if resume > 0 else "play", target, resume)


# MARK: - the cards at the foot

def people(item, roles, limit=3):
    names = []
    for c in item.get("credits") or []:
        if (c.get("role") or "actor") in roles and c.get("name") and c["name"] not in names:
            names.append(c["name"])
    return names[:limit]


def details_lines(item):
    """The Details card: (key, value) pairs, keys for the Kodi side to word."""
    out = []
    if item.get("release_date"):
        out.append(("released", item["release_date"]))
    rt = models.runtime_text(models.duration_ms(item))
    if rt:
        out.append(("runtime", rt))
    if item.get("content_rating"):
        out.append(("rated", item["content_rating"]))
    if item.get("genres"):
        out.append(("genres", ", ".join(item["genres"][:4])))
    return out


def crew_lines(item):
    out = []
    directors = people(item, ("director",))
    if directors:
        out.append(("directed", ", ".join(directors)))
    writers = people(item, ("writer", "screenplay", "author"))
    if writers:
        out.append(("written", ", ".join(writers)))
    if item.get("studio"):
        out.append(("studios", item["studio"]))
    return out


def size_text(size):
    size = float(size or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return ("%.1f %s" % (size, unit)) if unit in ("GB", "TB") else ("%d %s" % (size, unit))
        size /= 1024.0


def playback_lines(item, server_name="", local=None, profile_name=""):
    """The Playback card: the server, the connection, the profile and the file's quality."""
    out = []
    if server_name:
        out.append(("server", server_name))
    if local is not None:
        out.append(("connection", "home" if local else "remote"))
    if profile_name:
        out.append(("profile", profile_name))
    badges = models.quality_badges(item)
    if badges:
        out.append(("quality", " · ".join(badges)))
    f = models.main_file(item)
    if f:
        if f.get("bitrate"):
            out.append(("bitrate", "%.1f Mbps" % (f["bitrate"] / 1000000.0)))
        if f.get("size"):
            out.append(("size", size_text(f["size"])))
        path = f.get("path") or ""
        if path:
            out.append(("file", path.replace("\\", "/").rsplit("/", 1)[-1]))
    return out


def starring(item, limit=3):
    return people(item, ("actor", ""), limit)


# MARK: - fitting words

_NARROW, _MID, _WIDE = set("ijlI.,:;'|!tf "), set("rsz-"), set("mwMW")


def text_width(label, names, size=25):
    """Roughly how wide "<label> <names, in bold>" draws in Kodi's standard font at `size` px:
    Kodi can't measure a label for an add-on, and won't bottom-align one that wraps, so the title
    page places Starring by this. Calibrated on Kodi's Noto Sans against lines seen to fit or wrap
    in 620 px."""
    def width(text, bold):
        total = 0.0
        for c in text:
            if c in _NARROW:
                em = 0.27
            elif c in _MID:
                em = 0.42
            elif c in _WIDE:
                em = 0.85
            elif c.isupper():
                em = 0.64
            else:
                em = 0.55
            total += em * (1.07 if bold else 1.0)
        return total * size
    return width(label + " ", False) + width(names, True)


def wraps(label, names, room=605):
    """Whether "<label> <names>" needs a second line in a 620-wide label (605 leaves a margin)."""
    return text_width(label, names) > room
