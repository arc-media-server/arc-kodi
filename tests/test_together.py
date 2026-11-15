import pytest

from arc import together
from arc.api import ArcAPI, RoomConflict

from fake_server import FakeServer


def room(**kw):
    r = {"id": "r1", "revision": 3, "generation": 1, "state": "paused", "position_ms": 0, "at_ms": 0,
         "rate": 1, "host_id": "p1", "self_id": "p1",
         "participants": [{"id": "p1", "name": "Sam", "available": True, "ready": True, "state": "paused"},
                          {"id": "p2", "name": "Alex", "available": True, "ready": False, "state": "waiting"}]}
    r.update(kw)
    return r


def test_codes():
    assert together.normalise_code(" abcd-12 34 ") == "ABCD1234"
    assert together.format_code("abcd1234") == "ABCD-1234"
    assert together.format_code("abc") == "ABC"
    assert together.normalise_code("ÀBCD") == "BCD"


def test_room_basics():
    r = room()
    assert together.is_host(r) and together.host_name(r) == "Sam"
    assert not together.is_host(room(self_id="p2"))
    assert not together.started(r)
    assert together.started(room(position_ms=5)) and together.started(room(state="playing"))
    assert together.should_adopt(room(revision=4), r)
    assert together.should_adopt(room(revision=3), r)
    assert not together.should_adopt(room(revision=2), r)
    assert together.should_adopt(room(id="r2", revision=1), r)
    assert together.host_name({"host_id": "x", "host_name": "Jo", "participants": []}) == "Jo"


def test_clock_and_expected_position():
    # Two samples: the second has the shorter round trip and wins.
    samples = [(1000, 1300, 6100, 6110), (2000, 2040, 7020, 7022)]
    assert together.clock_offset(samples) == ((7020 - 2000) + (7022 - 2040)) / 2.0
    assert together.clock_offset([]) is None
    playing = room(state="playing", position_ms=10000, at_ms=50000)
    assert together.expected_position(playing, 53000) == 13000
    assert together.expected_position(playing, 49000) == 10000
    assert together.expected_position(room(position_ms=7000), 99999) == 7000


def test_follower_plays_pauses_and_jumps_once_settled():
    f = together.Follower()
    playing = room(state="playing")
    assert f.step(playing, 10000, False, 0, 10500) == [("play",)]
    assert f.step(playing, 10000, True, 100, 13000) == [("seek", 13000)]
    # Settling: still out, but no second jump until Kodi has landed.
    assert f.step(playing, 10200, True, 5000, 18000) == []
    assert f.step(playing, 10200, True, 8200, 18000) == [("seek", 18000)]
    paused = room(state="paused", position_ms=20000)
    g = together.Follower()
    assert g.step(paused, 20500, True, 0, 20000) == [("pause",)]
    assert g.step(paused, 25000, False, 0, 20000) == [("seek", 20000)]
    h = together.Follower()
    h.settle(0)
    assert h.step(paused, 25000, False, 1000, 20000) == []


def test_notices():
    before = room(state="playing", revision=3, generation=1, changed_by="p1")
    paused = room(state="paused", revision=4, generation=1, changed_by="p2")
    assert together.notice(paused, before) == ("paused_by", "Alex")
    assert together.notice(room(state="playing", revision=5, changed_by="p2"), paused) == ("played_by", "Alex")
    assert together.notice(room(state="playing", revision=5, generation=2, changed_by="p2"), before) == ("moved_by", "Alex")
    assert together.notice(room(state="paused", revision=4, changed_by="p1"), before) is None   # me
    assert together.notice(room(state="paused", revision=3, changed_by="p2"), before) is None   # not newer
    assert together.notice(room(state="paused", revision=4), None) is None


def test_participant_status():
    assert together.participant_status({"available": False}) == "unavailable"
    assert together.participant_status({"available": True, "ready": False}) == "loading"
    assert together.participant_status({"available": True, "ready": True, "state": "waiting"}) == "loading"
    assert together.participant_status({"available": True, "ready": True, "state": "playing"}) == "watching"
    assert together.participant_status({"available": True, "ready": True, "state": "paused"}) == "ready"
    assert together.is_playing({"state": "waiting"}) and not together.is_playing({"state": "paused"})


def api_for(server):
    return ArcAPI("http://arc.test", token="t0ken", opener=server)


def test_api_calls_and_conflict():
    conflict = room(revision=7)
    server = FakeServer({
        ("GET", "watch-together/rooms"): (200, {"rooms": [{"id": "r1"}]}),
        ("GET", "watch-together/people"): lambda q, b: (200, {"people": [{"id": "x", "name": "Jo", "q": q}]}),
        ("POST", "watch-together/rooms"): lambda q, b: (201, {"room": {"id": "r9"}, "invite_code": "ABCD1234", "b": b}),
        ("POST", "watch-together/r1/commands"): (409, {"error": "room changed", "room": conflict}),
        ("POST", "watch-together/r1/heartbeat"): lambda q, b: (200, dict(room(), got=b)),
        ("GET", "watch-together/current"): (404, {"error": "not found"}),
        ("POST", "watch-together/rooms/r1/join"): (200, room()),
        ("POST", "watch-together/r1/leave"): (204, None),
    })
    api = api_for(server)
    assert api.watch_rooms() == [{"id": "r1"}]
    assert api.watch_people("m1")[0]["q"] == {"item_id": "m1"}
    made = api.create_invited_room("m1", ["x"])
    assert made["b"] == {"item_id": "m1", "profile_ids": ["x"]}
    with pytest.raises(RoomConflict) as e:
        api.room_command("r1", 3, "seek", position_ms=-5)
    assert e.value.room["revision"] == 7
    assert server.requests[-1]["body"] == {"revision": 3, "action": "seek", "position_ms": 0}
    beat = api.room_heartbeat("r1", 1, 1234.6, "playing", True)
    assert beat["got"] == {"generation": 1, "position_ms": 1234, "state": "playing", "ready": True}
    assert api.current_room() is None
    assert api.accept_room("r1")["id"] == "r1"
    api.leave_room("r1")


def test_room_stream_delivers_rooms_and_stops_when_gone():
    frames = ("event: room\nid: 3\ndata: " + '{"id":"r1","revision":3}' + "\n\n"
              ": ping\n\nevent: other\ndata: {}\n\n"
              "event: room\ndata: " + '{"id":"r1","revision":4,"state":"ended"}' + "\n\n").encode()
    answers = [(200, frames), (404, {"error": "not found"})]
    server = FakeServer({("GET", "watch-together/r1/events"): lambda q, b: answers.pop(0)})
    got, gone, waits = [], [], []
    s = together.RoomStream(api_for(server), "r1", got.append, gone.append, stopped=lambda: False,
                            wait=lambda sec: waits.append(sec) or False)
    s.run()
    assert [r["revision"] for r in got] == [3, 4]
    assert gone == [404]
    assert waits == [together.BACKOFF[0]]  # the first stream ended at once: a pause before the next
    assert server.requests[0]["headers"].get("Accept") == "text/event-stream"
