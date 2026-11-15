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
