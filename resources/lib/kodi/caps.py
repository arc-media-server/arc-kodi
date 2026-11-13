"""Kodi-managed source playback, with the add-on's chosen resolution limit.

Do not infer accepted source formats from the display or passthrough switches. Kodi owns
software/hardware decoding, HDR/Dolby Vision compatibility, tone mapping and audio output.
"""

from arc import playback
from .compat import ADDON
from .log import log


def device_caps(max_height=None):
    """Build the request policy without probing or certifying this device's output."""
    if max_height is None:
        try:
            max_height = ADDON.getSettingInt("max_height") or 2160
        except Exception:
            max_height = 2160
    caps = playback.kodi_caps(max_height)
    log.debug("Kodi-managed playback: height limit=%d", max_height)
    return caps
