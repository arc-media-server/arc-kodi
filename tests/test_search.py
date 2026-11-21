from arc import search


def test_edit_types_deletes_and_clears():
    t = ""
    for k in ["a", "l", search.SPACE, search.SPACE, "i"]:
        t = search.edit(t, k)
    assert t == "al i"
    assert search.edit(t, search.DELETE) == "al "
    assert search.edit(t, search.CLEAR) == ""
    assert search.edit("", search.SPACE) == ""
    assert search.edit("", search.DELETE) == ""
    assert search.edit("x" * search.MAX_LENGTH, "y") == "x" * search.MAX_LENGTH


def test_query_trims_and_skips_empty():
    assert search.query("  alien ") == "alien"
    assert search.query("   ") is None
    assert search.query(None) is None


def test_rows_in_order_only_with_matches():
    data = {
        "people": [{"id": 3, "name": "Sigourney Weaver"}, {"id": 0, "name": "nobody"}],
        "movies": [{"id": "m1", "title": "Alien"}],
        "shows": [{"id": "s1"}, {"id": "s2"}],
        "genres": [{"name": "Horror", "library_id": 1, "library_name": "Films"}, {"name": "x"}],
        "collections": [{"id": "c1", "title": "Alien Collection"}],
        "future_kind": [{"id": 1}],
    }
    got = [(k, s, [e.get("id") or e.get("name") for e in es]) for k, s, es in search.rows(data)]
    assert got == [("top", "poster", ["m1", "s1", "s2"]), ("collections", "poster", ["c1"]),
                   ("people", "face", [3]), ("genres", "pill", ["Horror"])]
    assert search.rows(None) == []
    assert search.rows({"movies": None}) == []


def test_helpers():
    assert search.initials("Sigourney Weaver") == "SW"
    assert search.initials("") == ""
    assert search.known_for({"known_for": "actor"}) == "Actor"
    assert search.known_for({}) == ""
    assert search.collection_image({"id": "c1", "images": {"primary": "/a.jpg"}}) == "/a.jpg"
    assert search.collection_image({"id": "c1"}) == "/api/collections/c1/images/primary"
    assert len(search.KEYS) == 36 and len(search.KEYS) % search.COLUMNS == 0
