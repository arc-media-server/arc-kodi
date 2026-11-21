"""Home's rows, as the web arranges them (web/src/lib/home.ts resolveRows; the Apple app's
ArcKit/HomeRows.swift): carrying on watching first, then each library's newest and its own filter
rows in the profile's library order, the Watchlist at its place among them, and collections and
playlists last. The layout is arranged on the web; Kodi follows it.
"""

import datetime

from . import models

POSTER, THUMB, BACKDROP = "poster", "thumb", "backdrop"

# The seasonal row's picks and their dates (month*100 + day), with their /items queries.
SEASONAL = [
    ("romance", (201, 214), {"kind": "movie", "genre": "Romance", "sort": "shuffle"}),
    ("horror", (1001, 1031), {"kind": "movie", "genre": "Horror", "sort": "shuffle"}),
    ("christmas", (1201, 1231),
     {"kind": "movie", "about": "christmas,santa,xmas,north pole,reindeer,elves", "sort": "shuffle"}),
]


def seasonal_pick(today=None):
    today = today or datetime.date.today()
    md = today.month * 100 + today.day
    for name, (start, end), query in SEASONAL:
        if start <= md <= end:
            return name, query
    return None


def ordered_libraries(libraries, order):
    """The libraries in the profile's order (Arrange libraries on the web); new ones go last."""
    order = list(order or [])
    rank = {}
    for i, lib_id in enumerate(order):
        rank.setdefault(lib_id, i)
    indexed = list(enumerate(libraries or []))
    indexed.sort(key=lambda p: (rank.get(p[1].get("id"), len(order) + p[0]), p[0]))
    return [lib for _, lib in indexed]


def card_style(saved):
    return {"poster": POSTER, "thumb": THUMB, "arc": BACKDROP}.get(saved)


def _query_value(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if v is None:
        return ""
    return str(v)


def resolve_home_rows(prefs, libraries, today=None):
    """The profile's Home rows: dicts with id, source (a tuple naming what to load), style and
    season_posters. `libraries` must be in the profile's order. Hidden rows are left out."""
    prefs = prefs or {}
    home = prefs.get("home") or []
    saved = {}
    for row in home:
        saved.setdefault(row.get("id"), row)

    def shown(row_id):
        return not (saved.get(row_id) or {}).get("hidden")

    out = []

    def carry_on(row_id, source):
        row = saved.get(row_id) or {}
        out.append({"id": row_id, "source": source, "style": card_style(row.get("style")) or THUMB,
                    "season_posters": row.get("posters") == "season"})

    split = bool(prefs.get("split_up_next"))
    if shown("continue"):
        carry_on("continue", ("continue", not split))
    if split and shown("next-up"):
        carry_on("next-up", ("next-up",))
    pick = seasonal_pick(today)
    if pick and shown("seasonal"):
        out.append({"id": "seasonal", "source": ("seasonal", pick[0], pick[1]), "style": POSTER, "season_posters": False})
    watchlist_at = min(max(int(prefs.get("watchlist_position") or 0), 0), len(libraries))
    watchlist = {"id": "watchlist", "source": ("watchlist",), "style": POSTER, "season_posters": False}
    for i, lib in enumerate(libraries):
        if i == watchlist_at and shown("watchlist"):
            out.append(dict(watchlist))
        # Home videos rarely have posters worth showing: their rows use thumbnails.
        look = THUMB if lib.get("kind") == "videos" else POSTER
        recent = "recent:%s" % lib.get("id")
        if shown(recent):
            out.append({"id": recent, "source": ("recent", lib, bool((saved.get(recent) or {}).get("shows_only"))),
                        "style": look, "season_posters": True})
        for row in home:
            rid = row.get("id") or ""
            if not rid.startswith("custom:") or row.get("hidden"):
                continue
            flt, title = row.get("filter"), (row.get("title") or "").strip()
            if not isinstance(flt, dict) or not title or _query_value(flt.get("library_id")) != str(lib.get("id")):
                continue
            out.append({"id": rid, "source": ("custom", title, lib, flt), "style": look, "season_posters": False})
    if watchlist_at == len(libraries) and shown("watchlist"):
        out.append(dict(watchlist))
    # Collections and playlists come last, in the order they were added (no library to follow).
    for row in home:
        rid = row.get("id") or ""
        if row.get("hidden"):
            continue
        if rid.startswith("collection:"):
            out.append({"id": rid, "source": ("collection", rid[len("collection:"):], row.get("title") or ""),
                        "style": POSTER, "season_posters": False})
        elif rid.startswith("playlist:"):
            out.append({"id": rid, "source": ("playlist", rid[len("playlist:"):], row.get("title") or ""),
                        "style": POSTER, "season_posters": False})
    return out


CUSTOM_KEYS = ["library_id", "genre", "language", "label", "decade", "resolution", "unwatched", "added_within",
               "min_runtime", "max_runtime", "min_rating", "sort"]


def custom_row_query(flt, library, limit=24):
    """/items query parameters for a custom row's filter (web/src/lib/home.ts rowQuery)."""
    out = {}
    for k in CUSTOM_KEYS:
        v = _query_value(flt.get(k))
        if v and v != "0":
            out[k] = v
    out["kind"] = "series" if library.get("kind") == "shows" else "movie"
    out["limit"] = str(limit)
    return out


def library_query(library, sort, limit, offset=0, extra=None):
    """/items query parameters for a library's titles in an order."""
    q = {"library_id": str(library.get("id")), "kind": "series" if library.get("kind") == "shows" else "movie",
         "sort": sort, "limit": str(limit), "offset": str(offset)}
    q.update(extra or {})
    return q


def card(item, card_id=None):
    """An item as a card, choosing artwork as the web's PosterCard and EpisodeCard do."""
    img = models.images(item)
    ep = models.is_episode(item)
    return {
        "id": card_id or item.get("id"),
        "item": item,
        "poster": (img.get("series_primary") or img.get("primary")) if ep else img.get("primary"),
        "season_poster": img.get("season_primary") if ep else None,
        "thumb": (img.get("primary") or img.get("series_backdrop") or img.get("backdrop")) if ep
        else (img.get("backdrop") or img.get("primary")),
        "backdrop": (img.get("series_backdrop") or img.get("backdrop_full") or img.get("backdrop") or img.get("primary")) if ep
        else (img.get("backdrop_full") or img.get("backdrop") or img.get("primary")),
        "logo": img.get("series_logo") if ep else img.get("logo"),
        "progress": models.progress(item),
        "season_number": None,
        "new_episodes": 0,
        "show_art": False,
    }


def card_title(item):
    """A card's first line: the show's name for an episode (its number goes on the line under
    it), as Plex and the Android app label them; otherwise the title's own."""
    if models.is_episode(item):
        return (item or {}).get("series_title") or (item or {}).get("title", "")
    return (item or {}).get("title", "")


def recent_card(recent):
    """A TV library's Recently Added card: a new show, new episodes of a season, or one episode."""
    item = recent.get("item") or {}
    c = card(item, "%s:%s:%s:%s" % (recent.get("type"), item.get("id"), recent.get("season_number") or "",
                                    recent.get("added_at") or 0))
    if recent.get("type") == "season":
        c["season_number"] = recent.get("season_number")
        c["new_episodes"] = int(recent.get("episodes") or 0)
        c["season_poster"] = recent.get("season_poster") or c["poster"]
    return c


def with_show_art(c):
    """The same card with the show's own picture in place of the episode's still, so a row of
    shows (Continue Watching) is easy to tell apart; films are unchanged."""
    bg = models.images(c["item"]).get("series_backdrop")
    if not models.is_episode(c["item"]) or not bg:
        return c
    c = dict(c)
    c["thumb"] = bg
    c["show_art"] = True
    return c


def without_spoilers(c):
    """The card of an episode the profile hasn't started, with Hide Spoilers on: its show's
    picture in place of the episode's still (as the web's), or none when the show has none."""
    if models.images(c["item"]).get("series_backdrop"):
        return with_show_art(c)
    c = dict(c)
    c["thumb"] = None
    c["show_art"] = True
    return c


def card_art(c, style, season_posters=False):
    """The picture a card of `style` shows."""
    if style == POSTER:
        return (c.get("season_poster") or c.get("poster")) if season_posters else c.get("poster")
    if style == THUMB:
        return c.get("thumb")
    return c.get("backdrop")
