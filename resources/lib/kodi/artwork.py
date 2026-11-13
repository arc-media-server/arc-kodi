"""A tiny local HTTP proxy (127.0.0.1 only) so Kodi's image loader can fetch Arc's artwork, which
needs the Bearer header Kodi's <texture> can't send. It forwards only GET image routes to Arc,
adds the header, and streams the bytes back. The session token never leaves this machine: the
proxy listens on the loopback address alone.
"""

import threading
from http import server as httpserver
from urllib import error as urlerror
from urllib import parse, request

from .log import log

# Routes that serve an image. The proxy refuses anything else, so a stray request can't reach the
# rest of the API with the token attached.
_IMAGE_PARTS = ("/images/", "/artwork", "/image", "/trickplay/", "/preroll")


def _is_image_path(path):
    return any(part in path for part in _IMAGE_PARTS)


class ArtworkProxy(object):
    def __init__(self, api):
        self.api = api
        self._server = None
        self._thread = None
        self.port = 0

    def start(self):
        if self._server is not None:
            return self.port
        api = self.api

        class Handler(httpserver.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if not _is_image_path(self.path.split("?", 1)[0]):
                    self.send_error(404)
                    return
                target = api.base_url + "/api/v1" + self.path if self.path.startswith("/") else None
                if target is None:
                    self.send_error(400)
                    return
                req = request.Request(target)
                for k, v in api.authorization.items():
                    req.add_header(k, v)
                try:
                    with request.urlopen(req, timeout=20) as resp:
                        self.send_response(resp.status)
                        ctype = resp.headers.get("Content-Type", "image/jpeg")
                        self.send_header("Content-Type", ctype)
                        self.end_headers()
                        while True:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except urlerror.HTTPError as e:
                    self.send_error(e.code)
                except Exception as e:
                    log.debug("artwork fetch failed (%s)", type(e).__name__)
                    try:
                        self.send_error(502)
                    except Exception:
                        pass

        self._server = httpserver.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, name="arc-artwork", daemon=True)
        self._thread.start()
        log.info("artwork proxy on 127.0.0.1:%d", self.port)
        return self.port

    def url_for(self, api_path):
        """A Kodi-loadable local URL for an Arc image path (/api/... or /api/v1/...)."""
        if not api_path:
            return ""
        if api_path.startswith("http://") or api_path.startswith("https://"):
            return api_path  # already absolute (rare: remote artwork redirects)
        path = api_path
        if path.startswith("/api/v1/"):
            path = path[len("/api/v1"):]
        elif path.startswith("/api/"):
            path = path[len("/api"):]
        elif not path.startswith("/"):
            path = "/" + path
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server = None
