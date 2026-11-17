"""Stand-ins only: these tests never probe the machine's LAN."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from arc.api import ArcAPI
from arc.discovery import DiscoveryState, candidates, scan


@pytest.mark.parametrize("ip", ["8.8.8.8", "127.0.0.1", "169.254.1.2", "100.64.1.2", "172.32.0.1", "::1", "bad", None])
def test_no_scan_outside_private_ipv4(ip):
    assert candidates(ip) == []


@pytest.mark.parametrize("ip", ["10.11.12.50", "172.16.1.50", "172.31.1.50", "192.168.1.50"])
def test_candidates_only_own_24_without_self_network_broadcast(ip):
    hosts = candidates(ip)
    prefix = ip.rsplit(".", 1)[0]
    assert len(hosts) == 253
    assert ip not in hosts
    assert all(h.startswith(prefix + ".") for h in hosts)
    assert prefix + ".0" not in hosts and prefix + ".255" not in hosts


def test_scan_deduplicates_and_repeats():
    for _ in range(3):
        found = []
        def ask(host):
            return {"id": "same", "address": host, "name": "Fixture"}
        scan("192.168.1.10", found.append, threading.Event(), ask=ask)
        assert len(found) == 1


def test_cancel_prevents_more_probes_and_callbacks():
    stop = threading.Event()
    started = []
    def ask(host):
        started.append(host)
        return {"id": host}
    found = []
    def accept(server):
        found.append(server)
        stop.set()
    scan("10.1.2.3", accept, stop, ask=ask, parallel=1)
    assert len(found) == len(started) == 1
    scan("10.1.2.3", accept, stop, ask=ask)
    assert len(started) == 1


def test_focus_first_unless_typing_or_manual_and_ignore_cancelled_results():
    state = DiscoveryState()
    assert state.accept({"id": "first"})
    assert not state.accept({"id": "second"})
    for attr in ("typing", "manual"):
        state = DiscoveryState()
        setattr(state, attr, True)
        assert not state.accept({"id": "first"})
        setattr(state, attr, False)
        assert not state.accept({"id": "second"})
    state.stop.set()
    before = list(state.found)
    assert not state.accept({"id": "late"})
    assert state.found == before


def test_anonymous_discover_against_standin_server():
    requests = []
    class Handler(BaseHTTPRequestHandler):
        answer = {"product": "arc", "api_version": 1, "id": "fixture", "name": "Fixture", "future": True}
        status = 200
        def do_GET(self):
            requests.append((self.path, self.headers.get("Authorization")))
            self.send_response(self.status)
            self.end_headers()
            self.wfile.write(json.dumps(self.answer).encode())
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        api = ArcAPI("http://127.0.0.1:%d" % server.server_port, token="must-not-send", timeout=1)
        assert api.discover()["id"] == "fixture"
        for answer in ({"product": "other", "api_version": 1}, {"product": "arc"},
                       {"product": "arc", "api_version": True}, [], None):
            Handler.answer = answer
            assert api.discover() is None
        Handler.status = 404
        assert api.discover() is None
        assert requests and all(path == "/api/v1/discover" and auth is None for path, auth in requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_probe_default_port_validation_and_name_fallback(monkeypatch):
    from arc import discovery
    calls = []
    class API:
        def __init__(self, base, timeout):
            calls.append((base, timeout))
        def discover(self):
            return {"id": [], "name": None}
    monkeypatch.setattr(discovery, "ArcAPI", API)
    found = discovery.probe("192.168.1.12")
    assert calls == [("http://192.168.1.12:8099", 1.2)]
    assert found == {"id": "http://192.168.1.12:8099", "name": "192.168.1.12", "address": "http://192.168.1.12:8099"}


def test_scan_network_failure_and_non_arc_do_not_stop_other_results():
    found = []
    def ask(host):
        if host.endswith(".1"):
            raise OSError("fixture failure")
        if host.endswith(".2"):
            return {"id": "fixture"}
        return None
    scan("192.168.1.3", found.append, threading.Event(), ask=ask)
    assert found == [{"id": "fixture"}]
