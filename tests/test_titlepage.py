from arc import titlepage


def test_toned_keeps_hue_and_darkens():
    out = titlepage.toned("#ff0000")
    assert out.startswith("FF") and len(out) == 8
    r, g, b = (int(out[i:i + 2], 16) for i in (2, 4, 6))
    assert r > g and r > b and r <= 77  # brightness capped at 0.30
    assert titlepage.toned("nope") is None


def test_palette_corners():
    pal = {"available": True, "colors": {"top_left": "#112233", "top_right": "#445566",
                                         "bottom_left": "#778899", "bottom_right": "#aabbcc"}}
    assert len(titlepage.palette_corners(pal)) == 4
    assert titlepage.palette_corners({"available": False}) is None


def ep(id, n, watched=False, pos=0, available=True):
    return {"id": id, "kind": "episode", "episode_number": n, "available": available,
            "user_data": {"played": watched, "position_ms": pos}}


def test_next_to_play_prefers_in_progress_then_unwatched():
    seasons = [{"season_number": 0, "episodes": [ep("s0", 1)]},
               {"season_number": 1, "episodes": [ep("a", 1, True), ep("b", 2), ep("c", 3, pos=90000)]}]
    assert titlepage.next_to_play(seasons)["id"] == "c"
    seasons[1]["episodes"][2]["user_data"]["position_ms"] = 0
    assert titlepage.next_to_play(seasons)["id"] == "b"
    all_watched = [{"season_number": 1, "episodes": [ep("a", 1, True)]}]
    assert titlepage.next_to_play(all_watched)["id"] == "a"
    assert titlepage.next_to_play([{"season_number": 1, "episodes": [ep("x", 1, available=False)]}]) is None


def test_play_action():
    movie = {"id": "m", "kind": "movie", "user_data": {"position_ms": 120000}}
    assert titlepage.play_action(movie) == ("resume", movie, 120000)
    show = {"id": "s", "kind": "series"}
    e = ep("e", 1)
    assert titlepage.play_action(show, e) == ("play", e, 0)
    assert titlepage.play_action(show, None) is None


def test_cards():
    item = {"release_date": "2010-07-16", "runtime_min": 148, "content_rating": "PG-13",
            "genres": ["Action", "Sci-Fi"], "studio": "Legendary",
            "credits": [{"name": "C. Nolan", "role": "director"}, {"name": "C. Nolan", "role": "writer"},
                        {"name": "Leo", "role": "actor"}],
            "files": [{"id": 1, "size": 5 * 1024 ** 3, "bitrate": 12000000, "path": "/m/Inception.mkv",
                       "streams": [{"kind": "video", "height": 2160, "width": 3840}]}]}
    assert ("runtime", "2h 28m") in titlepage.details_lines(item)
    assert titlepage.crew_lines(item)[0] == ("directed", "C. Nolan")
    lines = dict(titlepage.playback_lines(item, "Home Arc", True, "Jon"))
    assert lines["connection"] == "home" and lines["size"] == "5.0 GB" and lines["file"] == "Inception.mkv"
    assert titlepage.starring(item) == ["Leo"]


def test_starring_wraps_as_seen_in_kodi():
    # Lines seen in Kodi at 620 px: these wrapped...
    for names in ("Ryan Gosling, Harrison Ford, Ana de Armas", "Leonardo DiCaprio, Joseph Gordon-Levitt, Ken Watanabe",
                  "Yumi Uchiyama, Tomokazu Sugita, Ai Kakuma", "Dan Castellaneta, Julie Kavner, Nancy Cartwright"):
        assert titlepage.wraps("Starring", names), names
    # ...and these fitted.
    for names in ("Harrison Ford, Rutger Hauer, Sean Young", "Nathan Fillion, Gina Torres, Alan Tudyk"):
        assert not titlepage.wraps("Starring", names), names


def test_season_tabs_add_episodes_outside_the_order():
    data = {"seasons": [{"season_number": 1, "episodes": [{"id": "e1", "episode_number": 1, "title": "One"}]}],
            "unplaced": [{"id": "x2", "episode_number": 12, "season_number": 1, "title": "Twelve"}, {"title": "no id"}]}
    seasons, tabs = titlepage.season_tabs(data)
    assert [s["season_number"] for s in seasons] == [1]
    assert len(tabs) == 2 and tabs[1]["unplaced"] and [e["id"] for e in tabs[1]["episodes"]] == ["x2"]
    # Play follows the order: an unwatched episode outside it isn't picked.
    assert titlepage.next_to_play(seasons)["id"] == "e1"
    assert titlepage.season_tabs({"seasons": [], "unplaced": None}) == ([], [])
    assert titlepage.season_tabs(None) == ([], [])


def test_episode_label():
    assert titlepage.episode_label({"episode_number": 4, "title": "Ariel"}) == "4. Ariel"
    assert titlepage.episode_label({"episode_number": 12, "title": "Trash"}, unplaced=True) == "Trash"
    assert titlepage.episode_label({"title": "Pilot"}) == "Pilot"


def test_unplaced_episodes_have_no_code():
    from arc import models
    assert models.episode_code({"season_number": 0, "episode_number": 0}) == ""
    assert models.episode_code({"season_number": 0, "episode_number": 3}) == "S0 · E3"   # a special
    assert models.episode_code({"season_number": 2, "episode_number": 4}) == "S2 · E4"
    assert not models.placed({"season_number": 0, "episode_number": 0})
    assert titlepage.episode_label({"season_number": 0, "episode_number": 0, "title": "Trash"}) == "Trash"


def test_season_actions():
    from arc import models
    unwatched = {"season_number": 1, "episodes": [
        {"id": "a", "user_data": {"played": True}}, {"id": "b", "user_data": {"position_ms": 5000}},
        {"id": "c", "available": False}]}
    assert titlepage.season_actions(unwatched) == ["watched", "shuffle"]
    assert titlepage.season_episode_ids(unwatched) == ["a", "b"]
    marked = titlepage.mark_season(unwatched, True)
    assert [models.watched(e) for e in marked[:2]] == [True, True]
    assert marked[1]["user_data"]["position_ms"] == 0
    assert "user_data" not in marked[2]            # not on disk: left as it is
    assert unwatched["episodes"][1]["user_data"]["position_ms"] == 5000   # the original isn't changed
    assert titlepage.season_actions(dict(unwatched, episodes=marked)) == ["unwatched", "shuffle"]
    one = {"season_number": 2, "episodes": [{"id": "x"}]}
    assert titlepage.season_actions(one) == ["watched"]
    assert titlepage.season_actions({"unplaced": True, "episodes": [{"id": "u"}, {"id": "v"}]}) == []
    assert titlepage.season_actions({"season_number": 3, "episodes": [{"id": "z", "available": False}]}) == []
    assert titlepage.season_actions(None) == []


def test_versions():
    from arc import menus, models
    uhd = {"id": 1, "size": 60 * 1024 ** 3, "streams": [
        {"kind": "video", "height": 2160, "width": 3840, "color_transfer": "smpte2084", "dolby_vision": True},
        {"kind": "audio", "codec": "truehd", "profile": "TrueHD Atmos", "channels": 8}]}
    hd = {"id": 2, "edition": "Director's Cut", "streams": [{"kind": "video", "height": 1080, "width": 1920}]}
    gone = {"id": 3, "missing": True}
    part2 = {"id": 4, "part": 2}
    film = {"id": "m", "kind": "movie", "files": [uhd, hd, gone, part2]}
    assert [f["id"] for f in models.versions(film)] == [1, 2]
    assert titlepage.version_label(uhd) == ("4K", "DV · HDR10 · Atmos · 7.1 · 60.0 GB")
    assert titlepage.version_label(hd) == ("Director's Cut", "1080p")
    assert titlepage.version_label({"container": "mkv"}) == ("MKV", "")
    assert "play_version" in menus.card_actions(film)
    assert "play_version" in menus.card_actions(film, on_page=True)
    assert "play_version" not in menus.card_actions(dict(film, files=[uhd, gone]))
    assert "play_version" not in menus.card_actions({"kind": "series", "files": [uhd, hd]})
