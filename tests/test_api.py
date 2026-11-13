from arc.api import ArcAPI, APIError, Unreachable, normalise_address, versioned
from fake_server import FakeServer

import pytest
from urllib import error as urlerror


def make(routes, token="tok"):
    server = FakeServer(routes)
    api = ArcAPI("http://arc:8099", token=token, opener=server)
    return api, server


def test_normalise_address():
    assert normalise_address("192.168.1.20") == "http://192.168.1.20:8099"
    assert normalise_address("http://192.168.1.20") == "http://192.168.1.20:8099"
    assert normalise_address("https://arc.example.com") == "https://arc.example.com"
    assert normalise_address("192.168.1.20:9000") == "http://192.168.1.20:9000"
    assert normalise_address("arc.example.com/base") == "http://arc.example.com:8099/base"
    assert normalise_address("  ") is None
    assert normalise_address("has space") is None
    assert normalise_address("ftp://x") is None


def test_versioned():
    assert versioned("/api/items/x/stream") == "/api/v1/items/x/stream"
    assert versioned("/api/v1/items/x/stream") == "/api/v1/items/x/stream"
    assert versioned("https://cdn/x.jpg") == "https://cdn/x.jpg"


def test_get_sends_bearer_and_decodes():
    api, server = make({("GET", "identity"): (200, {"name": "Home Arc"})})
    assert api.identity() == {"name": "Home Arc"}
    assert server.requests[0]["auth"] == "Bearer tok"


def test_poll_link_states():
    api, _ = make({("GET", "auth/link/p"): (202, None)})
    assert api.poll_link("p") == ("waiting", None)
    api, _ = make({("GET", "auth/link/p"): (404, {"error": "gone"})})
    assert api.poll_link("p") == ("expired", None)
    api, _ = make({("GET", "auth/link/p"): (200, {"token": "T"})})
    assert api.poll_link("p") == ("approved", "T")


def test_next_episode_204_is_none():
    api, _ = make({("GET", "items/e1/next"): (204, None)})
    assert api.next_episode("e1") is None
    api, _ = make({("GET", "items/e1/next"): (200, {"id": "e2", "kind": "episode"})})
    assert api.next_episode("e1")["id"] == "e2"


def test_error_carries_needs_and_code():
    api, _ = make({("POST", "auth/profile"): (401, {"error": "PIN required", "needs": "pin", "code": "authentication_required"})})
    with pytest.raises(APIError) as e:
        api.choose_profile("p1")
    assert e.value.status == 401
    assert e.value.needs == "pin"
    assert e.value.code == "authentication_required"


def test_unreachable_wrapped():
    class Dead(object):
        def open(self, *a, **k):
            raise urlerror.URLError("down")

    api = ArcAPI("http://arc", token="t", opener=Dead())
    with pytest.raises(Unreachable):
        api.health()


def test_set_played_and_watchlist_bodies():
    api, server = make({("PUT", "items/i1/played"): (204, None),
                        ("PUT", "items/i1/watchlist"): (204, None)})
    api.set_played("i1", True)
    api.set_watchlist("i1", False)
    assert server.requests[0]["body"] == {"played": True}
    assert server.requests[1]["body"] == {"on": False}


def test_cast_link_returns_url():
    api, server = make({("POST", "cast"): (200, {"url": "http://arc/api/cast/T/api/items/i1/stream", "local_only": False})})
    assert api.cast_link("/api/items/i1/stream").endswith("/stream")
    assert server.requests[0]["body"] == {"url": "/api/items/i1/stream"}


def test_absolute_versions_api_paths():
    api, _ = make({})
    assert api.absolute("/api/items/i1/images/backdrop") == "http://arc:8099/api/v1/items/i1/images/backdrop"
    assert api.absolute("https://cdn/x.jpg") == "https://cdn/x.jpg"
