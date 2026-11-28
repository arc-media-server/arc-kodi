"""A bounded journal of fixed app events, never raw Kodi log text."""
from collections import deque
import json
from pathlib import Path
from threading import RLock
import time

_EVENTS = {
    "app_started", "profile_picker", "automatic_sign_in", "sign_in_failed", "request_failed",
    "session_expired", "playback_requested", "playback_started", "playback_failed",
    "detailed_logging_enabled", "detailed_logging_expired", "crash_detected",
}
_LEVELS = {"debug", "info", "warn", "error"}


def _entry(value):
    if not isinstance(value, dict):
        return None
    event, level, stamp = value.get("event"), value.get("level"), value.get("time_ms")
    if (isinstance(event, str) and event in _EVENTS and isinstance(level, str) and level in _LEVELS
            and type(stamp) is int and 0 < stamp < 253402300800000):
        return {"event": event, "level": level, "time_ms": stamp}
    return None


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = RLock()
        self.entries = deque(maxlen=3000)
        self.until = 0
        self.crash = False
        self._last_write = float("-inf")
        try:
            with self.path.open(encoding="utf-8") as handle:
                saved = json.loads(handle.read(256 * 1024))
            for raw in saved["entries"]:
                item = _entry(raw)
                if item:
                    self.entries.append(item)
            self.until = int(saved.get("until", 0))
            self.crash = saved.get("crash") is True
        except (OSError, TypeError, ValueError, KeyError):
            pass

    def flush(self):
        with self.lock:
            try:
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps({"entries": list(self.entries), "until": self.until,
                                          "crash": self.crash}, separators=(",", ":")), encoding="utf-8")
                tmp.replace(self.path)
                self._last_write = time.monotonic()
            except OSError:
                pass

    def detailed(self):
        with self.lock:
            if self.until and self.until <= time.time():
                self.until = 0
                self.record("info", "detailed_logging_expired")
                self.flush()
            return bool(self.until)

    def toggle(self):
        with self.lock:
            self.until = 0 if self.detailed() else int(time.time()) + 7200
            if self.until:
                self.record("info", "detailed_logging_enabled")
            self.flush()

    def record(self, level, event):
        item = _entry({"event": event, "level": level, "time_ms": int(time.time() * 1000)})
        with self.lock:
            if not item or (level == "debug" and not self.detailed()):
                return
            self.entries.append(item)
            if time.monotonic() - self._last_write > 5:
                self.flush()

    def payload(self):
        with self.lock:
            return {"platform": "kodi", "entries": list(self.entries)}

    def set_crash(self, pending):
        with self.lock:
            self.crash = pending
            if pending:
                self.record("error", "crash_detected")
            self.flush()

    def clear(self):
        with self.lock:
            self.entries.clear()
            self.until = 0
            self.crash = False
            self.flush()


# Translate known Arc log templates only. Logging args can contain personal data and are never read.
def kodi_event(message, status=None):
    if message == "starting at Who's watching":
        return "info", "profile_picker"
    if message == "signing in automatically as the saved profile":
        return "info", "automatic_sign_in"
    if message == "automatic profile sign-in failed (HTTP %s)":
        return "warn", "sign_in_failed"
    if message == "playback request failed (%s)":
        return "error", "playback_failed"
    if message == "playback started (%s)":
        return "debug", "playback_started"
    if message == "playing %s: %s":
        return "info", "playback_requested"
    if message == "%s: can't reach the server (%s)" or message == "unexpected answer from %s: %s":
        return "warn", "request_failed"
    if message == "%s failed: %d %s":
        if status == 401:
            return "warn", "session_expired"
        if isinstance(status, int) and status >= 500:
            return "warn", "request_failed"
    return None
