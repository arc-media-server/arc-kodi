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


# The catalogue's words (strings.po 30172 and 30603), as the Kodi side passes them.
CODE, SPECIAL = "S%d · E%d", "Special %d"


def test_episode_words_in_catalogue():
    import os
    po = open(os.path.join(os.path.dirname(__file__), "..", "resources", "language",
                           "resource.language.en_gb", "strings.po"), encoding="utf-8").read()
    assert 'msgctxt "#30172"\nmsgid "%s"' % CODE in po
    assert 'msgctxt "#30603"\nmsgid "%s"' % SPECIAL in po


def test_episode_code():
    from arc import models
    # The owner's rule for every Arc app: "S1 · E4", no leading zeros, "Special 3" for season 0.
    assert models.episode_code({"season_number": 1, "episode_number": 4}, CODE, SPECIAL) == "S1 · E4"
    assert models.episode_code({"season_number": 12, "episode_number": 10}, CODE, SPECIAL) == "S12 · E10"
    assert models.episode_code({"season_number": 0, "episode_number": 3}, CODE, SPECIAL) == "Special 3"


def test_episode_heading():
    from arc import models
    ep = {"season_number": 1, "episode_number": 4, "title": "Ariel"}
    assert models.episode_heading(ep, CODE, SPECIAL) == "S1 · E4 · Ariel"
    assert models.episode_heading(dict(ep, season_number=0), CODE, SPECIAL) == "Special 4 · Ariel"
    assert models.episode_heading(dict(ep, episode_number=12), CODE, SPECIAL, unplaced=True) == "Ariel"
    assert models.episode_heading({"title": "Pilot"}, CODE, SPECIAL) == "Pilot"
    assert models.episode_heading({"season_number": 1, "episode_number": 2}, CODE, SPECIAL) == "S1 · E2"


def test_unplaced_episodes_have_no_code():
    from arc import models
    unplaced = {"season_number": 0, "episode_number": 0, "title": "Trash"}
    assert not models.placed(unplaced)
    assert models.episode_code(unplaced, CODE, SPECIAL) == ""   # never "S0 · E0" or "Special 0"
    assert models.episode_heading(unplaced, CODE, SPECIAL) == "Trash"


def test_previous_episode():
    eps = [{"id": "a"}, {"id": "b", "available": False}, {"id": "c"}, {"id": "d"}]
    assert titlepage.previous_episode(eps, "d")["id"] == "c"
    assert titlepage.previous_episode(eps, "c") is None      # the one before isn't on disk
    assert titlepage.previous_episode(eps, "a") is None
    assert titlepage.previous_episode(eps, "zz") is None
    assert titlepage.previous_episode(None, "a") is None


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
    assert titlepage.version_label(uhd) == ("4K", "DV · HDR10 · TrueHD 7.1 · Atmos · 60.0 GB")
    assert titlepage.version_label(hd) == ("Director's Cut", "1080p · SDR")
    assert titlepage.version_label({"container": "mkv"}) == ("MKV", "")
    assert "play_version" in menus.card_actions(film)
    assert "play_version" in menus.card_actions(film, on_page=True)
    assert "play_version" not in menus.card_actions(dict(film, files=[uhd, gone]))
    assert "play_version" not in menus.card_actions({"kind": "series", "files": [uhd, hd]})


# MARK: - Play's words, the meta line and fitting the overview

def _ep(s, e, pos=0, played=False):
    return {"kind": "episode", "season_number": s, "episode_number": e, "id": "e%d%d" % (s, e),
            "files": [{"duration_ms": 3000000}], "user_data": {"position_ms": pos, "played": played}}


def test_clock():
    assert titlepage.clock(6012000) == "1:40:12"
    assert titlepage.clock(754000) == "12:34"
    assert titlepage.clock(0) == "0:00"


def test_play_label_for_a_film():
    film = {"kind": "movie", "files": [{"duration_ms": 7200000}], "user_data": {"position_ms": 6012000}}
    assert titlepage.play_label(film, titlepage.play_action(film)) == ("resume_from", "1:40:12")
    film["user_data"] = {}
    assert titlepage.play_label(film, titlepage.play_action(film)) == ("play", None)
    assert titlepage.play_label(film, None) == ("play", None)


def test_play_label_for_a_show():
    show = {"kind": "series"}
    resume = _ep(1, 3, pos=1000)
    assert titlepage.play_label(show, titlepage.play_action(show, resume)) == ("resume_episode", resume)
    first = _ep(1, 1)
    assert titlepage.play_label(show, titlepage.play_action(show, first)) == ("start_watching", first)
    later = _ep(1, 4)
    assert titlepage.play_label(show, titlepage.play_action(show, later)) == ("play_episode", later)
    special = _ep(0, 1)
    assert titlepage.play_label(show, titlepage.play_action(show, special)) == ("play_episode", special)
    # Outside the show's order (Arc's 0/0) an episode has no number to show.
    unplaced = _ep(0, 0, pos=5000)
    assert titlepage.play_label(show, titlepage.play_action(show, unplaced)) == ("resume_from", "0:05")


def test_meta_line():
    left = lambda n: "%d episodes left" % n
    film = {"kind": "movie", "year": 2024, "runtime_min": 166, "rating": 8.24}
    assert titlepage.meta_line(film, left) == ("2024 \u00b7 2h 46m \u00b7", "8.2")
    assert titlepage.meta_line(dict(film, edition="IMAX"), left) == ("2024 · IMAX · 2h 46m ·", "8.2")
    assert titlepage.meta_line({"kind": "movie", "edition": "IMAX"}, left) == ("IMAX", "")
    show = {"kind": "series", "year": 2008, "unwatched_count": 12, "runtime_min": 47}
    assert titlepage.meta_line(show, left) == ("2008 \u00b7 12 episodes left", "")
    show["unwatched_count"] = 0
    show["rating"] = 0
    assert titlepage.meta_line(show, left) == ("2008", "")
    assert titlepage.meta_line({"kind": "movie", "rating": 7}, left) == ("", "7.0")
    episode = {"kind": "episode", "year": 2008, "runtime_min": 47}
    assert titlepage.meta_line(episode, left) == ("47m", "")


def test_time_left():
    assert titlepage.time_left(_ep(1, 1)) == (False, "50m")
    assert titlepage.time_left(_ep(1, 1, pos=1200000)) == (True, "30m")
    assert titlepage.time_left(_ep(1, 1, pos=2990000)) == (True, "1m")
    assert titlepage.time_left({"kind": "episode"}) == (False, "")


def test_clip_keeps_short_text_and_cuts_long_text():
    text, cut, lines = titlepage.clip("A short overview.", 1000)
    assert (text, cut, lines) == ("A short overview.", False, 1)
    long = " ".join(["Paul Atreides unites with Chani and the Fremen"] * 12)
    text, cut, lines = titlepage.clip(long, 1000)
    assert cut and lines == 3 and text.endswith("…")
    assert len(titlepage.wrap_lines(text, 1000)) == 3
    assert titlepage.clip("", 1000) == ("", False, 0)


def test_hero_layout_sits_low_on_the_screen():
    film = titlepage.hero_layout(False, starring_lines=1, director_lines=1)
    assert film["height"] == 1080 and film["row"] == 920 and film["hint"] == 1000
    assert film["directors"] + titlepage.SMALL_LINE == 992      # level with the buttons' foot
    assert film["starring"] < film["directors"]
    assert film["meta"] + 40 + 16 == film["row"] - 12          # the block ends 12 over the row
    assert film["overview"] + 3 * titlepage.BODY_LINE + 16 == film["meta"]
    assert film["genres"] + 44 == film["block"] and film["logo"] + 240 + 32 == film["genres"]
    show = titlepage.hero_layout(True, overview_lines=1, cut=False)
    assert show["height"] == 932 and show["row"] == 836
    assert "more" not in show
    cut = titlepage.hero_layout(True, cut=True)
    assert cut["more"] + 32 + 16 == cut["meta"] and cut["block"] < show["block"]
    bare = titlepage.hero_layout(False, rating_row=False, overview_lines=0, meta_row=False)
    assert "overview" not in bare and bare["logo"] + 240 + 32 == bare["block"]
