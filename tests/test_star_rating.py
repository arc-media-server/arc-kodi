import pytest
from arc import ratings
from arc.api import ArcAPI, APIError
from fake_server import FakeServer


def test_half_stars_and_clear():
    assert ratings.CHOICES == tuple(range(10, 0, -1))
    assert ratings.stars(9) == "★★★★½"
    assert ratings.stars(1) == "½"
    assert ratings.stars(0) == ""
    assert ratings.out_of_five(9) == "4.5"
    assert ratings.out_of_five(8) == "4"


def test_rating_saved_and_cleared_against_standin():
    server = FakeServer({("PUT", "items/a%2Fb/rating"): (204, None)})
    api = ArcAPI("http://scratch", token="scratch", opener=server)
    api.set_rating("a/b", 9)
    api.set_rating("a/b", 0)
    assert [r["body"] for r in server.requests] == [{"rating": 9}, {"rating": 0}]
    assert all(r["auth"] == "Bearer scratch" for r in server.requests)


def test_rating_failure_is_reported():
    server = FakeServer({("PUT", "items/a/rating"): (403, {"error": "denied"})})
    with pytest.raises(APIError):
        ArcAPI("http://scratch", opener=server).set_rating("a", 5)
