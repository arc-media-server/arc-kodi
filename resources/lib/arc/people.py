"""A person's page (GET /people/{id}), as the Apple app's PersonView: rows of the Movies and TV
Shows they act in, then what they made behind the camera, newest first; a summary line; and
their part in a title. Plain Python; the Kodi side words the keys."""


def _date(item):
    return item.get("release_date") or (str(item["year"]) if item.get("year") else "")


def _acting(credit):
    roles = credit.get("roles") or []
    return not roles or "actor" in roles


def rows(page):
    """[(key, [credit, ...])] with key movies, shows or crew; empty rows left out."""
    credits = sorted((page or {}).get("credits") or [], key=lambda c: _date(c.get("item") or {}), reverse=True)

    def unique(cs):
        seen, out = set(), []
        for c in cs:
            item_id = (c.get("item") or {}).get("id")
            if item_id and item_id not in seen:
                seen.add(item_id)
                out.append(c)
        return out

    movies = unique([c for c in credits if _acting(c) and (c.get("item") or {}).get("kind") == "movie"])
    shows = unique([c for c in credits if _acting(c) and (c.get("item") or {}).get("kind") != "movie"])
    crew = unique([c for c in credits if not _acting(c)])
    return [(key, cs) for key, cs in (("movies", movies), ("shows", shows), ("crew", crew)) if cs]


def title_count(page):
    """How many of their titles are in the libraries (each title once)."""
    return len({(c.get("item") or {}).get("id") for c in (page or {}).get("credits") or [] if (c.get("item") or {}).get("id")})


def part(credit):
    """(title with year, character or None, the first role behind the camera or None) for
    "Heat (1995) · as Lt. Vincent Hanna" or "Inception (2010) · Director"."""
    item = credit.get("item") or {}
    title = item.get("title", "")
    if item.get("year"):
        title += " (%s)" % item["year"]
    character = credit.get("character") or None
    role = None
    if not character:
        role = next((r for r in credit.get("roles") or [] if r != "actor"), None)
    return title, character, role
