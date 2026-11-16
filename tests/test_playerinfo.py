import base64
import json

from arc import playerinfo


def _record(profile, level, rpu, el, bl, compat):
    b2 = (profile << 1) | (level >> 5)
    b3 = ((level & 31) << 3) | (rpu << 2) | (el << 1) | bl
    return bytes([1, 0, b2, b3, compat << 4]) + bytes(19)


def test_dovi_config():
    c = playerinfo.dovi_config(_record(7, 6, 1, 1, 1, 6))
    assert (c["profile"], c["level"], c["rpu"], c["el"], c["bl"], c["compat"]) == (7, 6, True, True, True, 6)
    assert playerinfo.dv_profile_name(c) == "7.6"
    assert playerinfo.dv_profile_name(playerinfo.dovi_config(_record(5, 6, 1, 0, 1, 0))) == "5"
    assert playerinfo.dovi_config(b"\x01") is None


def test_sidedata():
    raw = json.dumps({"dovi.config": base64.b64encode(_record(8, 6, 1, 0, 1, 1)).decode(),
                      "flags": ["converted"], "hdr10plus": "abc"})
    sd = playerinfo.sidedata(raw)
    assert sd["dovi"]["profile"] == 8 and sd["dovi"]["compat"] == 1
    assert sd["flags"] == ["converted"] and sd["hdr10plus"] and sd["structure"] is None
    assert playerinfo.sidedata("") is None and playerinfo.sidedata("not json") is None


def test_rows_plain_kodi():
    values = {"decoder": "hevc", "width": "3840", "height": "2160", "fps": "23.976", "pixformat": "yuv420p10le",
              "hdrtype": "hdr10", "screen": "3840x2160 @ 23.98Hz - Full Screen",
              "audio_decoder": "eac3", "audio_channels": "FL,FR,FC,LFE,SL,SR", "audio_rate": "48000"}
    out = playerinfo.rows(values, hw=True, plan={"method": "direct"})
    assert ("row", "decoder", "hevc · hardware") in out
    assert ("row", "picture", "3840×2160 · 23.976 fps") in out
    assert ("row", "hdr", "HDR10") in out
    assert ("row", "output", "3840x2160 @ 23.98Hz - Full Screen") in out
    assert ("heading", "dolby_vision") not in out           # no CoreELEC side data
    assert ("row", "arc_method", "direct") in out
    assert not any(e[1] == "arc_reason" for e in out if e[0] == "row")


def test_rows_coreelec_dual_layer():
    raw = json.dumps({"dovi.config": base64.b64encode(_record(7, 6, 1, 1, 1, 6)).decode(),
                      "structure": "st-dl", "flags": []})
    values = {"decoder": "amlogic", "sidedata": raw, "aml_mode": "2160p23.976hz",
              "aml_eotf": "Dolby Vision", "aml_pixformat": "YCbCr 4:2:2 12bit", "screen": "ignored"}
    out = playerinfo.rows(values, hw=True, plan={"method": "remux", "reasons": ["container"]})
    assert ("row", "dv_profile", "7.6 · level 6") in out
    assert ("row", "dv_layers", "dual layer (one track)") in out
    assert ("row", "output", "2160p23.976hz") in out
    assert ("row", "output_format", "Dolby Vision · YCbCr 4:2:2 12bit") in out
    assert ("row", "arc_reason", "container") in out
    assert ("heading", "audio") not in out                   # nothing known: no section


def test_unknown_labels_left_out():
    # Kodi hands back the label's own text for a label it doesn't know (CoreELEC's elsewhere).
    values = {k: label for k, label in playerinfo.LABELS.items()}
    values["decoder"] = "ff-h264"
    out = playerinfo.rows(values)
    assert out == [("heading", "video"), ("row", "decoder", "ff-h264 · software")]


def test_unknowns_and_zeros_left_out():
    values = {"decoder": "ff-h264", "width": "1,280", "height": "720", "fps": "24.000", "scantype": "p",
              "deint": "unknown", "audio_decoder": "unknown", "audio_channels": "unknown",
              "audio_rate": "0", "audio_bits": "0"}
    out = playerinfo.rows(values)
    assert ("row", "picture", "1280×720 · 24.000 fps · progressive") in out
    assert not any(e[1] == "deint" for e in out)
    assert ("heading", "audio") not in out
