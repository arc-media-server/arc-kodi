from arc import events
from arc.api import ArcAPI

from fake_server import FakeServer


def sse(*frames):
    return "".join(frames).encode("utf-8")


def api_for(server):
    return ArcAPI("http://arc.test", token="t0ken", opener=server)


def test_parser_frames_ids_comments():
    p = events.SSEParser()
    lines = [": heartbeat\n", "id: 7\n", "event: invalidate\n", 'data: {"topic":"profile"}\n', "\n",
             "event: resync\r\n", "data:\r\n", "\r\n", "\n"]
    frames = [f for f in (p.feed(l) for l in lines) if f]
    assert frames == [("invalidate", '{"topic":"profile"}', "7"), ("resync", "", "7")]
    assert p.last_id == "7"


def test_change_topics_and_libraries():
    c = events.Change()
    c.add("invalidate", {"topic": "catalog", "library_id": 2})
    assert c.catalog(2) and not c.catalog(3) and c.catalog() and not c.personal()
    assert not c.libraries_changed()
    c.add("invalidate", {"topic": "library"})
    assert c.catalog(3) and c.libraries_changed()
    p = events.Change()
    p.add("invalidate", {"topic": "playback"})
    assert p.personal() and not p.catalog() and p.touches(5)
    admin = events.Change()
    admin.add("invalidate", {"topic": "activity"})
    admin.add("invalidate", {"topic": "a_future_topic"})
    admin.add("invalidate", "not an object")
    assert admin.empty
    r = events.Change()
    r.add("resync", None)
    assert r.everything and r.personal() and r.catalog(9) and r.libraries_changed() and not r.empty


def test_gatherer_merges_a_burst():
    now = [0.0]
    g = events.Gatherer(clock=lambda: now[0])
    a, b = events.Change(), events.Change()
    a.add("invalidate", {"topic": "catalog", "library_id": 1})
    b.add("invalidate", {"topic": "profile"})
    g.add(a)
    now[0] = 0.5
    g.add(b)
    assert g.take() is None
    now[0] = 1.0
    got = g.take()
    assert got.topics == {"catalog", "profile"} and got.library_ids == {1}
    assert g.take() is None


def run_stream(server, max_waits=3):
    got, waits = [], []

    def wait(seconds):
        waits.append(seconds)
        return len(waits) >= max_waits

    stream = events.EventStream(api_for(server), got.append, stopped=lambda: False, wait=wait)
    stream.run()
    return got, waits, stream


def test_stream_skips_first_resync_and_resumes_with_last_id():
    bodies = [sse("event: resync\ndata: {}\n\n", "id: 1\nevent: invalidate\ndata: {\"topic\":\"profile\"}\n\n",
                  ": heartbeat\n\n", "id: 2\nevent: invalidate\ndata: {\"topic\":\"sessions\"}\n\n"),
              sse("id: 3\nevent: resync\ndata: {}\n\n")]

    def handler(q, b):
        return 200, bodies.pop(0) if bodies else b""

    server = FakeServer({("GET", "events"): handler})
    got, waits, stream = run_stream(server, max_waits=3)
    assert [sorted(c.topics) for c in got[:1]] == [["profile"]]
    assert got[1].everything  # a resync on a later connection does mean refetch
    assert len(got) == 2      # "sessions" (admin) was dropped
    reqs = [r for r in server.requests if r["path"] == "events"]
    assert reqs[0]["auth"] == "Bearer t0ken"
    assert reqs[0]["headers"].get("Accept") == "text/event-stream"
    assert "Last-event-id" not in reqs[0]["headers"]
    assert reqs[1]["headers"].get("Last-event-id") == "2"
    assert reqs[2]["headers"].get("Last-event-id") == "3"


def test_stream_honours_retry_after_and_stops_when_signed_out():
    answers = [(429, {"error": "busy"}, {"Retry-After": "5"}), (401, {"error": "signed out"})]

    def handler(q, b):
        return answers.pop(0)

    server = FakeServer({("GET", "events"): handler})
    got, waits, _ = run_stream(server, max_waits=10)
    assert waits == [5]
    assert got == []


def test_stream_backs_off_when_unreachable():
    class Down(object):
        def open(self, req, data=None, timeout=None):
            raise OSError("down")

    got, waits = [], []
    stream = events.EventStream(ArcAPI("http://arc.test", token="t", opener=Down()), got.append,
                                stopped=lambda: False, wait=lambda s: waits.append(s) or len(waits) >= 4)
    stream.run()
    assert waits == list(events.BACKOFF[:4])
