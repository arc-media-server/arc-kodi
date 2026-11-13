from arc import menus


def test_movie_unplayed():
    m = {"id": "m", "kind": "movie"}
    assert menus.card_actions(m) == ["play", "watched", "watchlist_add"]


def test_movie_in_progress_on_continue_row():
    m = {"id": "m", "kind": "movie", "user_data": {"position_ms": 60000}, "runtime_min": 100}
    assert menus.card_actions(m, continue_row=True) == ["resume", "from_start", "watched", "watchlist_add",
                                                       "remove_continue"]


def test_episode_offers_its_show_but_no_watchlist():
    e = {"id": "e", "kind": "episode", "parent_id": "s", "series_title": "Firefly",
         "user_data": {"played": True}}
    assert menus.card_actions(e) == ["play", "unwatched", "go_to_show"]
    assert menus.show_ref(e) == {"id": "s", "kind": "series", "title": "Firefly"}


def test_series_watched_and_watchlisted():
    s = {"id": "s", "kind": "series", "user_data": {"watchlisted": True}}
    assert menus.card_actions(s) == ["watched", "watchlist_remove"]


def test_on_page_leaves_out_play_and_show():
    e = {"id": "e", "kind": "episode", "parent_id": "s"}
    assert menus.card_actions(e, on_page=True) == ["watched"]


def test_episode_on_its_show_page():
    e = {"id": "e", "kind": "episode", "parent_id": "s"}
    assert menus.card_actions(e, in_show=True) == ["play", "watched"]
