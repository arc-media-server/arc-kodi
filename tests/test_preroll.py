"""Pre-roll API, deadline and real Kodi adapter with platform stand-ins."""
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock
from arc.api import ArcAPI
from arc.preroll import clips_before_deadline, enabled
from fake_server import FakeServer


def test_list_route_authorization_and_order():
    clips = [{"url": "/api/preroll/0", "unknown": True}, {"url": "/api/preroll/1"}]
    server = FakeServer({("GET", "items/m%201/preroll"): (200, clips)})
    api = ArcAPI("http://arc:8099", token="fixture", opener=server)
    assert api.preroll("m 1") == clips
    assert server.requests[0]["auth"] == "Bearer fixture"


def test_empty_failed_and_malformed_lists_never_block():
    assert clips_before_deadline(lambda: []) == ([], "ready")
    assert clips_before_deadline(lambda: {}) == ([], "failed")
    def fails():
        raise OSError("fixture")
    assert clips_before_deadline(fails) == ([], "failed")
    assert clips_before_deadline(lambda: [{"url": "a"}, {}, {"url": 4}, {"url": "b"}]) == ([{"url": "a"}, {"url": "b"}], "ready")


def test_deadline_ignores_late_network_result():
    release = threading.Event()
    def late():
        release.wait(1)
        return [{"url": "late"}]
    start = time.monotonic()
    assert clips_before_deadline(late, seconds=.025) == ([], "timeout")
    assert time.monotonic() - start < .5
    release.set()


def test_only_initial_film_from_beginning():
    assert enabled({"kind": "movie"})
    assert not enabled({"kind": "movie"}, resume_ms=1)
    assert not enabled({"kind": "movie"}, together=True)
    assert not enabled({"kind": "episode"})
    assert not enabled({"kind": "extra"})


def load_player(monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    monkeypatch.setitem(sys.modules, "xbmc", SimpleNamespace(Player=object))
    monkeypatch.setitem(sys.modules, "xbmcgui", SimpleNamespace(ListItem=lambda: Mock()))
    for name in ("toast", "storage"):
        monkeypatch.setitem(sys.modules, "kodi." + name, SimpleNamespace())
    monkeypatch.setitem(sys.modules, "kodi.compat", SimpleNamespace(T=lambda n: str(n)))
    monkeypatch.setitem(sys.modules, "kodi.caps", SimpleNamespace(device_caps=lambda: {}))
    monkeypatch.setitem(sys.modules, "kodi.log", SimpleNamespace(log=Mock()))
    spec = importlib.util.spec_from_file_location("kodi.player", Path(__file__).parents[1] / "resources/lib/kodi/player.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adapter_clip_error_skip_end_late_stop_and_back(monkeypatch):
    module = load_player(monkeypatch)
    pb = module.Playback.__new__(module.Playback)
    pb.done = False
    pb._stop = threading.Event()
    pb.preroll_pending = False
    pb.preroll_active = True
    pb._preroll_clips = [{"url": "first"}, {"url": "second"}, {"url": "third"}]
    pb._preroll_index = -1
    pb._preroll_lock = threading.Lock()
    pb.controls = Mock()
    pb.player = Mock()
    pb.api = SimpleNamespace(cast_link=lambda url: url)
    pb._start_film = Mock(return_value=True)
    pb.advance_preroll()
    assert pb.player.play.call_args.args[0] == "first"
    pb.on_started()
    pb.on_ended(finished=False)  # Late replaced-clip Stop after AVStarted.
    assert not pb._stop.is_set()
    pb.on_error()
    assert pb.player.play.call_args.args[0] == "second"
    pb.advance_preroll()
    assert pb.player.play.call_args.args[0] == "third"
    pb.on_started()
    pb.on_ended(finished=True)
    pb._start_film.assert_called_once()
    assert not pb.preroll_active
    pb.advance_preroll()  # Late duplicate Skip cannot start film twice.
    pb._start_film.assert_called_once()
    pb.preroll_active = True
    pb._finish = Mock()
    pb._stop.set()
    pb.on_ended(finished=False)
    pb._finish.assert_called_once()
    pb._start_film.assert_called_once()


def test_adapter_resume_and_room_start_film_directly(monkeypatch):
    module = load_player(monkeypatch)
    for resume, together in ((1, None), (0, object())):
        pb = module.Playback.__new__(module.Playback)
        pb.item = {"kind": "movie"}
        pb.resume_ms = resume
        pb.together = together
        pb._start_film = Mock(return_value=True)
        assert pb.start()
        pb._start_film.assert_called_once()


def test_film_request_failure_after_preroll_from_worker(monkeypatch):
    module = load_player(monkeypatch)
    monkeypatch.setattr(module.toast, "show", lambda text: None, raising=False)
    pb = module.Playback.__new__(module.Playback)
    pb.done = False
    pb._stop = threading.Event()
    pb.resume_ms = 0
    pb.caps = {}
    pb.file_id = pb.audio_index = pb.max_kbps = pb.burn_subtitle = None
    pb.item_id = "fixture"
    pb._choose_start_audio = Mock()
    pb.api = SimpleNamespace(start_playback=Mock(side_effect=OSError("fixture failure")))
    pb._finish = Mock()
    results = []
    worker = threading.Thread(target=lambda: results.append(pb._start_film()))
    worker.start()
    worker.join(timeout=1)
    assert not worker.is_alive()
    assert results == [False]
    assert pb._stop.is_set()
    pb._finish.assert_called_once()


def test_late_clip_start_after_back_stops_only_its_own_source(monkeypatch):
    module = load_player(monkeypatch)
    for done in (False, True):
        pb = SimpleNamespace(done=done, _stop=threading.Event(), _preroll_url="clip-grant", on_started=Mock())
        pb._stop.set()
        player = module.ArcPlayer(pb)
        player.getPlayingFile = Mock(return_value="clip-grant")
        player.stop = Mock()
        player.onAVStarted()
        player.stop.assert_called_once()
        pb.on_started.assert_not_called()
        player.getPlayingFile.return_value = "another-title"
        player.onAVStarted()
        player.stop.assert_called_once()


def test_optional_clip_error_dialog_does_not_block_next_clip(monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    load_player(monkeypatch)
    execute = Mock()
    monkeypatch.setitem(sys.modules, "xbmc", SimpleNamespace(
        getCondVisibility=lambda condition: condition == "Window.IsVisible(okdialog)",
        executebuiltin=execute))
    monkeypatch.setitem(sys.modules, "xbmcgui", SimpleNamespace(WindowXMLDialog=object))
    monkeypatch.setitem(sys.modules, "kodi.compat", SimpleNamespace(ADDON_PATH="", T=str))
    spec = importlib.util.spec_from_file_location("kodi.preroll_osd_test",
        Path(__file__).parents[1] / "resources/lib/kodi/player_osd.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    controls = object.__new__(module.PlayerControls)
    controls.pb = SimpleNamespace(preroll_pending=False, preroll_active=True, _started=False)
    controls._close_kodi_dialogs()
    execute.assert_called_once_with("Dialog.Close(okdialog,true)")
    execute.reset_mock()
    controls.pb.preroll_active = False
    controls._close_kodi_dialogs()
    execute.assert_not_called()  # The film's own error is not dismissed.


def test_stopped_failed_clip_advances_but_replacement_stop_is_ignored(monkeypatch):
    module = load_player(monkeypatch)
    pb = module.Playback.__new__(module.Playback)
    pb._stop = threading.Event()
    pb._preroll_index = 0
    pb.preroll_active = True
    pb.preroll_pending = False
    pb._switching = True
    pb._preroll_replacing = False
    pb.player = Mock()
    pb.player.isPlaying.return_value = False
    pb.advance_preroll = Mock()
    pb._finish = Mock()
    pb.on_ended(False)  # Kodi can signal an unreadable clip with Stopped, not Error.
    pb.advance_preroll.assert_called_once()
    pb._finish.assert_not_called()
    pb.advance_preroll.reset_mock()
    pb._preroll_replacing = True
    pb.on_ended(False)  # Stop for a clip explicitly replaced by Skip.
    pb.advance_preroll.assert_not_called()
    assert not pb._preroll_replacing
    pb.on_ended(False)  # The replacement itself then fails.
    pb.advance_preroll.assert_called_once()


def test_queue_advancement_does_not_fetch_or_start_prerolls(monkeypatch):
    module = load_player(monkeypatch)
    monkeypatch.setattr(module.threading, "Thread", Mock(return_value=Mock()))
    pb = module.Playback.__new__(module.Playback)
    pb._stop = threading.Event()
    pb.api = SimpleNamespace(preroll=Mock())
    pb.start = Mock(side_effect=AssertionError("queue must not re-enter initial play"))
    pb._request = Mock(return_value=True)
    pb._open_player = Mock()
    assert pb._switch_to({"id": "next-film", "kind": "movie"})
    pb._request.assert_called_once_with(0)
    pb._open_player.assert_called_once()
    pb.start.assert_not_called()
    pb.api.preroll.assert_not_called()
