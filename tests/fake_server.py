"""A stand-in Arc server, as a urllib opener, so the API client can be tested with no network.

Routes answer with small fixtures shaped like the v1 contract. It's deliberately tiny: enough
to exercise sign-in, browsing, playback and progress, not a real server.
"""

import io
import json
from urllib import error, parse


class FakeResponse(object):
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.headers = headers or {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeServer(object):
    """Records requests and answers from a routing table. `routes` maps (METHOD, path) to either
    a (status, body) tuple or a callable taking (query, body) and returning one."""

    def __init__(self, routes=None, token_required=True):
        self.routes = routes or {}
        self.token_required = token_required
        self.requests = []

    def open(self, req, data=None, timeout=None):
        method = req.get_method()
        full = req.full_url
        split = parse.urlsplit(full)
        path = split.path.split("/api/v1/", 1)[-1]
        query = dict(parse.parse_qsl(split.query))
        body = json.loads(data.decode("utf-8")) if data else None
        self.requests.append({"method": method, "path": path, "query": query, "body": body,
                              "auth": req.get_header("Authorization")})
        handler = self.routes.get((method, path))
        if handler is None:
            return self._error(404, {"error": "not found", "code": "not_found"})
        status, out = handler(query, body) if callable(handler) else handler
        if 200 <= status < 300:
            if status == 204 or out is None:
                return FakeResponse(status, b"")
            return FakeResponse(status, out)
        return self._error(status, out)

    def _error(self, status, out):
        body = json.dumps(out).encode("utf-8")
        raise error.HTTPError("http://arc", status, out.get("error", ""), {}, io.BytesIO(body))
