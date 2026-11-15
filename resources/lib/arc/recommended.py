"""A library's Recommended rows (GET /libraries/{id}/recommended), as the Apple app's ArcKit
Recommended.swift and the web's recommendedTitle: each row titled from its type in the viewer's
language (Arc's own English title for a type the app doesn't know yet), and its card style.
Plain Python; the Kodi side words the string keys."""

from . import home

# A row type -> its string key; shows libraries say Shows and Episodes where films say Movies.
KEYS = {
    "continue": "continue", "recently_released": "recently_released", "recently_added": "recently_added",
    "start_watching": "start_watching", "because_you_watched": "because_you_watched",
    "rediscover": "rediscover", "more_in_genre": "more_in_genre", "top_unwatched": "top_unwatched",
}


def title(row, library_name="", library_kind=""):
    """(key, name) for the Kodi side to word, or (None, Arc's title) for a type new to this app."""
    shows = library_kind == "shows"
    kind = row.get("type") or ""
    name = row.get("name") or ""
    if kind == "recently_added":
        return "recently_added", name or library_name
    if kind == "top_rated":
        return ("top_rated_shows" if shows else "top_rated_movies"), None
    if kind == "recently_watched":
        return ("recently_watched_episodes" if shows else "recently_watched"), None
    if kind == "top_in_genre":
        return ("top_shows_in_genre" if shows else "top_movies_in_genre"), name
    if kind == "top_by_person":
        by = row.get("role") == "director"
        return ("top_shows_" if shows else "top_movies_") + ("by" if by else "with"), name
    if kind in KEYS:
        return KEYS[kind], (name if kind in ("because_you_watched", "more_in_genre") else None)
    return None, row.get("title") or ""


def style(row, library_kind=""):
    """The shared layout's look, else posters, with wide pictures for what's in progress and for a
    shows library's recently watched episodes."""
    saved = home.card_style(row.get("style"))
    if saved:
        return saved
    kind = row.get("type")
    if kind == "continue" or (kind == "recently_watched" and library_kind == "shows"):
        return home.THUMB
    return home.POSTER


def rows(page, library):
    """The page's rows with cards, as Home's row dicts (id, source, style, title key, cards)."""
    out = []
    for row in (page or {}).get("rows") or []:
        items = row.get("items") or []
        if not items:
            continue
        key, name = title(row, library.get("name", ""), library.get("kind", ""))
        look = style(row, library.get("kind", ""))
        cards = [home.card(it) for it in items]
        if row.get("type") == "continue":
            cards = [home.with_show_art(c) for c in cards]
        out.append({"id": row.get("id"), "source": ("recommended", row.get("type") or ""), "style": look,
                    "season_posters": False, "title": (key, name), "cards": cards})
    return out
