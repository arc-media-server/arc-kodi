"""Server discovery on this device's private IPv4 /24, without credentials or Kodi."""
import ipaddress
import threading
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from .api import ArcAPI, DEFAULT_PORT

_PRIVATE = tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def candidates(address):
    try:
        ip = ipaddress.IPv4Address(address)
    except (ValueError, TypeError):
        return []
    if not any(ip in network for network in _PRIVATE):
        return []
    return [str(host) for host in ipaddress.ip_network(str(ip) + "/24", strict=False).hosts() if host != ip]


def probe(host):
    base = "http://%s:%d" % (host, DEFAULT_PORT)
    answer = ArcAPI(base, timeout=1.2).discover()
    if answer is None:
        return None
    identity = answer.get("id")
    name = answer.get("name")
    return {"id": identity if isinstance(identity, str) and identity else base,
            "name": name if isinstance(name, str) and name else host, "address": base}


def scan(address, on_found, stop, ask=probe, parallel=32):
    """Publish unique answers as they arrive; stop prevents further requests or callbacks."""
    pool = ThreadPoolExecutor(max_workers=parallel)
    hosts = iter(candidates(address))
    pending, seen = set(), set()

    def next_probe():
        host = next(hosts, None)
        if host is not None and not stop.is_set():
            pending.add(pool.submit(lambda: None if stop.is_set() else ask(host)))

    try:
        for _ in range(parallel):
            next_probe()
        while pending and not stop.is_set():
            ready, _ = wait(pending, timeout=0.05, return_when=FIRST_COMPLETED)
            for future in ready:
                pending.remove(future)
                try:
                    server = future.result()
                except Exception:
                    server = None
                if server and not stop.is_set() and server["id"] not in seen:
                    seen.add(server["id"])
                    on_found(server)
                next_probe()
    finally:
        for future in pending:
            future.cancel()
        pool.shutdown(wait=False)


class DiscoveryState:
    """A scan's cancellation and focus policy, also usable outside Kodi."""
    def __init__(self):
        self.stop = threading.Event()
        self.typing = False
        self.manual = False
        self.found = []

    def accept(self, server):
        if self.stop.is_set():
            return False
        first = not self.found
        self.found.append(server)
        return first and not self.typing and not self.manual
