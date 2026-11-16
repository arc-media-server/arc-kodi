"""Player Info: what Kodi's player reports live about what's playing (as Kodi's Player Process
Info, and on CoreELEC its extra display and Dolby Vision values), worded for Arc's own panel.
Plain Python: kodi/player_osd.py reads the labels and draws the rows.

CoreELEC's extra labels are its own (xbmc/guilib/guiinfo/CEGUIInfoLabels.dox in CoreELEC/xbmc):
amlogic.displaymode, amlogic.pixformat and amlogic.eoft_gamut (what the TV is sent),
audiochannelssink, and on newer builds video.sidedata (the Dolby Vision and HDR metadata of
the frame on screen, as JSON with base64 payloads). Builds without them leave those rows out."""

import base64
import json

# Kodi's labels this reads (the strings go to xbmc.getInfoLabel as they are).
LABELS = {
    "decoder": "Player.Process(videodecoder)",
    "pixformat": "Player.Process(pixformat)",
    "width": "Player.Process(videowidth)",
    "height": "Player.Process(videoheight)",
    "fps": "Player.Process(videofps)",
    "scantype": "Player.Process(videoscantype)",
    "deint": "Player.Process(deintmethod)",
    "hdrtype": "VideoPlayer.HdrType",
    "aml_mode": "Player.Process(amlogic.displaymode)",
    "aml_pixformat": "Player.Process(amlogic.pixformat)",
    "aml_eotf": "Player.Process(amlogic.eoft_gamut)",
    "screen": "System.ScreenResolution",
    "sidedata": "Player.Process(video.sidedata)",
    "audio_decoder": "Player.Process(audiodecoder)",
    "audio_channels": "Player.Process(audiochannels)",
    "audio_rate": "Player.Process(audiosamplerate)",
    "audio_bits": "Player.Process(audiobitspersample)",
    "audio_sink": "Player.Process(audiochannelssink)",
}
# Kodi's conditions this reads (xbmc.getCondVisibility).
CONDITIONS = {"hw": "Player.Process(videohwdecoder)"}

HDR_NAMES = {"dolbyvision": "Dolby Vision", "hdr10": "HDR10", "hdr10+": "HDR10+", "hdr10plus": "HDR10+",
             "hlg": "HLG", "sdr": "SDR"}
DV_FLAGS = {"converted": "converted", "rpu-removed": "RPU removed", "hdr10plus-removed": "HDR10+ removed",
            "l5-zeroed": "L5 zeroed"}


def dovi_config(record):
    """The Dolby Vision configuration record (dvcC/dvvC, 24 bytes): its profile, level, which
    layers there are and the base layer's compatibility. None if it isn't one."""
    if not isinstance(record, (bytes, bytearray)) or len(record) < 5:
        return None
    b = record
    return {
        "version": "%d.%d" % (b[0], b[1]),
        "profile": b[2] >> 1,
        "level": ((b[2] & 1) << 5) | (b[3] >> 3),
        "rpu": bool(b[3] & 4),
        "el": bool(b[3] & 2),
        "bl": bool(b[3] & 1),
        "compat": b[4] >> 4,
    }


def sidedata(raw):
    """CoreELEC's video.sidedata, read: {"dovi": config or None, "hdr10plus": bool,
    "structure": "st-dl"/"dt-dl"/None, "flags": [...]}; None when there's nothing (other builds,
    or a stream without metadata)."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    dovi = None
    if isinstance(data.get("dovi.config"), str):
        try:
            dovi = dovi_config(base64.b64decode(data["dovi.config"]))
        except (ValueError, TypeError):
            dovi = None
    flags = data.get("flags") if isinstance(data.get("flags"), list) else []
    return {"dovi": dovi, "hdr10plus": bool(data.get("hdr10plus")),
            "structure": data.get("structure") if data.get("structure") in ("st-dl", "dt-dl") else None,
            "flags": [f for f in flags if isinstance(f, str)]}


def dv_profile_name(dovi):
    """"Profile 8.1", "Profile 7.6", "Profile 5"."""
    if not dovi:
        return ""
    compat = dovi.get("compat") or 0
    return ("%d.%d" % (dovi["profile"], compat)) if compat else str(dovi["profile"])


def known(value, label):
    """A label's answer, or "" when Kodi didn't know the label: it then hands back the label's
    own text (CoreELEC's labels on other builds)."""
    value = (value or "").strip()
    if not value or value.lower() == label.lower() or value.lower() == "unknown":
        return ""
    return "" if value.replace("0", "").replace(".", "").replace(",", "") == "" else value  # 0, 0.000


def _join(*bits):
    return " · ".join(b for b in bits if b)


def rows(values, hw=False, plan=None):
    """The panel's entries, top to bottom: ("heading", key) and ("row", key, value). `values` are
    LABELS' answers by key (empty when Kodi doesn't know them). Rows with nothing to say are left
    out, and so is a section left empty."""
    v = {k: known(values.get(k), LABELS[k]) for k in LABELS}
    out = []

    def section(key, entries):
        entries = [(k, val) for k, val in entries if val]
        if entries:
            out.append(("heading", key))
            out.extend(("row", k, val) for k, val in entries)

    size = "%s×%s" % (v["width"].replace(",", ""), v["height"].replace(",", "")) if v["width"] and v["height"] else ""
    scan = {"p": "progressive", "i": "interlaced"}.get(v["scantype"].lower(), v["scantype"])
    fps = ("%s fps" % v["fps"]) if v["fps"] else ""
    decoder = _join(v["decoder"], ("hardware" if hw else "software") if v["decoder"] else "")
    hdr = HDR_NAMES.get(v["hdrtype"].lower(), v["hdrtype"]) if v["hdrtype"] else ""
    section("video", [("decoder", decoder), ("picture", _join(size, fps, scan)),
                      ("pixformat", v["pixformat"]), ("hdr", hdr),
                      ("deint", v["deint"] if v["deint"] and v["deint"].lower() not in ("none", "") else "")])

    sd = sidedata(v["sidedata"])
    dovi = (sd or {}).get("dovi")
    if dovi:
        layers = "dual layer" if dovi["el"] else "single layer"
        if dovi["el"] and sd.get("structure"):
            layers += " (%s)" % ("one track" if sd["structure"] == "st-dl" else "two tracks")
        section("dolby_vision", [("dv_profile", _join(dv_profile_name(dovi), "level %d" % dovi["level"])),
                                 ("dv_layers", layers),
                                 ("dv_changed", ", ".join(DV_FLAGS.get(f, f) for f in sd["flags"]))])

    display = v["aml_mode"] or v["screen"]
    section("display", [("output", display), ("output_format", _join(v["aml_eotf"], v["aml_pixformat"]))])

    audio_in = _join(v["audio_decoder"], v["audio_channels"])
    audio_fmt = _join(("%s Hz" % v["audio_rate"]) if v["audio_rate"] else "",
                      ("%s bit" % v["audio_bits"]) if v["audio_bits"] else "")
    section("audio", [("audio_decoder", audio_in), ("audio_format", audio_fmt), ("audio_sink", v["audio_sink"])])

    if plan:
        method = plan.get("method") or ""   # "direct", "remux" or "transcode": the Kodi side words it
        reasons = [r for r in plan.get("reasons") or [] if isinstance(r, str)]
        section("arc", [("arc_method", method), ("arc_reason", reasons[0] if reasons and method != "direct" else "")])
    return out
