from arc import settings


def test_values_and_defaults():
    assert settings.value({}, "auto_play") is True
    assert settings.value({"auto_play": False}, "auto_play") is False
    assert settings.value({}, "auto_skip") is False
    assert settings.value({"hide_spoilers": True}, "hide_spoilers") is True
    assert settings.value({"subtitle_mode": "always"}, "subtitle_mode") == "always"
    assert settings.value({"subtitle_mode": "odd"}, "subtitle_mode") == ""
    assert settings.value({"audio_language": "fra"}, "audio_language") == "fra"
    assert settings.value({}, "subtitle_language") == ""
    assert settings.value({}, "subtitle_size") == "medium"
    assert settings.value({"subtitle_style": {"color": "yellow", "size": "giant"}}, "subtitle_color") == "yellow"
    assert settings.value({"subtitle_style": {"size": "giant"}}, "subtitle_size") == "medium"
    assert settings.value({"subtitle_style": None}, "subtitle_background") == "box"
    assert settings.value({}, "sign_out") is None


def test_changes():
    assert settings.change({}, "auto_play") == {"auto_play": False}
    assert settings.change({"auto_skip": True}, "auto_skip") == {"auto_skip": False}
    assert settings.change({}, "hide_spoilers") == {"hide_spoilers": True}
    assert settings.change({}, "subtitle_mode", "foreign") == {"subtitle_mode": "foreign"}
    assert settings.change({}, "audio_language", "deu") == {"audio_language": "deu"}
    assert settings.change({}, "subtitle_language", "") == {"subtitle_language": ""}
    # A style field sends the whole style, the others kept.
    assert settings.change({"subtitle_style": {"color": "yellow"}}, "subtitle_size", "large") == {
        "subtitle_style": {"size": "large", "color": "yellow", "background": "box", "position": "bottom"}}
    assert settings.change({}, "subtitle_size", "giant") == {}
    assert settings.change({}, "switch_profile") == {}


def test_layout_has_headings_rows_and_notes():
    entries = settings.layout()
    assert entries[0] == ("heading", "playback")
    assert ("heading", "together") not in entries and "join_code" not in settings.rows()
    assert entries.index(("note", "style_note")) == entries.index(("row", "subtitle_position")) + 1
    rows = settings.rows(together=True)
    assert rows.index("join_code") == rows.index("switch_profile") - 1
    assert rows[-1] == "about"
    for key in rows:
        c = settings.choices(key)
        assert c is None or (len(c) > 1 and settings.value({}, key) in c)
