from arc import recommended, home


def test_titles_follow_the_library_kind():
    assert recommended.title({"type": "top_rated"}, "Films", "movies") == ("top_rated_movies", None)
    assert recommended.title({"type": "top_rated"}, "TV", "shows") == ("top_rated_shows", None)
    assert recommended.title({"type": "recently_added"}, "Films", "movies") == ("recently_added", "Films")
    assert recommended.title({"type": "because_you_watched", "name": "Heat"}) == ("because_you_watched", "Heat")
    assert recommended.title({"type": "top_by_person", "name": "Nolan", "role": "director"}) == ("top_movies_by", "Nolan")
    assert recommended.title({"type": "top_by_person", "name": "Pacino", "role": "actor"}, "", "shows") == ("top_shows_with", "Pacino")


def test_unknown_types_keep_arcs_title():
    assert recommended.title({"type": "brand_new", "title": "Something New"}) == (None, "Something New")


def test_styles():
    assert recommended.style({"type": "continue"}) == home.THUMB
    assert recommended.style({"type": "recently_watched"}, "shows") == home.THUMB
    assert recommended.style({"type": "recently_watched"}, "movies") == home.POSTER
    assert recommended.style({"type": "top_rated", "style": "arc"}) == home.BACKDROP


def test_rows_skip_empty_ones():
    page = {"rows": [{"id": "a", "type": "top_rated", "items": [{"id": "1", "kind": "movie", "title": "X"}]},
                     {"id": "b", "type": "rediscover", "items": []}]}
    out = recommended.rows(page, {"name": "Films", "kind": "movies"})
    assert [r["id"] for r in out] == ["a"]
    assert out[0]["title"] == ("top_rated_movies", None) and out[0]["cards"][0]["item"]["id"] == "1"
