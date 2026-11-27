from arc.api import ArcAPI
from arc.queues import PlayQueue
from fake_server import FakeServer


def queue(entries, current, revision=1, shuffled=False):
    return {"id": "q1", "revision": revision, "current_entry_id": current, "shuffled": shuffled,
            "entries": entries}


E = [{"id": "e1", "available": True, "item": {"id": "a", "kind": "movie"}},
     {"id": "e2", "available": False},
     {"id": "e3", "available": True, "item": {"id": "c", "kind": "movie"}}]


def make(routes):
    server = FakeServer(routes)
    return ArcAPI("http://arc", token="t", opener=server), server


def test_create_shuffle_and_walk():
    state = {"rev": 1, "cur": "e1"}

    def patch(_q, body):
        assert body["revision"] == state["rev"]
        state["rev"] += 1
        if body["operation"] == "advance":
            order = [e["id"] for e in E]
            state["cur"] = order[order.index(state["cur"]) + 1]
        return 200, queue(E, state["cur"], state["rev"])

    api, server = make({("POST", "play-queues"): (201, queue(E, "e1")), ("PATCH", "play-queues/q1"): patch})
    q = PlayQueue.create(api, item_ids=["a", "b", "c"], shuffle=True)
    assert server.requests[0]["body"] == {"item_ids": ["a", "b", "c"]}
    assert server.requests[1]["body"]["operation"] == "shuffle"
    assert q.current_item()["id"] == "a"
    assert q.peek_next()["id"] == "c"          # e2 can't be played
    assert q.advance()["id"] == "c"            # passes over e2
    assert q.advance() is None                 # the end


def test_playlist_queue_without_shuffle():
    api, server = make({("POST", "play-queues"): (201, queue(E[:1], "e1"))})
    q = PlayQueue.create(api, playlist_id="p1")
    assert server.requests[0]["body"] == {"playlist_id": "p1"}
    assert len(server.requests) == 1 and q.peek_next() is None


def test_an_existing_queue_is_replaced():
    calls = []

    def post(_q, body):
        calls.append(body)
        if "replace_id" not in body:
            return 409, {"error": "a queue exists", "code": "conflict"}
        return 201, queue(E[:1], "e1")

    api, server = make({("POST", "play-queues"): post,
                        ("GET", "play-queues/current"): (200, queue(E, "e3", revision=7))})
    q = PlayQueue.create(api, item_ids=["a"])
    assert calls[1] == {"item_ids": ["a"], "replace_id": "q1", "revision": 7}
    assert q.current_item()["id"] == "a"


def test_moved_keeps_the_playing_entry_first():
    from arc.queues import moved
    assert moved(["a", "b", "c"], 1, "c", -1) == ["a", "c", "b"]
    assert moved(["a", "b", "c"], 1, "b", -1) is None      # not in front of the one playing
    assert moved(["a", "b", "c"], 1, "c", 1) is None
    assert moved(["a", "b", "c"], 1, "a", 1) is None       # the one playing doesn't move


def test_edit_retries_once_after_a_conflict():
    state = {"n": 0}

    def patch(_q, body):
        state["n"] += 1
        if state["n"] == 1:
            return 409, {"error": "changed"}
        assert body["revision"] == 5 and body["operation"] == "next"
        return 200, queue(E, "e1", 6)

    api, _ = make({("PATCH", "play-queues/q1"): patch, ("GET", "play-queues/q1"): (200, queue(E, "e1", 5))})
    from arc.queues import PlayQueue as Q
    q = Q(api, queue(E, "e1"))
    q.add(["x"], next_=True)
    assert q.revision == 6 and state["n"] == 2
    assert [eid for eid, _ in q.upcoming()] == ["e1", "e3"]
    assert q.editable("e3") == {"earlier": True, "later": False, "remove": True}
