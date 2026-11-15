from arc import settings


def test_values_and_defaults():
    assert settings.value({}, "auto_play") is True
    assert settings.value({"auto_play": False}, "auto_play") is False
    assert settings.value({}, "auto_skip") is False
    assert settings.value({"subtitle_mode": "always"}, "subtitle_mode") == "always"
    assert settings.value({"subtitle_mode": "odd"}, "subtitle_mode") == ""
    assert settings.value({}, "sign_out") is None


def test_changes():
    assert settings.change({}, "auto_play") == {"auto_play": False}
    assert settings.change({"auto_skip": True}, "auto_skip") == {"auto_skip": False}
    assert settings.change({}, "subtitle_mode", "foreign") == {"subtitle_mode": "foreign"}
    assert settings.change({}, "switch_profile") == {}


def test_rows_offer_join_code_with_watch_together():
    assert "join_code" not in settings.rows()
    assert settings.rows(together=True).index("join_code") == settings.rows(together=True).index("switch_profile") - 1
