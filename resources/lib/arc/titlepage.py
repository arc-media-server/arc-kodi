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


def season_tabs(data):
    """A show's seasons from GET /series/{id}/seasons, and the tabs the page shows: the seasons,
    then "Not in This Order" ({"unplaced": True, "episodes": [...]}) when the profile has episodes
    the order doesn't place (`unplaced`), so nothing silently disappears. Play, Resume and Up Next
    follow the seasons alone, as the web does. Returns (seasons, tabs)."""
    data = data if isinstance(data, dict) else {}
    seasons = [s for s in data.get("seasons") or [] if isinstance(s, dict)]
    unplaced = [e for e in data.get("unplaced") or [] if isinstance(e, dict) and e.get("id")]
    tabs = list(seasons)
    if unplaced:
        tabs.append({"unplaced": True, "episodes": unplaced})
    return seasons, tabs


def previous_episode(episodes, current_id):
    """The episode before `current_id` in its season's list, when it's on disk (the player's
    Info card offers it as Previous); None for the first or one not found."""
    ids = [e.get("id") for e in episodes or []]
    if current_id not in ids:
        return None
    at = ids.index(current_id)
    if at == 0 or not episodes[at - 1].get("available", True):
        return None
    return episodes[at - 1]


def season_actions(tab):
    """What a season tab's menu offers, as the web's show page and Plex's season menu: "watched"
    (Mark Season as Watched) or "unwatched" once every episode on disk is watched, then "shuffle"
    when it has more than one episode on disk. Nothing for Not in This Order (it isn't a season
    Arc can mark) or a season with nothing on disk."""
    if not tab or tab.get("unplaced"):
        return []
    on_disk = [e for e in tab.get("episodes") or [] if e.get("available", True)]
    if not on_disk:
        return []
    out = ["unwatched" if all(models.watched(e) for e in on_disk) else "watched"]
    if len(on_disk) > 1:
        out.append("shuffle")
    return out


def season_episode_ids(tab):
    """The season's episodes on disk, in order (for Shuffle Season's play queue)."""
    return [e["id"] for e in (tab or {}).get("episodes") or [] if e.get("id") and e.get("available", True)]


def mark_season(tab, played):
    """The season's episodes as they'll be once Arc has marked them (shown at once): watched or
    not, and no resume point either way. Upcoming episodes (not on disk) are left as they are."""
    out = []
    for e in (tab or {}).get("episodes") or []:
        e = dict(e)
        if e.get("available", True):
            ud = dict(e.get("user_data") or {})
            ud["played"] = bool(played)
            ud["position_ms"] = 0
            e["user_data"] = ud
        out.append(e)
    return out


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


def version_label(f):
    """A version as Play Version… lists it, as the Android app's: its edition (or else its
    resolution), then the rest of its picture and sound and its size."""
    badges = models.file_badges(f)
    edition = (f or {}).get("edition") or ""
    if edition:
        name, rest = edition, badges
    elif badges and badges[0] in ("4K", "1080p", "720p", "SD"):
        name, rest = badges[0], badges[1:]
    else:
        name, rest = ((f or {}).get("container") or "?").upper(), badges
    if (f or {}).get("size"):
        rest = rest + [size_text(f["size"])]
    return name, " · ".join(rest)


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


# MARK: - Play's words and the line under the overview

def clock(ms):
    """A resume point as a clock, as the Android app's: "1:40:12", or "12:34" under an hour."""
    s = max(0, int(ms or 0) // 1000)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return "%d:%02d:%02d" % (h, m, sec) if h else "%d:%02d" % (m, sec)


def play_label(item, action):
    """How Play reads, as the Android app's: (kind, argument) for the Kodi side to word.
    "resume_episode" (Resume S1 · E3) and "play_episode" (Play S1 · E4) take the episode;
    "start_watching" (Start watching · S1 · E1) is a show's first episode with nothing to resume;
    "resume_from" (Resume from 1:40:12) takes the clock; "play" takes nothing."""
    if not action:
        return "play", None
    kind, target, resume = action
    numbered = models.is_episode(target) and models.placed(target)
    if resume > 0 and numbered:
        return "resume_episode", target
    if resume > 0:
        return "resume_from", clock(resume)
    if numbered and models.is_series(item) and target.get("episode_number") == 1 and target.get("season_number") != 0:
        return "start_watching", target
    if numbered:
        return "play_episode", target
    return "play", None


def meta_line(item, episodes_left):
    """The line under the overview, as the Android app's: the year (not an episode's), the running
    time (not a show's) or, for a show, how many episodes are left ("N episodes left", worded by
    `episodes_left(n)`), and the score ("★ 7.9"), joined with " · ". Returned as (the words before
    the score, ending " ·" when a score follows; the score as "7.9" or ""), since Kodi's font has
    no ★ and the page draws it."""
    item = item or {}
    bits = []
    if not models.is_episode(item):
        subtitle = models.year_and_edition(item)
        if subtitle:
            bits.append(subtitle)
    if models.is_series(item):
        left = int(item.get("unwatched_count") or 0)
        if left > 0:
            bits.append(episodes_left(left))
    else:
        rt = models.runtime_text(models.duration_ms(item))
        if rt:
            bits.append(rt)
    try:
        score = float(item.get("rating") or 0)
    except (TypeError, ValueError):
        score = 0.0
    words = " \u00b7 ".join(bits)
    if score <= 0:
        return words, ""
    return (words + " \u00b7" if words else ""), "%.1f" % score


def time_left(ep):
    """An episode card's length, as the Android app's: minutes left once started (at least one),
    else its running time; (left?, "1h 2m") or (False, "") when Arc doesn't know its length."""
    duration = models.duration_ms(ep)
    resume = models.resume_ms(ep)
    if resume > 0 and duration > resume:
        return True, models.runtime_text(max(60000, duration - resume))
    return False, models.runtime_text(duration)


# MARK: - the header's layout

SCREEN = 1080
SEASON_PEEK = 148       # a show's season bar under its header (the Android app's 74 dp)
BODY_LINE = 41          # a line of the description (Kodi's font13, 30 px)
SMALL_LINE = 34         # a line of Starring / Directed by (font12, 25 px)


def hero_layout(series, logo=True, episode_line=False, rating_row=True, overview_lines=3, cut=False,
                meta_row=True, starring_lines=0, director_lines=0):
    """Where the header's parts go, from the foot up, as the Android app's Header: a film's fills
    the screen with a margin of 80 under the buttons; a show's is SEASON_PEEK shorter, its season
    bar under it, with a margin of 16. Tops (and a few heights) in the header's own coordinates,
    for the Kodi side to place: Kodi lays controls out from the top, so the Python stacks them."""
    height = SCREEN - (SEASON_PEEK if series else 0)
    out = {"height": height}
    row = height - (16 if series else 80) - 80              # the buttons' row, 80 high
    out["row"] = row
    out["hint"] = row + 80                                   # their names, in the margin below
    # Starring and Directed by at the right, ending level with the buttons' foot.
    foot = row + 72
    out["directors"] = foot - SMALL_LINE * director_lines
    out["directors_h"] = SMALL_LINE * max(1, director_lines) + 6
    out["starring"] = out["directors"] - (12 if director_lines else 0) - SMALL_LINE * starring_lines
    out["starring_h"] = SMALL_LINE * max(1, starring_lines) + 6
    # The description's block (focusable when cut): 16 above and below inside, the text, MORE,
    # then the line with the year and the capsules.
    y = row - 12 - 16
    if meta_row:
        y -= 40
        out["meta"] = y
        if overview_lines:
            y -= 16
    if cut:
        y -= 32
        out["more"] = y
    if overview_lines:
        y -= BODY_LINE * overview_lines
        out["overview"] = y
        out["overview_h"] = BODY_LINE * overview_lines + 6
    y -= 16
    out["block"] = y
    out["block_h"] = row - 12 - y
    if rating_row:
        y -= 4 + 40
        out["genres"] = y
    if episode_line:
        y -= 16 + 40
        out["episode"] = y
    y -= 32
    out["logo"] = y - 240                                    # its foot at y, 240 at most
    out["title"] = y - 84
    return out


# MARK: - fitting words

_NARROW, _MID, _WIDE = set("ijlI.,:;'|!tf "), set("rsz-"), set("mwMW")


def text_width(label, names, size=25):
    """Roughly how wide "<label> <names, in bold>" draws in Kodi's standard font at `size` px:
    Kodi can't measure a label for an add-on, and won't bottom-align one that wraps, so the title
    page places Starring by this. Calibrated on Kodi's Noto Sans against lines seen to fit or wrap
    in 620 px."""
    return plain_width(label + " ", size) + plain_width(names, size, bold=True)


def plain_width(text, size=25, bold=False):
    """Roughly how wide `text` draws in Kodi's standard font at `size` px (see text_width)."""
    total = 0.0
    for c in text or "":
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


def wraps(label, names, room=605):
    """Whether "<label> <names>" needs a second line in a 620-wide label (605 leaves a margin)."""
    return text_width(label, names) > room


def wrap_lines(text, room, size=30):
    """`text` as Kodi would wrap it into lines `room` px wide (by plain_width's estimate)."""
    lines = []
    for para in (text or "").splitlines() or [""]:
        line = ""
        for word in para.split():
            trial = (line + " " + word) if line else word
            if line and plain_width(trial, size) > room:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def clip(text, room, size=30, max_lines=3):
    """The text cut to `max_lines` lines with "…", as Compose's maxLines and Ellipsis do, and
    whether it was cut (the title page then shows MORE). Kodi can't tell an add-on whether a
    textbox's text overflowed, so the add-on decides from its estimate (a little short of `room`,
    so Kodi's own wrapping doesn't need a line more)."""
    lines = wrap_lines(text, room, size)
    if len(lines) <= max_lines:
        return text or "", False, len(lines)
    kept = lines[:max_lines]
    last = kept[-1]
    while last and plain_width(last + "\u2026", size) > room:
        last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
    kept[-1] = last.rstrip(" ,.;:") + "\u2026"
    return " ".join(kept), True, max_lines
