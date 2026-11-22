from arc.launch import launch_profile


def test_fresh_launch_asks_even_when_a_profile_was_selected():
    a, b = {"id": "a"}, {"id": "b"}
    assert launch_profile({"profile": a, "profiles": [a, b]}) is None


def test_resume_keeps_the_current_profile():
    a, b = {"id": "a", "has_pin": True}, {"id": "b"}
    assert launch_profile({"profile": a, "profiles": [a, b]}, "b", fresh=False) == a


def test_automatic_profile_takes_precedence_over_last_selected():
    a, b = {"id": "a"}, {"id": "b"}
    assert launch_profile({"profile": a, "profiles": [a, b]}, "b") == b


def test_pin_and_deleted_automatic_profiles_return_to_picker():
    a, b = {"id": "a"}, {"id": "b", "has_pin": True}
    assert launch_profile({"profile": b, "profiles": [a, b]}, "b") is None
    assert launch_profile({"profile": a, "profiles": [a]}, "deleted") is None


def test_existing_single_profile_and_friend_shortcuts():
    a = {"id": "a"}
    assert launch_profile({"profile": a, "profiles": [a]}) == a
    assert launch_profile({"profiles": [a]}) is None
    assert launch_profile({"profile": a, "friend": True}) == a
