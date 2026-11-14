"""The player's choices, as the web and Apple players make them (web/src/lib/playback.ts): the
caps Kodi can play, which subtitles turn on, the marker on screen, when Up Next shows, and the
clock for a converted stream. Plain Python, so the tests cover it without Kodi.
"""

# Source formats delegated to Kodi's player, including its software decoders and local
# conversion paths. This is a playback policy, not a claim about hardware or native output.
# Kodi settings own HDR/Dolby Vision handling, tone mapping and audio output.
BASE_CAPS = {
    "containers": ["mp4", "mkv", "webm"],
    "video": ["h264", "hevc", "vp9", "av1", "mpeg2video", "mpeg4", "vc1"],
    "audio": ["aac", "mp3", "ac3", "eac3", "flac", "opus", "vorbis", "truehd", "dts", "pcm"],
}


def kodi_caps(max_height=2160):
    """Prefer original sources and let Kodi handle format compatibility.

    Omit HDR/profile/output restrictions: Arc treats omission as unspecified, while [] for
    hdr_formats explicitly means SDR only. Kodi may handle a source through local conversion.
    16 is Arc's accepted source bit-depth ceiling; it also avoids its legacy 8-bit H.264 default.
    The chosen resolution and server/profile/quality limits still apply.
    """
    caps = {key: list(values) for key, values in BASE_CAPS.items()}
    caps.update(max_height=max_height, max_bit_depth=16)
    return caps


def playback_request(caps, start_ms=0, file_id=None, audio_stream=None, max_kbps=None, burn_subtitle=None):
    body = {"caps": caps, "start_ms": int(max(0, start_ms))}
    if file_id is not None:
        body["file_id"] = file_id
    if audio_stream is not None:
        body["audio_stream"] = audio_stream
    if max_kbps:
        body["max_kbps"] = max_kbps
    if burn_subtitle:
        body["burn_subtitle"] = burn_subtitle
    return body


def fallback_caps(caps, failed_method):
    """Caps for trying again after Kodi failed (web/src/lib/playback.ts): a file played as it is
    failed, so have it repackaged; repackaged failed, so have the video converted too."""
    out = dict(caps)
    out["containers"] = []
    if failed_method != "direct":
        out["video"] = []
    out["failed_method"] = failed_method
    return out


def source_position_ms(plan, player_time_s):
    """Progress always uses the source file's timeline. For a converted stream Arc's offset is
    added to the player's own clock; a direct file is already in source time."""
    return int((plan.get("offset_ms") or 0) + player_time_s * 1000)


def player_time_ms(plan, source_ms):
    """The reverse: where the player should seek to for a source position within this plan."""
    return int(source_ms - (plan.get("offset_ms") or 0))


def within_converted(plan, source_ms):
    """Whether a source position is inside what this converted plan can already play. Seeking
    outside it needs a new playback request at that start_ms (and a fresh offset)."""
    if plan.get("method") == "direct" or not plan.get("session_id"):
        return True
    offset = plan.get("offset_ms") or 0
    duration = plan.get("duration_ms") or 0
    return offset <= source_ms <= (offset + duration if duration else offset)


_ALPHA3 = {
    "eng": "en", "fre": "fr", "fra": "fr", "ger": "de", "deu": "de", "spa": "es", "ita": "it", "por": "pt",
    "dut": "nl", "nld": "nl", "swe": "sv", "nor": "no", "nob": "no", "dan": "da", "fin": "fi", "pol": "pl",
    "rus": "ru", "jpn": "ja", "kor": "ko", "chi": "zh", "zho": "zh", "ara": "ar", "heb": "he", "hin": "hi",
    "tur": "tr", "gre": "el", "ell": "el", "cze": "cs", "ces": "cs", "hun": "hu", "rum": "ro", "ron": "ro",
    "ukr": "uk", "tha": "th", "vie": "vi", "ind": "id", "may": "ms", "msa": "ms", "bul": "bg", "hrv": "hr",
    "srp": "sr", "slv": "sl", "slo": "sk", "slk": "sk", "ice": "is", "isl": "is", "cat": "ca", "baq": "eu",
    "eus": "eu", "glg": "gl", "per": "fa", "fas": "fa", "est": "et", "lav": "lv", "lit": "lt", "wel": "cy",
    "cym": "cy", "gle": "ga", "tam": "ta", "tel": "te", "ben": "bn", "urd": "ur", "fil": "tl", "tgl": "tl",
}


def _base_language(code):
    c = (code or "").lower().strip()
    if not c or c == "und":
        return None
    for sep in ("-", "_"):
        if sep in c:
            c = c.split(sep)[0]
    return _ALPHA3.get(c, c)


def same_language(a, b):
    """Whether two language codes name the same language ("en", "eng" and "en-GB" do)."""
    ba, bb = _base_language(a), _base_language(b)
    return ba is not None and ba == bb


def choose_subtitle(tracks, preferred, audio_language, mode):
    """The subtitles that turn on by themselves, as Plex's modes (web/src/lib/playback.ts): "manual"
    only forced ones, "foreign" the profile's language when the audio is in another, "always" its
    language whenever there is one, "" (the default) the language last chosen."""
    if mode == "manual":
        wanted = False
    elif mode == "foreign":
        wanted = bool(preferred) and audio_language is not None and not same_language(audio_language, preferred)
    else:
        wanted = True
    if preferred and wanted:
        matching = [t for t in tracks if same_language(t.get("language"), preferred)]
        best = (next((t for t in matching if not t.get("forced") and not t.get("hearing_impaired") and not t.get("image")), None)
                or next((t for t in matching if not t.get("forced")), None)
                or (matching[0] if matching else None))
        if best:
            return best
    return next((t for t in tracks if t.get("forced") and
                 (t.get("language") is None or audio_language is None or same_language(t.get("language"), audio_language))), None)


def remembered_subtitle_language(track, mode):
    """What a choice in the player saves as the profile's subtitle language: a track's language, or
    "" for Off in the default mode; None when nothing should change."""
    if track and not track.get("forced"):
        return track.get("language") or ""
    if track is None and not mode:
        return ""
    return None


def active_marker(markers, ms):
    """The intro, recap or credits marker playing at `ms`, if any."""
    for m in markers or []:
        if m.get("kind") in ("intro", "recap", "credits") and (m.get("start_ms") or 0) <= ms < (m.get("end_ms") or 0) - 1000:
            return m
    return None


def shows_up_next(markers, position_ms, duration_ms):
    """When the Up Next card shows: at the credits, else in the last 30 seconds."""
    if duration_ms <= 0:
        return False
    credits = next((m for m in markers or [] if m.get("kind") == "credits"), None)
    if credits:
        return position_ms >= (credits.get("start_ms") or 0)
    return position_ms >= duration_ms - 30000


# MARK: - tracks and choices in the player (Kodi's own player plays; Arc names the tracks)

def audio_tracks(plan):
    """The plan's audio tracks in file order (by stream index), as Kodi lists them."""
    return sorted(plan.get("audio_tracks") or [], key=lambda t: t.get("index", 0))


def kodi_audio_index(plan, arc_index):
    """Kodi's number for an Arc audio track in a file played as it is: its place among the
    file's audio tracks. None when Arc doesn't list it."""
    for i, t in enumerate(audio_tracks(plan)):
        if t.get("index") == arc_index:
            return i
    return None


def kodi_subtitle_index(plan, track_id):
    """Kodi's number for a subtitle track inside a file played as it is: its place among the
    file's own (not external) tracks, which Kodi lists first. None for external tracks, which
    Kodi only gets when the add-on gives it the file."""
    inside = [t for t in plan.get("subtitle_tracks") or [] if not t.get("external")]
    for i, t in enumerate(inside):
        if t.get("id") == track_id:
            return i
    return None


def converted(plan):
    return bool(plan.get("session_id")) or plan.get("method") not in (None, "direct")


def subtitle_vtt_path(item_id, track_id, file_id, offset_ms=0):
    """Arc's WebVTT link for a text subtitle track (GET /items/{id}/subtitles/{track}/vtt), on the
    stream's own clock: a converted stream starts at offset_ms, so the cues move back by it.
    Unversioned /api/ as Arc's cast links expect."""
    path = "/api/items/%s/subtitles/%s/vtt?file=%s" % (item_id, track_id, file_id)
    if offset_ms:
        path += "&shift_ms=%d" % -int(offset_ms)
    return path


QUALITY_STEPS = [20000, 12000, 8000, 4000, 3000, 2000, 1500, 720]


def quality_options(plan):
    """The qualities worth offering (kbit/s), best first, after the original (None): only below
    the file's own bitrate, as the web and Android players offer them."""
    source = int(plan.get("source_kbps") or 0)
    return [None] + [q for q in QUALITY_STEPS if not source or q < source]


def clamp_seek(ms, duration_ms):
    """A seek target inside the title: not before the start, not in the last second."""
    if duration_ms > 0:
        ms = min(ms, duration_ms - 1000)
    return max(0, int(ms))


def default_audio_index(plan):
    """The file's default audio track (the one a player picks by itself): marked default, else
    the first. None when there's no audio."""
    tracks = audio_tracks(plan)
    for t in tracks:
        if t.get("default"):
            return t.get("index")
    return tracks[0].get("index") if tracks else None


def needs_default_audio_try(preview):
    """Arc converts whenever the profile's audio language picks a track other than the file's
    default, as a browser can't switch tracks. Kodi can: when that's the only reason, the file
    can be played as it is with the default track and Kodi switched to the preferred one.
    True when a preview with the default track is worth asking for."""
    if not preview or preview.get("method") == "direct":
        return False
    preferred, default = preview.get("audio_stream"), default_audio_index(preview)
    return default is not None and preferred is not None and preferred >= 0 and preferred != default


# MARK: - chapters

def chapters(plan):
    """The plan's chapters in order, each with a start (ms); ones without a start are left out."""
    out = [c for c in (plan or {}).get("chapters") or [] if c.get("start_ms") is not None]
    return sorted(out, key=lambda c: c.get("start_ms") or 0)


def chapter_at(chaps, position_ms):
    """The index of the chapter playing at `position_ms`, or -1 before the first."""
    at = -1
    for i, c in enumerate(chaps):
        if (c.get("start_ms") or 0) <= position_ms:
            at = i
    return at


def chapter_marks(chaps, duration_ms, limit=40):
    """Where to mark chapters on the timeline, as fractions of the length: every chapter but one
    starting at the very beginning (there's nothing to mark there), at most `limit` of them."""
    if duration_ms <= 0:
        return []
    marks = [float(c.get("start_ms") or 0) / duration_ms for c in chaps if (c.get("start_ms") or 0) > 1000]
    return [m for m in marks if 0 < m < 1][:limit]


# MARK: - speed

# The speeds offered, as Kodi's tempo steps them (0.1 at a time, 0.8x to 1.5x).
SPEEDS = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]


def speed_steps(current, target):
    """How many tempo steps (positive up, negative down) take `current` to `target`."""
    return int(round((target - current) * 10))
