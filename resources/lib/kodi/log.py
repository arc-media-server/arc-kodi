"""The add-on's log (xbmc.log, prefixed [Arc]). Never logs tokens, passwords, PINs, cast links or
full URLs; name the route, as arc/api.py does."""

import logging

import xbmc


class _KodiHandler(logging.Handler):
    LEVELS = {logging.DEBUG: xbmc.LOGDEBUG, logging.INFO: xbmc.LOGINFO,
              logging.WARNING: xbmc.LOGWARNING, logging.ERROR: xbmc.LOGERROR,
              logging.CRITICAL: xbmc.LOGFATAL}

    def emit(self, record):
        try:
            xbmc.log("[Arc] " + self.format(record), self.LEVELS.get(record.levelno, xbmc.LOGINFO))
        except Exception:
            pass


def install():
    """Routes the arc/ package's `logging` through Kodi, once."""
    root = logging.getLogger("arc")
    if not any(isinstance(h, _KodiHandler) for h in root.handlers):
        handler = _KodiHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        root.propagate = False
    return root


log = logging.getLogger("arc.kodi")
