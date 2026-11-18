"""A tiny local HTTP proxy (127.0.0.1 only) so Kodi's image loader can fetch Arc's artwork, which
needs the Bearer header Kodi's <texture> can't send. It forwards only GET image routes to Arc,
adds the header, and streams the bytes back. The session token never leaves this machine: the
proxy listens on the loopback address alone.
"""

import threading
from http import server as httpserver
from urllib import error as urlerror
from urllib import parse, request

from arc.thememusic import is_theme_path
from .log import log

# Routes that serve an image. The proxy refuses anything else, so a stray request can't reach the
# rest of the API with the token attached.
_IMAGE_PARTS = ("/images/", "/artwork", "/image", "/trickplay/", "/preroll")


def _is_image_path(path):
    return any(part in path for part in _IMAGE_PARTS)


# Theme music never follows a redirect with the profile's Authorization header.
class _NoThemeRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ArtworkProxy(object):
    def __init__(self, api):
        self.api = api
        self._server = None
        self._thread = None
        self.port = 0
        self._bifs = {}                 # (item, file) -> BIF, the last two
        self._bif_lock = threading.Lock()

    def start(self):
        if self._server is not None:
            return self.port
        api = self.api
        proxy = self

        class Handler(httpserver.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path.startswith("/bif/"):
                    proxy._serve_bif_frame(self)
                    return
                # Theme music: allow only this exact Arc route, never an arbitrary media URL.
                theme = is_theme_path("/api/v1" + self.path)
                if not theme and not _is_image_path(self.path.split("?", 1)[0]):
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
                    opener = request.build_opener(_NoThemeRedirect()).open if theme else request.urlopen
                    with opener(req, timeout=20) as resp:
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

    # MARK: - timeline thumbnails

    def bif_url(self, item_id, file_id, index):
        """A local URL for frame `index` of a file's timeline thumbnails."""
        return "http://127.0.0.1:%d/bif/%s/%s/%d.jpg" % (self.port, parse.quote(str(item_id), safe=""),
                                                          parse.quote(str(file_id), safe=""), int(index))

    def _bif(self, item_id, file_id):
        """The file's BIF, fetched once and kept (the last two files)."""
        from arc.bif import BIF
        key = (item_id, file_id)
        with self._bif_lock:
            if key in self._bifs:
                return self._bifs[key]
        data = self.api.bif(item_id, file_id)
        bif = BIF(data) if data else None
        with self._bif_lock:
            self._bifs[key] = bif
            while len(self._bifs) > 2:
                self._bifs.pop(next(iter(self._bifs)))
        if bif is not None:
            log.debug("timeline thumbnails: %d frames", len(bif))
        return bif

    def _serve_bif_frame(self, handler):
        try:
            _, _, item_id, file_id, name = handler.path.split("?", 1)[0].split("/", 4)
            frame = None
            bif = self._bif(parse.unquote(item_id), parse.unquote(file_id))
            if bif is not None:
                frame = bif.frame(int(name.split(".", 1)[0]))
            if not frame:
                handler.send_error(404)
                return
            handler.send_response(200)
            handler.send_header("Content-Type", "image/jpeg")
            handler.send_header("Content-Length", str(len(frame)))
            handler.end_headers()
            handler.wfile.write(frame)
        except Exception as e:
            log.debug("timeline thumbnail failed (%s)", type(e).__name__)
            try:
                handler.send_error(502)
            except Exception:
                pass

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
        """Stops the server and its thread. Kodi waits for every thread an add-on started before
        it lets the add-on end (and kills it after 5 s at Kodi's exit), so this must run."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
