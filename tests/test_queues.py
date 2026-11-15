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
