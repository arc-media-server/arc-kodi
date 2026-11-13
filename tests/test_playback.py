from arc import playback, models


def test_fallback_caps_narrow_in_order():
    caps = dict(playback.BASE_CAPS)
    once = playback.fallback_caps(caps, "direct")
    assert once["containers"] == [] and once["video"] == caps["video"]
    twice = playback.fallback_caps(caps, "remux")
    assert twice["containers"] == [] and twice["video"] == []


def test_source_position_adds_offset_for_conversion():
    plan = {"method": "transcode", "offset_ms": 60000, "session_id": "s"}
    assert playback.source_position_ms(plan, 30.0) == 90000
    assert playback.player_time_ms(plan, 90000) == 30000
    direct = {"method": "direct"}
    assert playback.source_position_ms(direct, 30.0) == 30000


def test_within_converted_window():
    plan = {"method": "transcode", "session_id": "s", "offset_ms": 60000, "duration_ms": 120000}
    assert playback.within_converted(plan, 90000) is True
    assert playback.within_converted(plan, 200000) is False
    assert playback.within_converted({"method": "direct"}, 999999) is True


def test_same_language():
    assert playback.same_language("en", "eng")
    assert playback.same_language("en-GB", "en")
    assert not playback.same_language("en", "fr")
    assert not playback.same_language("und", "und")


def test_choose_subtitle_prefers_language_non_forced():
    tracks = [{"id": "1", "language": "en", "forced": True},
              {"id": "2", "language": "en", "forced": False},
              {"id": "3", "language": "fr", "forced": False}]
    chosen = playback.choose_subtitle(tracks, preferred="en", audio_language="ja", mode="")
    assert chosen["id"] == "2"


def test_choose_subtitle_foreign_only_when_audio_differs():
    tracks = [{"id": "2", "language": "en", "forced": False}]
    assert playback.choose_subtitle(tracks, "en", "en", "foreign") is None
    assert playback.choose_subtitle(tracks, "en", "ja", "foreign")["id"] == "2"


def test_choose_subtitle_manual_only_forced():
    tracks = [{"id": "f", "language": "ja", "forced": True}, {"id": "n", "language": "en", "forced": False}]
    chosen = playback.choose_subtitle(tracks, "en", "ja", "manual")
    assert chosen["id"] == "f"


def test_remembered_subtitle_language():
    assert playback.remembered_subtitle_language({"language": "fr", "forced": False}, "") == "fr"
    assert playback.remembered_subtitle_language(None, "") == ""
    assert playback.remembered_subtitle_language(None, "always") is None
    assert playback.remembered_subtitle_language({"language": "fr", "forced": True}, "") is None


def test_markers_and_up_next():
    markers = [{"kind": "intro", "start_ms": 1000, "end_ms": 30000},
               {"kind": "credits", "start_ms": 600000, "end_ms": 660000}]
    assert playback.active_marker(markers, 5000)["kind"] == "intro"
    assert playback.active_marker(markers, 100000) is None
    assert playback.shows_up_next(markers, 600001, 660000) is True
    assert playback.shows_up_next([], 100000, 660000) is False
    assert playback.shows_up_next([], 650000, 660000) is True  # last 30s


def test_quality_badges():
    item = {"files": [{"streams": [
        {"kind": "video", "codec": "hevc", "width": 3840, "height": 2160, "dolby_vision": True},
        {"kind": "audio", "codec": "eac3", "channels": 6, "profile": "Dolby Atmos"}]}]}
    badges = models.quality_badges(item)
    assert "4K" in badges and "DV" in badges and "Atmos" in badges and "5.1" in badges


def test_runtime_and_clock():
    assert models.runtime_text(92 * 60000) == "1h 32m"
    assert models.runtime_text(45 * 60000) == "45m"
    assert models.clock(3723000) == "1:02:03"
    assert models.clock(123000) == "2:03"
