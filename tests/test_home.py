import datetime

from arc import home, models


LIBS = [{"id": 1, "name": "Films", "kind": "movies"},
        {"id": 2, "name": "Shows", "kind": "shows"},
        {"id": 3, "name": "Home Videos", "kind": "videos"}]


def test_ordered_libraries_follows_order_then_new_last():
    out = home.ordered_libraries(LIBS, [2, 1])
    assert [lib["id"] for lib in out] == [2, 1, 3]


def test_seasonal_pick_by_date():
    assert home.seasonal_pick(datetime.date(2026, 2, 10))[0] == "romance"
    assert home.seasonal_pick(datetime.date(2026, 10, 15))[0] == "horror"
    assert home.seasonal_pick(datetime.date(2026, 6, 1)) is None


def test_resolve_rows_order_and_hidden():
    prefs = {"home": [{"id": "recent:1", "hidden": True}], "watchlist_position": 1,
             "library_order": [1, 2, 3]}
    rows = home.resolve_home_rows(prefs, LIBS, today=datetime.date(2026, 6, 1))
    ids = [r["id"] for r in rows]
    assert ids[0] == "continue"
    assert "recent:1" not in ids  # hidden
    assert "watchlist" in ids
    assert ids.index("watchlist") == ids.index("recent:2") - 1  # watchlist before the 2nd library
    assert "recent:3" in ids


def test_resolve_rows_collections_and_playlists_last():
    prefs = {"home": [{"id": "collection:c1", "title": "Marvel"}, {"id": "playlist:p1", "title": "Mix"}]}
    rows = home.resolve_home_rows(prefs, [], today=datetime.date(2026, 6, 1))
    assert [r["id"] for r in rows][-2:] == ["collection:c1", "playlist:p1"]


def test_custom_row_query_drops_empty_and_zero():
    flt = {"library_id": 1, "genre": "Action", "unwatched": True, "min_rating": 0, "sort": "rating"}
    q = home.custom_row_query(flt, LIBS[0], limit=10)
    assert q == {"library_id": "1", "genre": "Action", "unwatched": "1", "sort": "rating",
                 "kind": "movie", "limit": "10"}


def test_card_picks_episode_artwork():
    ep = {"id": "e1", "kind": "episode", "title": "Pilot",
          "images": {"primary": "/still.jpg", "series_primary": "/poster.jpg",
                     "series_backdrop": "/show.jpg", "series_logo": "/logo.png"}}
    c = home.card(ep)
    assert c["poster"] == "/poster.jpg"       # series poster, not the still
    assert c["thumb"] == "/still.jpg"         # the episode still for a wide card
    assert c["logo"] == "/logo.png"


def test_with_show_art_swaps_thumb():
    ep = {"id": "e1", "kind": "episode", "images": {"primary": "/still.jpg", "series_backdrop": "/show.jpg"}}
    c = home.with_show_art(home.card(ep))
    assert c["thumb"] == "/show.jpg"
    assert c["show_art"] is True


def test_recent_season_card_identity():
    recent = {"type": "season", "season_number": 2, "episodes": 3, "added_at": 123,
              "season_poster": "/s2.jpg", "item": {"id": "sh1", "kind": "series", "images": {"primary": "/p.jpg"}}}
    c = home.recent_card(recent)
    assert c["id"] == "season:sh1:2:123"
    assert c["new_episodes"] == 3
    assert c["season_poster"] == "/s2.jpg"


def test_spoilers():
    from arc import models
    ep = {"id": "e", "kind": "episode", "images": {"primary": "/still", "series_backdrop": "/show"}}
    on = {"hide_spoilers": True}
    assert models.spoiler_hidden(on, ep)
    assert not models.spoiler_hidden({}, ep)
    assert not models.spoiler_hidden(on, dict(ep, user_data={"position_ms": 1000}))   # started
    assert not models.spoiler_hidden(on, dict(ep, user_data={"played": True}))
    assert not models.spoiler_hidden(on, {"kind": "movie"})
    c = home.without_spoilers(home.card(ep))
    assert c["thumb"] == "/show" and c["show_art"]
    bare = home.without_spoilers(home.card(dict(ep, images={"primary": "/still"})))
    assert bare["thumb"] is None and home.card_art(bare, home.THUMB) is None
