"""A library grid's sort and filters, as the Apple app's LibraryQuery (ArcKit Browse.swift) and
the web's library page: seven sorts, each reversible, and filters for unwatched titles, a watch
status, a genre, a decade, (films) a resolution, and what the files are (HDR, video and audio
format, audio channels), from GET /libraries/{id}/facets. Plain Python, so the tests cover it; the
Kodi side words and draws the menus."""

# The sorts, in the menu's order: (the value /items takes, its string key for the Kodi side).
# Shuffle is Arc's daily shuffle (the same order all day), with no direction, as the Android app's.
SORTS = [("title", "title"), ("added", "added"), ("release", "released"), ("year", "year"),
         ("rating", "rating"), ("runtime", "runtime"), ("watched", "watched"), ("shuffle", "shuffle")]

# How each sort runs, as the server orders it (internal/store/items.go itemOrdering): Title A to Z,
# the rest newest, highest or longest first; reversed, the other way. (normal, reversed) keys.
DIRECTIONS = {"title": ("a_to_z", "z_to_a"), "added": ("newest", "oldest"), "release": ("newest", "oldest"),
              "year": ("newest", "oldest"), "rating": ("highest", "lowest"), "runtime": ("longest", "shortest"),
              "watched": ("recent", "least_recent")}

RESOLUTIONS = {"4k": "4K", "1080": "1080p", "720": "720p", "sd": "SD"}

# Names for what the files are, as Arc's web and the other TV apps write them. "unknown" (HDR not
# known yet) is worded on the Kodi side.
DYNAMIC_RANGES = {"dolby_vision": "Dolby Vision", "hdr10_plus": "HDR10+", "hlg": "HLG", "hdr10": "HDR10", "sdr": "SDR"}
VIDEO_CODECS = {"h264": "H.264", "hevc": "HEVC", "av1": "AV1", "vp9": "VP9", "mpeg2video": "MPEG-2",
                "mpeg4": "MPEG-4", "vc1": "VC-1"}
AUDIO_CODECS = {"aac": "AAC", "ac3": "Dolby Digital", "eac3": "Dolby Digital Plus", "truehd": "Dolby TrueHD",
                "dts": "DTS", "flac": "FLAC", "mp3": "MP3", "opus": "Opus", "vorbis": "Vorbis", "alac": "ALAC"}

# The filters that narrow by what the files are: (the query's attribute and /items parameter, the
# facets' key). Offered only when they'd narrow something (`offered`).
MEDIA_FILTERS = [("dynamic_range", "dynamic_ranges"), ("video_codec", "video_codecs"),
                 ("audio_codec", "audio_codecs"), ("audio_channels", "audio_channels")]

# Watch Status's choices: /items' watch_state values.
WATCH_STATES = ["played", "unstarted"]

_FILTERS = ("genre", "decade", "resolution", "watch_state") + tuple(k for k, _ in MEDIA_FILTERS)


class LibraryQuery(object):
    # Title first, as the Android app's library (and Plex's).
    def __init__(self, sort="title"):
        self.sort = sort
        self.reversed = False
        self.unwatched = False
        self.genre = None
        self.decade = None
        self.resolution = None
        # played or unstarted. It and unwatched only exclude each other, as Arc requires.
        self.watch_state = None
        self.dynamic_range = None
        self.video_codec = None
        self.audio_codec = None
        self.audio_channels = None

    def choose_sort(self, sort):
        """Choosing the sort already in use turns it round (Z to A, oldest first), as the Apple app.
        Shuffle has no other way round."""
        if sort == self.sort and sort != "shuffle":
            self.reversed = not self.reversed
        else:
            self.sort, self.reversed = sort, False

    def direction(self):
        """The current sort's direction, as a key for the Kodi side to word."""
        pair = DIRECTIONS.get(self.sort, ("", ""))
        return pair[1] if self.reversed else pair[0]

    @property
    def filtered(self):
        return bool(self.unwatched or any(getattr(self, k) for k in _FILTERS))

    @property
    def filter_count(self):
        """How many filters are on, for the Filters pill ("Filters, 2 on")."""
        return int(bool(self.unwatched)) + sum(1 for k in _FILTERS if getattr(self, k))

    def clear_filters(self):
        self.unwatched = False
        for key in _FILTERS:
            setattr(self, key, None)

    def set_unwatched(self, on):
        """Unwatched only on or off; turning it on clears a watch status."""
        self.unwatched = bool(on)
        if on:
            self.watch_state = None

    def set_watch_state(self, state):
        """A watch status, or None; choosing one turns Unwatched only off."""
        self.watch_state = state or None
        if state:
            self.unwatched = False

    @property
    def shows_letters(self):
        """The A–Z bar is offered with the title sort only, as on the web, Android and Apple."""
        return self.sort == "title"

    def parameters(self, library, offset, limit, letters=False):
        """The /items parameters for `library`'s grid, `limit` titles from `offset`. `letters` asks
        for the A–Z bar's counts too (only sorted by title, where letters mean something)."""
        p = {"library_id": str(library.get("id")), "kind": "series" if library.get("kind") == "shows" else "movie",
             "sort": self.sort, "offset": str(offset), "limit": str(limit)}
        if letters and self.shows_letters:
            p["letters"] = "1"
        if self.reversed and self.sort != "shuffle":
            p["reverse"] = "1"
        if self.unwatched:
            p["unwatched"] = "1"
        for key in _FILTERS:
            if getattr(self, key):
                p[key] = str(getattr(self, key))
        return p



def letter_jumps(letters, reversed_=False):
    """Where each letter's first title is in a title-sorted list (GET /items with letters=1), in
    the list's own order (Z to A when reversed), as the web's, Android's and Apple's: a list of
    (letter as shown, offset). "a" to "z" show as capitals, anything else as "#". Letters with no
    titles are left out, and a "#" that comes twice (digits before A, other scripts after Z)
    keeps its first place."""
    out, seen, at = [], set(), 0
    for entry in reversed(letters or []) if reversed_ else (letters or []):
        letter = str(entry.get("letter") or "")
        count = int(entry.get("count") or 0)
        shown = letter.upper() if len(letter) == 1 and "a" <= letter.lower() <= "z" else "#"
        if count > 0 and shown not in seen:
            seen.add(shown)
            out.append((shown, at))
        at += count
    return out


def pages_to_reach(target, have, total, page, max_limit=500):
    """The requests that load a grid from the `have` titles it holds through `target` and a page
    past it, so a jump to a letter lands on a full screen of titles: (offset, limit) pairs, at
    most `max_limit` each (/items takes up to 500)."""
    end = min(total, target + page)
    out, at = [], have
    while at < end:
        limit = min(max_limit, end - at)
        out.append((at, limit))
        at += limit
    return out


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


def offered(facets, key, chosen):
    """A media filter is offered when the library has more than one value, or one is already chosen
    (the web's rule): a library that's all HEVC has no Video Format row."""
    return len(facet_values(facets, key)) > 1 or chosen is not None


def choices(facets, key, chosen):
    """A filter's values for its list, with the chosen one kept even if the library no longer has
    it, so it can be seen and changed. Audio channels come as numbers, most first (7.1, 5.1, 2)."""
    values = [v for v, _ in facet_values(facets, key)]
    if key == "audio_channels":
        values = sorted({int(v) for v in values if v.isdigit() and int(v) > 0}, reverse=True)
    if chosen is not None and chosen not in values:
        values.append(chosen)
    return values


def resolution_name(value):
    return RESOLUTIONS.get(value, value)


def dynamic_range_name(value):
    return DYNAMIC_RANGES.get(value, value)


def video_codec_name(value):
    return VIDEO_CODECS.get(value, (value or "").upper())


def audio_codec_name(value):
    return AUDIO_CODECS.get(value, (value or "").upper())


# The Watchlist's pills, as the Android and Apple TV apps': what it shows, and in which order.
# Date Added is Arc's own order (newest first); the others sort here.
WATCHLIST_SHOWS = ["all", "movies", "shows"]
WATCHLIST_SORTS = ["added", "title", "released"]


def sort_title(item):
    """A title as libraries sort it: lower case, without a leading "The", "A" or "An"."""
    title = (item.get("sort_title") or item.get("title") or "").lower()
    for word in ("the ", "a ", "an "):
        if title.startswith(word):
            return title[len(word):]
    return title


def watchlist_view(items, show="all", sort="added"):
    """The Watchlist's titles for its two pills: all, movies or shows; by date added (as Arc sends
    them), title, or release date (newest first, then by title)."""
    if show == "movies":
        items = [it for it in items if it.get("kind") == "movie"]
    elif show == "shows":
        items = [it for it in items if it.get("kind") == "series"]
    else:
        items = list(items)
    if sort == "title":
        return sorted(items, key=sort_title)
    if sort == "released":
        items = sorted(items, key=sort_title)
        return sorted(items, key=lambda it: it.get("release_date") or (str(it["year"]) if it.get("year") else ""),
                      reverse=True)
    return items
