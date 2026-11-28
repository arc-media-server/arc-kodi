import json

from arc.device_logs import Journal, kodi_event


def test_device_logs_project_known_arc_events_without_credentials(tmp_path):
    path = tmp_path / "arc-logs.json"
    url = "https://private.test/cast?token=secret-fixture&pin=1234"
    valid = {"event": "request_failed", "level": "warn", "time_ms": 1795420800000, "url": url}
    path.write_text(json.dumps({"entries": [valid, dict(valid, event=url)]}))
    journal = Journal(path)
    journal.record("debug", "playback_started")
    assert len(journal.payload()["entries"]) == 1
    assert "private.test" not in json.dumps(journal.payload())
    assert kodi_event("password " + url) is None
    journal.toggle()
    journal.record("debug", "playback_started")
    assert journal.payload()["entries"][-1]["event"] == "playback_started"
    journal.set_crash(True)
    assert Journal(path).crash
    journal.clear()
    assert not Journal(path).payload()["entries"]
