from arc.browse import LibraryQuery, facet_values, resolution_name, shows_resolution

FILMS = {"id": 1, "kind": "movies", "name": "Films"}
SHOWS = {"id": 2, "kind": "shows", "name": "TV"}


def test_parameters_default():
    q = LibraryQuery()
    assert q.parameters(FILMS, 0, 60) == {"library_id": "1", "kind": "movie", "sort": "added",
                                          "offset": "0", "limit": "60"}
    assert q.parameters(SHOWS, 60, 60)["kind"] == "series"


def test_choosing_the_same_sort_reverses_it():
    q = LibraryQuery()
    q.choose_sort("title")
    assert (q.sort, q.reversed) == ("title", False)
    q.choose_sort("title")
    assert q.reversed and q.parameters(FILMS, 0, 1)["reverse"] == "1"
    q.choose_sort("year")
    assert (q.sort, q.reversed) == ("year", False)


def test_filters_and_their_name():
    q = LibraryQuery()
    assert q.filter_name() == ("all", None) and not q.filtered
    q.genre = "Drama"
    assert q.filter_name() == ("genre", "Drama")
    q.unwatched = True
    assert q.filter_name() == ("filtered", None)
    p = q.parameters(FILMS, 0, 10)
    assert p["genre"] == "Drama" and p["unwatched"] == "1"
    q.clear_filters()
    assert not q.filtered and "genre" not in q.parameters(FILMS, 0, 10)


def test_facets_and_names():
    facets = {"genres": [{"value": "Drama", "count": 3}, {"value": "", "count": 1}], "decades": None}
    assert facet_values(facets, "genres") == [("Drama", 3)]
    assert facet_values(facets, "decades") == []
    assert resolution_name("4k") == "4K" and resolution_name("odd") == "odd"
    assert shows_resolution(FILMS) and not shows_resolution(SHOWS)


def test_direction_follows_the_servers_order():
    q = LibraryQuery()
    assert q.direction() == "newest"
    q.choose_sort("title")
    assert q.direction() == "a_to_z"
    q.choose_sort("title")
    assert q.direction() == "z_to_a"
