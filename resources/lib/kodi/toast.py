"""Arc's toast: a short message at the top right of whichever Arc window is showing, in place of
Kodi's notification. It never takes the focus. The skin draws it (the ArcToast include, in every
window but the player, which has its own notice) while the global property arc.toast has words;
this sets them and clears them after a few seconds, unless a newer message has replaced them."""

import threading

import xbmcgui

SHOWN_FOR = 4.0   # seconds
HOME = 10000      # Kodi's Home window holds global properties
_lock = threading.Lock()
_latest = [0]
_closing = threading.Event()   # set when the add-on closes: wakes the timers (Kodi waits for them)


def show(text):
    if not text:
        return
    with _lock:
        _latest[0] += 1
        mine = _latest[0]
    xbmcgui.Window(HOME).setProperty("arc.toast", text)

    def expire():
        if _closing.wait(SHOWN_FOR):
            return
        with _lock:
            if _latest[0] != mine:
                return  # a newer message is showing
        xbmcgui.Window(HOME).clearProperty("arc.toast")

    threading.Thread(target=expire, daemon=True).start()


def close():
    """Gone at once, and no timer left waiting: the add-on is closing."""
    _closing.set()
    xbmcgui.Window(HOME).clearProperty("arc.toast")
