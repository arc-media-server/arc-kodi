"""Live updates in Kodi: one thread keeps Arc's change-hint stream open (arc/events.py), another
hands the merged changes to the app about once a second. Started once Home opens, stopped on sign
out, a profile switch and exit. Kodi waits for an add-on's threads before ending it, so stop()
cuts the stream's read short rather than waiting for its timeout."""

import threading

import xbmc

from arc import events

from .log import log

TICK = 0.25   # seconds between looks for a gathered change


class Live(object):
    def __init__(self, session, deliver):
        self.session = session
        self.deliver = deliver
        self.stream = None
        self.threads = []
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._gatherer = events.Gatherer()

    @property
    def running(self):
        return any(t.is_alive() for t in self.threads)

    def start(self):
        if self.running:
            return
        self._stop = threading.Event()
        self._gatherer = events.Gatherer()
        stop = self._stop
        monitor = xbmc.Monitor()

        def wait(seconds):
            waited = 0.0
            while waited < seconds:
                if stop.wait(TICK) or monitor.abortRequested():
                    return True
                waited += TICK
            return False

        def add(change):
            with self._lock:
                self._gatherer.add(change)

        self.stream = events.EventStream(self.session.api, add, stopped=lambda: stop.is_set() or monitor.abortRequested(),
                                         wait=wait)
        self.threads = [threading.Thread(target=self._read, args=(self.stream,), daemon=True),
                        threading.Thread(target=self._hand_over, args=(stop, monitor), daemon=True)]
        for t in self.threads:
            t.start()

    def stop(self):
        if not self.threads:
            return
        self._stop.set()
        if self.stream is not None:
            self.stream.abort()
        for t in self.threads:
            t.join(2.0)
        self.threads = []
        self.stream = None

    def _read(self, stream):
        try:
            stream.run()
        except Exception as e:
            log.warning("live updates failed: %s", type(e).__name__)

    def _hand_over(self, stop, monitor):
        while not stop.wait(TICK) and not monitor.abortRequested():
            with self._lock:
                change = self._gatherer.take()
            if change is None:
                continue
            try:
                self.deliver(change)
            except Exception as e:
                log.error("live update failed: %s", e)
