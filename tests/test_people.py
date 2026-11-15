from arc import people

PAGE = {"person": {"id": 1, "name": "A"}, "credits": [
    {"item": {"id": "m1", "kind": "movie", "title": "Old", "year": 1995, "release_date": "1995-12-15"},
     "character": "Neil", "roles": ["actor"]},
    {"item": {"id": "m2", "kind": "movie", "title": "New", "year": 2010, "release_date": "2010-07-15"},
     "roles": ["director", "writer"]},
    {"item": {"id": "s1", "kind": "series", "title": "Show", "year": 2005}, "character": "Host", "roles": []},
    {"item": {"id": "m3", "kind": "movie", "title": "Newer", "year": 2020}, "roles": ["actor"]},
    {"item": {"id": "m3", "kind": "movie", "title": "Newer", "year": 2020}, "roles": ["actor"]},
]}


def test_rows_split_and_newest_first():
    out = people.rows(PAGE)
    assert [k for k, _ in out] == ["movies", "shows", "crew"]
    assert [c["item"]["id"] for c in out[0][1]] == ["m3", "m1"]
    assert [c["item"]["id"] for c in out[2][1]] == ["m2"]


def test_count_and_part():
    assert people.title_count(PAGE) == 4
    assert people.part(PAGE["credits"][0]) == ("Old (1995)", "Neil", None)
    assert people.part(PAGE["credits"][1]) == ("New (2010)", None, "director")


def test_empty_page():
    assert people.rows({}) == [] and people.title_count(None) == 0
