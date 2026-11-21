from arc.browse import (LibraryQuery, audio_codec_name, choices, dynamic_range_name, facet_values, offered,
                        resolution_name, shows_resolution, video_codec_name, watchlist_view)

FILMS = {"id": 1, "kind": "movies", "name": "Films"}
SHOWS = {"id": 2, "kind": "shows", "name": "TV"}


def test_parameters_default():
    q = LibraryQuery()
    assert q.parameters(FILMS, 0, 60) == {"library_id": "1", "kind": "movie", "sort": "title",
                                          "offset": "0", "limit": "60"}
    assert q.parameters(SHOWS, 60, 60)["kind"] == "series"


def test_choosing_the_same_sort_reverses_it():
    q = LibraryQuery()
    assert (q.sort, q.reversed) == ("title", False)
    q.choose_sort("title")
    assert q.reversed and q.parameters(FILMS, 0, 1)["reverse"] == "1"
    q.choose_sort("year")
    assert (q.sort, q.reversed) == ("year", False)


def test_shuffle_is_a_sort_with_no_other_way_round():
    q = LibraryQuery()
    q.choose_sort("shuffle")
    q.choose_sort("shuffle")
    assert (q.sort, q.reversed) == ("shuffle", False)
    q.reversed = True
    assert "reverse" not in q.parameters(FILMS, 0, 1)


def test_filters_and_their_count():
    q = LibraryQuery()
    assert q.filter_count == 0 and not q.filtered
    q.genre = "Drama"
    assert q.filter_count == 1
    q.unwatched = True
    assert q.filter_count == 2
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
    assert q.direction() == "a_to_z"
    q.choose_sort("title")
    assert q.direction() == "z_to_a"
    q.choose_sort("added")
    assert q.direction() == "newest"


def test_watch_status_and_unwatched_exclude_each_other():
    q = LibraryQuery()
    q.set_unwatched(True)
    q.set_watch_state("played")
    assert q.watch_state == "played" and not q.unwatched
    q.set_unwatched(True)
    assert q.unwatched and q.watch_state is None
    p = q.parameters(FILMS, 0, 10)
    assert p["unwatched"] == "1" and "watch_state" not in p


def test_media_filters_parameters_count_and_clear():
    q = LibraryQuery()
    q.dynamic_range = "dolby_vision"
    assert q.filter_count == 1
    q.audio_channels = 8
    p = q.parameters(FILMS, 0, 10)
    assert p["dynamic_range"] == "dolby_vision" and p["audio_channels"] == "8"
    assert q.filter_count == 2
    q.clear_filters()
    assert not q.filtered and "audio_channels" not in q.parameters(FILMS, 0, 10)


def test_media_filters_offered_only_when_they_narrow():
    facets = {"video_codecs": [{"value": "hevc", "count": 4}],
              "dynamic_ranges": [{"value": "sdr", "count": 3}, {"value": "hdr10", "count": 1}]}
    assert not offered(facets, "video_codecs", None)
    assert offered(facets, "video_codecs", "h264")  # chosen stays visible to change
    assert offered(facets, "dynamic_ranges", None)


def test_choices_keep_the_chosen_value_and_order_channels():
    facets = {"audio_channels": [{"value": "2", "count": 1}, {"value": "8", "count": 1}, {"value": "6", "count": 2}],
              "audio_codecs": [{"value": "aac", "count": 2}]}
    assert choices(facets, "audio_channels", None) == [8, 6, 2]
    assert choices(facets, "audio_codecs", "truehd") == ["aac", "truehd"]


def test_media_names():
    assert dynamic_range_name("hdr10_plus") == "HDR10+"
    assert video_codec_name("hevc") == "HEVC" and video_codec_name("prores") == "PRORES"
    assert audio_codec_name("eac3") == "Dolby Digital Plus"


def test_watchlist_view_shows_and_sorts():
    items = [{"id": 1, "kind": "movie", "title": "The Matrix", "release_date": "1999-03-31"},
             {"id": 2, "kind": "series", "title": "Andor", "year": 2022},
             {"id": 3, "kind": "movie", "title": "Arrival", "release_date": "2016-11-11"}]
    assert [it["id"] for it in watchlist_view(items)] == [1, 2, 3]  # Arc's order: date added
    assert [it["id"] for it in watchlist_view(items, "movies")] == [1, 3]
    assert [it["id"] for it in watchlist_view(items, "shows")] == [2]
    assert [it["id"] for it in watchlist_view(items, "all", "title")] == [2, 3, 1]  # "The" is ignored
    assert [it["id"] for it in watchlist_view(items, "all", "released")] == [2, 3, 1]
