"""A library grid's sort and filters, as the Apple app's LibraryQuery (ArcKit Browse.swift) and
the web's library page: seven sorts, each reversible, and filters for unwatched titles, a genre,
a decade and (films) a resolution, from GET /libraries/{id}/facets. Plain Python, so the tests
cover it; the Kodi side words and draws the menus."""

# The sorts, in the menu's order: (the value /items takes, its string key for the Kodi side).
SORTS = [("title", "title"), ("added", "added"), ("release", "released"), ("year", "year"),
         ("rating", "rating"), ("runtime", "runtime"), ("watched", "watched")]

# How each sort runs, as the server orders it (internal/store/items.go itemOrdering): Title A to Z,
# the rest newest, highest or longest first; reversed, the other way. (normal, reversed) keys.
DIRECTIONS = {"title": ("a_to_z", "z_to_a"), "added": ("newest", "oldest"), "release": ("newest", "oldest"),
              "year": ("newest", "oldest"), "rating": ("highest", "lowest"), "runtime": ("longest", "shortest"),
              "watched": ("recent", "least_recent")}

RESOLUTIONS = {"4k": "4K", "1080": "1080p", "720": "720p", "sd": "SD"}


class LibraryQuery(object):
    def __init__(self, sort="added"):
        self.sort = sort
        self.reversed = False
        self.unwatched = False
        self.genre = None
        self.decade = None
        self.resolution = None

    def choose_sort(self, sort):
        """Choosing the sort already in use turns it round (Z to A, oldest first), as the Apple app."""
        if sort == self.sort:
            self.reversed = not self.reversed
        else:
            self.sort, self.reversed = sort, False

    def direction(self):
        """The current sort's direction, as a key for the Kodi side to word."""
        pair = DIRECTIONS.get(self.sort, ("", ""))
        return pair[1] if self.reversed else pair[0]

    @property
    def filtered(self):
        return bool(self.unwatched or self.genre or self.decade or self.resolution)

    def clear_filters(self):
        self.unwatched, self.genre, self.decade, self.resolution = False, None, None, None

    def parameters(self, library, offset, limit):
        """The /items parameters for `library`'s grid, `limit` titles from `offset`."""
        p = {"library_id": str(library.get("id")), "kind": "series" if library.get("kind") == "shows" else "movie",
             "sort": self.sort, "offset": str(offset), "limit": str(limit)}
        if self.reversed:
            p["reverse"] = "1"
        if self.unwatched:
            p["unwatched"] = "1"
        for key in ("genre", "decade", "resolution"):
            if getattr(self, key):
                p[key] = getattr(self, key)
        return p

    def filter_name(self):
        """What the Filter pill says: ("all", None), ("filtered", None), or the one filter chosen as
        (kind, value) with kind unwatched, genre, decade or resolution."""
        chosen = [(k, v) for k, v in (("unwatched", self.unwatched or None), ("genre", self.genre),
                                     ("decade", self.decade), ("resolution", self.resolution)) if v]
        if not chosen:
            return "all", None
        if len(chosen) > 1:
            return "filtered", None
        return chosen[0]


def shows_resolution(library):
    """Resolution is offered for films only, as the Apple app (shows mix resolutions per episode)."""
    return library.get("kind") not in ("shows", "videos")


def facet_values(facets, key):
    """A facet's values with their counts, [(value, count)], from GET /libraries/{id}/facets."""
    out = []
    for entry in (facets or {}).get(key) or []:
        if entry.get("value"):
            out.append((str(entry["value"]), int(entry.get("count") or 0)))
    return out


def resolution_name(value):
    return RESOLUTIONS.get(value, value)
