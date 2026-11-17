"""A library grid's sort and filters, as the Apple app's LibraryQuery (ArcKit Browse.swift) and
the web's library page: seven sorts, each reversible, and filters for unwatched titles, a watch
status, a genre, a decade, (films) a resolution, and what the files are (HDR, video and audio
format, audio channels), from GET /libraries/{id}/facets. Plain Python, so the tests cover it; the
Kodi side words and draws the menus."""

# The sorts, in the menu's order: (the value /items takes, its string key for the Kodi side).
SORTS = [("title", "title"), ("added", "added"), ("release", "released"), ("year", "year"),
         ("rating", "rating"), ("runtime", "runtime"), ("watched", "watched")]

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
    def __init__(self, sort="added"):
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
        return bool(self.unwatched or any(getattr(self, k) for k in _FILTERS))

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

    def parameters(self, library, offset, limit):
        """The /items parameters for `library`'s grid, `limit` titles from `offset`."""
        p = {"library_id": str(library.get("id")), "kind": "series" if library.get("kind") == "shows" else "movie",
             "sort": self.sort, "offset": str(offset), "limit": str(limit)}
        if self.reversed:
            p["reverse"] = "1"
        if self.unwatched:
            p["unwatched"] = "1"
        for key in _FILTERS:
            if getattr(self, key):
                p[key] = str(getattr(self, key))
        return p

    def filter_name(self):
        """What the Filter pill says: ("all", None), ("filtered", None), or the one filter chosen as
        (kind, value) with kind unwatched or one of the filters' attributes (genre, decade,
        resolution, watch_state, dynamic_range, video_codec, audio_codec, audio_channels)."""
        chosen = [("unwatched", True)] if self.unwatched else []
        chosen += [(k, getattr(self, k)) for k in _FILTERS if getattr(self, k)]
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
