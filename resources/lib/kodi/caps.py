"""What this Kodi device can play, as Arc's playback decision expects it. Starts from the common
set in arc/playback.py and narrows/widens it with what Kodi reports: the display's HDR, and the
settings for passthrough. Real passthrough/HDR/refresh checks need hardware (never marked done
without it, per CLAUDE.md)."""

import json

import xbmc

from arc import playback
from .log import log


def _setting_bool(key):
    try:
        return xbmc.getCondVisibility("System.GetBool(%s)" % key)
    except Exception:
        return False


def _hdr_formats():
    """The display's HDR, from Kodi's System.HDRType (Kodi 20+); empty when SDR or unknown."""
    try:
        hdr = xbmc.getInfoLabel("System.HDRType") or ""
    except Exception:
        hdr = ""
    hdr = hdr.lower()
    out = []
    if "dolby" in hdr:
        out.append("dolby_vision")
    if "hdr10+" in hdr or "hdr10plus" in hdr:
        out.append("hdr10_plus")
    if "hdr10" in hdr:
        out.append("hdr10")
    if "hlg" in hdr:
        out.append("hlg")
    return out


def device_caps(max_height=2160):
    """The caps Kodi sends with a playback request."""
    caps = {
        "containers": list(playback.BASE_CAPS["containers"]),
        "video": list(playback.BASE_CAPS["video"]),
        "audio": list(playback.BASE_CAPS["audio"]),
        "max_height": max_height,
    }
    # Passthrough: formats the receiver decodes itself, usable only for direct files.
    passthrough = []
    for codec, key in (("ac3", "audiooutput.ac3passthrough"), ("eac3", "audiooutput.eac3passthrough"),
                       ("dts", "audiooutput.dtspassthrough"), ("truehd", "audiooutput.truehdpassthrough"),
                       ("dts", "audiooutput.dtshdpassthrough")):
        if _setting_bool(key) and codec not in passthrough:
            passthrough.append(codec)
    if passthrough:
        caps["audio_passthrough"] = passthrough
    hdr = _hdr_formats()
    if hdr:
        caps["hdr_formats"] = hdr
        if "dolby_vision" in hdr:
            # Arc tags copied HEVC as hvc1, which suits DV profile 8's HDR10 base (as on Apple TV).
            caps["dolby_vision_profiles"] = [8]
        caps["max_bit_depth"] = 10
    log.debug("device caps: height<=%d, hdr=%s, passthrough=%s", max_height, ",".join(hdr) or "-",
              ",".join(passthrough) or "-")
    return caps
