"""Theme selection and real loopback delivery against a stand-in Arc."""
import importlib.util
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib import request, error

import pytest

from arc import settings
from arc.thememusic import theme_path


def test_selection_and_settings():
    movie = {"kind": "movie", "theme_url": "/api/items/abc/theme"}
    assert theme_path(movie, {}) == movie["theme_url"]
    assert theme_path(dict(movie, theme_url=movie["theme_url"] + "?v=123"), {}) == movie["theme_url"] + "?v=123"
    assert theme_path(movie, {"theme_music": False}) is None
    assert theme_path(dict(movie, kind="series"), {}) == movie["theme_url"]
    assert theme_path(dict(movie, kind="episode"), {}) is None
    for url in ("", "https://other.invalid/api/items/abc/theme", "/api/items/abc/stream", "/api/items/abc/theme?x=1"):
        assert theme_path(dict(movie, theme_url=url), {}) is None
    assert settings.value({}, "theme_music") is True
    assert settings.change({}, "theme_music") == {"theme_music": False}
    assert settings.rows().index("theme_music") == settings.rows().index("auto_skip") + 1


def test_authenticated_loopback_theme_delivery(monkeypatch):
    seen = []

    class Arc(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            seen.append((self.path, self.headers.get("Authorization")))
            if self.path.endswith("?v=redirect"):
                self.send_response(302)
                self.send_header("Location", "/forbidden-redirect")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            self.wfile.write(b"test theme bytes")

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Arc)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    monkeypatch.setitem(sys.modules, "kodi.log", SimpleNamespace(log=logging.getLogger("test")))
    path = Path(__file__).parents[1] / "resources/lib/kodi/artwork.py"
    spec = importlib.util.spec_from_file_location("kodi.artwork_theme_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    api = SimpleNamespace(base_url="http://127.0.0.1:%d" % upstream.server_port,
                          authorization={"Authorization": "Bearer scratch-only"})
    proxy = module.ArtworkProxy(api)
    proxy.start()
    try:
        for _ in range(2):
            url = proxy.url_for("/api/items/abc/theme")
            assert "scratch-only" not in url
            with request.urlopen(url) as res:
                assert res.headers["Content-Type"] == "audio/mpeg"
                assert res.read() == b"test theme bytes"
        with pytest.raises(error.HTTPError) as denied:
            request.urlopen(proxy.url_for("/api/items/abc/stream"))
        assert denied.value.code == 404
        assert seen == [("/api/v1/items/abc/theme", "Bearer scratch-only")] * 2
        with request.urlopen(proxy.url_for("/api/v1/items/abc/theme?v=123")) as res:
            assert res.read() == b"test theme bytes"
        with pytest.raises(error.HTTPError) as refused:
            request.urlopen(proxy.url_for("/api/items/abc/theme?v=redirect"))
        assert refused.value.code == 302
        assert refused.value.headers.get("Location") is None
        assert seen[-1][0] == "/api/v1/items/abc/theme?v=redirect"
        assert not any(path == "/forbidden-redirect" for path, _ in seen)
    finally:
        proxy.stop()
        upstream.shutdown()
        upstream.server_close()


def test_native_theme_ownership_and_delayed_navigation(monkeypatch):
    class Player:
        def __init__(self):
            self.playing = False
            self.file = ""
            self.starts = 0
            self.stops = 0

        def isPlaying(self):
            return self.playing

        def getPlayingFile(self):
            return self.file

        def play(self, url, windowed=False):
            assert windowed
            self.file = url
            self.starts += 1

        def stop(self):
            self.stops += 1

    monkeypatch.setitem(sys.modules, "xbmc", SimpleNamespace(Player=Player, getCondVisibility=lambda _: False))
    monkeypatch.setitem(sys.modules, "xbmcgui", SimpleNamespace(getCurrentWindowId=lambda: 42))
    monkeypatch.setitem(sys.modules, "kodi.log", SimpleNamespace(log=logging.getLogger("test")))
    spec = importlib.util.spec_from_file_location("kodi.theme_ownership_test", Path(__file__).parents[1] / "resources/lib/kodi/thememusic.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod.threading, "Thread", lambda **kwargs: SimpleNamespace(start=lambda: None))
    session = SimpleNamespace(prefs={}, artwork=SimpleNamespace(url_for=lambda path: "http://127.0.0.1:1234" + path))
    tune = mod.ThemeMusic(SimpleNamespace(session=session, _closing=False))
    tune.window_id = 42
    item = {"kind": "movie", "theme_url": "/api/items/abc/theme"}
    tune.start(item)
    tune.start(item)
    assert tune.player.starts == 1
    tune.stop()
    assert tune.player.stops == 1
    tune.start(item)
    assert tune.player.starts == 1
    # Native play is asynchronous: a cancelled tune may finish opening after stop().
    tune.player.playing = True
    tune.player.file = tune.url
    tune.player.onAVStarted()
    assert tune.player.stops == 2
    tune.player.file = "another-source"
    tune.player.onAVStarted()
    tune.stop()
    assert tune.player.stops == 2


@pytest.mark.parametrize("reason", ["closing", "navigation", "screensaver", "display_sleep", "dialog", "abort"])
def test_native_theme_stops_when_page_is_inactive(monkeypatch, reason):
    stopped = []
    module_name = "kodi.theme_lifecycle_test"
    window = SimpleNamespace(_closing=reason == "closing")
    waits = []
    def wait(_):
        waits.append(True)
        assert len(waits) == 1, "Inactive page did not stop its theme"
        return reason == "abort"
    monkeypatch.setitem(sys.modules, "xbmc", SimpleNamespace(
        Player=object, Monitor=lambda: SimpleNamespace(waitForAbort=wait),
        getCondVisibility=lambda key: key == {
            "screensaver": "System.ScreenSaverActive", "display_sleep": "System.DPMSActive",
            "dialog": "System.HasActiveModalDialog"
        }.get(reason)))
    monkeypatch.setitem(sys.modules, "xbmcgui", SimpleNamespace(
        getCurrentWindowId=lambda: 43 if reason == "navigation" else 42))
    monkeypatch.setitem(sys.modules, "kodi.log", SimpleNamespace(log=logging.getLogger("test")))
    spec = importlib.util.spec_from_file_location(module_name,
        Path(__file__).parents[1] / "resources/lib/kodi/thememusic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tune = object.__new__(module.ThemeMusic)
    tune.window = window
    tune.window_id = 42
    tune.stopped = False
    tune.stop = lambda: stopped.append(True)
    tune._watch()
    assert stopped == [True]
