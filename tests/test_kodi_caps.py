"""The thin Kodi adapter reads preferences without hardware/display capability probes."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_caps(monkeypatch, setting):
    class Addon:
        def getSettingInt(self, key):
            assert key == "max_height"
            if isinstance(setting, Exception):
                raise setting
            return setting

    monkeypatch.setitem(sys.modules, "kodi.compat", SimpleNamespace(ADDON=Addon()))
    monkeypatch.setitem(sys.modules, "kodi.log", SimpleNamespace(log=SimpleNamespace(debug=lambda *args: None)))
    path = Path(__file__).parents[1] / "resources/lib/kodi/caps.py"
    spec = importlib.util.spec_from_file_location("kodi.caps", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("height", [720, 1080, 2160])
def test_device_caps_read_selected_resolution_without_display_probes(monkeypatch, height):
    module = load_caps(monkeypatch, height)
    assert module.device_caps()["max_height"] == height
    assert "hdr_formats" not in module.device_caps()
    assert "dolby_vision_profiles" not in module.device_caps()
    assert module.device_caps(max_height=1080)["max_height"] == 1080


@pytest.mark.parametrize("setting", [0, RuntimeError("setting unavailable")])
def test_unavailable_resolution_setting_keeps_existing_default(monkeypatch, setting):
    assert load_caps(monkeypatch, setting).device_caps()["max_height"] == 2160
