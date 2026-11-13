"""The player's choices, as the web and Apple players make them (web/src/lib/playback.ts): the
caps Kodi can play, which subtitles turn on, the marker on screen, when Up Next shows, and the
clock for a converted stream. Plain Python, so the tests cover it without Kodi.
"""

# Containers, video and audio codecs Kodi plays directly on the common platforms. Kodi's own
# player handles far more than a browser; Arc only repackages or converts what's left. The real
# device caps (passthrough, HDR, refresh rates) come from kodi/caps.py at runtime.
BASE_CAPS = {
    "containers": ["mp4", "mkv", "webm"],
    "video": ["h264", "hevc", "vp9", "av1", "mpeg2video", "mpeg4", "vc1"],
    "audio": ["aac", "mp3", "ac3", "eac3", "flac", "opus", "vorbis", "truehd", "dts", "pcm"],
}


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
