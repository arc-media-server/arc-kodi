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


PLAN = {
    "method": "direct", "file_id": 7, "source_kbps": 9000,
    "audio_tracks": [{"index": 3, "language": "jpn"}, {"index": 1, "language": "eng"}],
    "subtitle_tracks": [{"id": "s4", "language": "eng"}, {"id": "ext-9", "external": True},
                        {"id": "s5", "language": "fre"}],
}


def test_kodi_audio_index_follows_file_order():
    assert playback.kodi_audio_index(PLAN, 1) == 0
    assert playback.kodi_audio_index(PLAN, 3) == 1
    assert playback.kodi_audio_index(PLAN, 99) is None


def test_kodi_subtitle_index_skips_external():
    assert playback.kodi_subtitle_index(PLAN, "s4") == 0
    assert playback.kodi_subtitle_index(PLAN, "s5") == 1
    assert playback.kodi_subtitle_index(PLAN, "ext-9") is None


def test_subtitle_vtt_path_shifts_for_conversion():
    assert playback.subtitle_vtt_path("i1", "s4", 7) == "/api/items/i1/subtitles/s4/vtt?file=7"
    assert playback.subtitle_vtt_path("i1", "s4", 7, 60000).endswith("&shift_ms=-60000")


def test_quality_options_below_source():
    assert playback.quality_options(PLAN) == [None, 8000, 4000, 3000, 2000, 1500, 720]
    assert playback.quality_options({})[1] == 20000


def test_clamp_seek_and_converted():
    assert playback.clamp_seek(-5, 100000) == 0
    assert playback.clamp_seek(200000, 100000) == 99000
    assert playback.converted({"method": "transcode", "session_id": "s"})
    assert not playback.converted({"method": "direct"})


def test_default_audio_and_retry_with_default():
    preview = {"method": "remux", "audio_stream": 3,
               "audio_tracks": [{"index": 1, "default": True}, {"index": 3}]}
    assert playback.default_audio_index(preview) == 1
    assert playback.needs_default_audio_try(preview) is True
    assert playback.needs_default_audio_try(dict(preview, method="direct")) is False
    assert playback.needs_default_audio_try(dict(preview, audio_stream=1)) is False
    assert playback.default_audio_index({"audio_tracks": [{"index": 4}, {"index": 2}]}) == 2


def test_kodi_caps_delegate_output_handling_and_preserve_source_depth():
    caps = playback.kodi_caps()
    assert "hevc" in caps["video"] and "truehd" in caps["audio"]
    assert caps["max_bit_depth"] == 16  # avoid Arc's browser-oriented H.264 Hi10 restriction
    for key in ("hdr_formats", "dolby_vision_profiles", "video_profiles", "audio_passthrough", "max_audio_channels"):
        assert key not in caps  # unspecified source handling, not an SDR-only declaration
    caps["video"].clear()
    assert "hevc" in playback.kodi_caps()["video"]


def test_kodi_requests_keep_limits_and_choices_during_fallback():
    from arc.api import ArcAPI
    from fake_server import FakeServer

    server = FakeServer({("POST", "items/i1/playback"): (200, {"method": "direct"})})
    api = ArcAPI("http://arc:8099", token="fixture-token", opener=server)
    for height in (720, 1080, 2160):
        caps = playback.kodi_caps(height)
        for method in (None, "direct", "remux"):
            attempt = playback.fallback_caps(caps, method) if method else caps
            body = playback.playback_request(attempt, start_ms=42000, file_id=7,
                                             audio_stream=2, max_kbps=4000)
            api.start_playback("i1", body)
            sent = server.requests[-1]["body"]
            assert sent["caps"]["max_height"] == height
            assert sent["max_kbps"] == 4000 and sent["start_ms"] == 42000
            assert sent["file_id"] == 7 and sent["audio_stream"] == 2
            assert "hdr_formats" not in sent["caps"] and "dolby_vision_profiles" not in sent["caps"]
            if method:
                assert sent["caps"]["failed_method"] == method
                assert sent["caps"]["containers"] == []
            if method == "remux":
                assert sent["caps"]["video"] == []
        assert "mkv" in caps["containers"] and "hevc" in caps["video"]
