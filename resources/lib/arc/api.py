"""Arc's stable API (/api/v1), signed in with a device token sent as a Bearer header.

Plain Python (no Kodi imports), so it can be tested anywhere. Answers are returned as the
decoded JSON (dicts and lists); read them with .get() and a default, since the v1 promise only
adds fields. Logs name routes only: never ids, query strings, URLs or tokens.
"""

import json
import logging
import socket
import ssl
from urllib import error as urlerror
from urllib import parse, request

log = logging.getLogger("arc")

DEFAULT_PORT = 8099


class APIError(Exception):
    """A failure Arc answered with: its status, plain-words message and what it needs next."""

    def __init__(self, status, message, needs=None, code=None, request_id=None, retry_after=None):
        Exception.__init__(self, message)
        self.status = status
        self.message = message
        self.needs = needs
        self.code = code
        self.request_id = request_id
        self.retry_after = retry_after


class RoomConflict(Exception):
    """A Watch Together room changed since the revision (or generation) a call named (409):
    `room` is the room as it is now."""

    def __init__(self, room):
        Exception.__init__(self, "room changed")
        self.room = room


class Unreachable(Exception):
    """Nothing answered (no network, a wrong address, a timeout)."""


class UnexpectedAnswer(Exception):
    """Arc answered with something this app couldn't read."""


def normalise_address(text):
    """A typed server address as a base URL: http:// and port 8099 unless given; None if it
    can't be one. "192.168.1.20" -> "http://192.168.1.20:8099"."""
    text = (text or "").strip()
    if not text:
        return None
    if "://" not in text:
        text = "http://" + text
    try:
        parts = parse.urlsplit(text)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    host = parts.hostname
    if any(c in host for c in " /\\@"):
        return None
    if ":" in host:
        host = "[" + host + "]"
    try:
        port = parts.port
    except ValueError:
        return None
    if port is None and parts.scheme == "http":
        port = DEFAULT_PORT
    netloc = host if port is None else "%s:%d" % (host, port)
    path = parts.path.rstrip("/")
    return "%s://%s%s" % (parts.scheme, netloc, path)


def versioned(path):
    """Arc answers with its unversioned /api/ paths; apps use the same routes under /api/v1/."""
    if path.startswith("/api/") and not path.startswith("/api/v1/"):
        return "/api/v1/" + path[len("/api/"):]
    return path


def _q(value):
    return parse.quote(str(value), safe="")


class ArcAPI(object):
    def __init__(self, base_url, token=None, timeout=20, user_agent="Arc for Kodi", opener=None):
        self.base_url = (base_url or "").rstrip("/")
        self._token = token if callable(token) else (lambda: token)
        self.timeout = timeout
        self.user_agent = user_agent
        self._opener = opener or request.build_opener(_NoRedirect())

    # MARK: - signing in

    def health(self):
        return self.get("health")

    def start_link(self, device):
        return self.send("POST", "auth/link", {"device": device})

    def poll_link(self, poll):
        """('waiting', None), ('expired', None) or ('approved', token)."""
        status, data, _ = self.raw("GET", "auth/link/" + _q(poll), route="auth/link/{poll}")
        if status == 202:
            return "waiting", None
        if status == 404:
            return "expired", None
        if status == 200:
            token = self._decode(data, "auth/link/{poll}").get("token")
            if not token:
                raise UnexpectedAnswer()
            return "approved", token
        raise self._failure(status, data, "auth/link/{poll}")

    def login(self, password, device):
        answer = self.send("POST", "auth/login", {"password": password, "device": device})
        token = answer.get("token") if isinstance(answer, dict) else None
        if not token:
            raise UnexpectedAnswer()
        return token

    def auth_status(self):
        return self.get("auth/status")

    def choose_profile(self, profile_id, pin=None):
        body = {"id": profile_id}
        if pin:
            body["pin"] = pin
        return self.send("POST", "auth/profile", body)

    def sign_out(self):
        try:
            self.raw("POST", "auth/logout", body={}, route="auth/logout")
        except Exception:  # signing out locally goes ahead whatever the server says
            pass

    def identity(self):
        return self.get("identity")

    def capabilities(self):
        return self.get("capabilities")

    # Server discovery: anonymous, direct probes; expected misses stay quiet.
    def discover(self):
        req = request.Request(self.base_url + "/api/v1/discover",
                              headers={"Accept": "application/json", "User-Agent": self.user_agent})
        opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(req, timeout=self.timeout) as response:
                if response.status != 200:
                    return None
                answer = json.loads(response.read(65537).decode("utf-8"))
            if (isinstance(answer, dict) and answer.get("product") == "arc"
                    and type(answer.get("api_version")) is int and answer["api_version"] >= 1):
                return answer
        except (OSError, urlerror.URLError, ValueError):
            pass
        return None

    # MARK: - browsing

    def libraries(self):
        return self.get("libraries") or []

    def prefs(self):
        return self.get("me/prefs") or {}

    def patch_prefs(self, changes):
        return self.send("PATCH", "me/prefs", changes)

    def continue_watching(self, with_up_next=True):
        path = "home/continue?with_up_next=1" if with_up_next else "home/continue"
        return self.get(path, route="home/continue") or []

    def next_up(self):
        return self.get("home/next-up") or []

    def watchlist(self):
        return self.get("watchlist") or []

    def items(self, params):
        return self.get("items?" + parse.urlencode(sorted(params.items())), route="items") or {}

    def recent_shows(self, library_id):
        return self.get("libraries/%d/recent-shows" % int(library_id), route="libraries/{id}/recent-shows") or []

    def trickplay(self, item_id, file_id):
        """A file's timeline thumbnails: {"bif", "info": {interval_ms, count, width, height}}, or
        None until Arc has made them (404)."""
        try:
            return self.get("items/%s/trickplay?file=%s" % (_q(item_id), _q(str(file_id))), route="items/{id}/trickplay")
        except APIError as e:
            if e.status == 404:
                return None
            raise

    def bif(self, item_id, file_id):
        """The file's thumbnails as one BIF file (bytes), or None."""
        status, data, _ = self.raw("GET", "items/%s/trickplay/%s/bif" % (_q(item_id), _q(str(file_id))),
                                   route="items/{id}/trickplay/{file}/bif")
        return data if status == 200 else None

    def facets(self, library_id):
        return self.get("libraries/%d/facets" % int(library_id), route="libraries/{id}/facets") or {}

    def folders(self, library_id, path=""):
        """An Other videos library's folder at `path` (as a folder's own "path"; "" for the top):
        {"path", "folders": [{name, path, count, cover}], "items": [...]}."""
        query = ("?path=" + _q(path)) if path else ""
        return self.get("libraries/%d/folders%s" % (int(library_id), query), route="libraries/{id}/folders") or {}

    def recommended(self, library_id):
        return self.get("libraries/%d/recommended" % int(library_id), route="libraries/{id}/recommended") or {}

    def library_collections(self, library_id):
        return self.get("libraries/%d/collections" % int(library_id), route="libraries/{id}/collections") or []

    def item(self, item_id):
        return self.get("items/" + _q(item_id), route="items/{id}")

    def similar(self, item_id):
        return self.get("items/" + _q(item_id) + "/similar", route="items/{id}/similar") or []

    def palette(self, item_id):
        return self.get("items/" + _q(item_id) + "/artwork/palette", route="items/{id}/artwork/palette")

    def seasons(self, series_id):
        return self.get("series/" + _q(series_id) + "/seasons", route="series/{id}/seasons")

    def collection(self, collection_id):
        return self.get("collections/" + _q(collection_id), route="collections/{id}")

    def playlists(self):
        return self.get("playlists") or []

    def playlist(self, playlist_id):
        return self.get("playlists/" + _q(playlist_id), route="playlists/{id}")

    def person(self, person_id):
        return self.get("people/%d" % int(person_id), route="people/{id}")

    def search(self, query):
        return self.get("search?" + parse.urlencode({"q": query}), route="search") or {}

    def next_episode(self, item_id):
        """The episode after this one in the profile's order, or None (204)."""
        route = "items/{id}/next"
        status, data, _ = self.raw("GET", "items/" + _q(item_id) + "/next", route=route)
        if status == 204:
            return None
        if not 200 <= status < 300:
            raise self._failure(status, data, route)
        return self._decode(data, route)

    # MARK: - changing things

    def set_played(self, item_id, played, season_number=None):
        body = {"played": bool(played)}
        if season_number is not None:
            body["season_number"] = season_number
        self.send("PUT", "items/" + _q(item_id) + "/played", body, route="items/{id}/played", expect_body=False)

    def set_watchlist(self, item_id, on):
        self.send("PUT", "items/" + _q(item_id) + "/watchlist", {"on": bool(on)}, route="items/{id}/watchlist",
                  expect_body=False)

    def remove_from_continue(self, item_id):
        self.send("DELETE", "home/continue/" + _q(item_id), None, route="home/continue/{id}", expect_body=False)

    # MARK: - playing

    def start_playback(self, item_id, body):
        return self.send("POST", "items/" + _q(item_id) + "/playback", body, route="items/{id}/playback")

    def playback_preview(self, item_id, body):
        """The decision a playback request would get, without starting anything (read-only)."""
        return self.send("POST", "items/" + _q(item_id) + "/playback-preview", body, route="items/{id}/playback-preview")

    def cast_link(self, stream_path):
        """A stream, subtitle or extra link Arc gave, as a link carrying its own scoped token, so
        Kodi's player can open it without the session token (POST /cast)."""
        answer = self.send("POST", "cast", {"url": stream_path})
        url = answer.get("url") if isinstance(answer, dict) else None
        if not url:
            raise UnexpectedAnswer()
        return url

    def report_progress(self, item_id, position_ms, duration_ms, state):
        body = {"position_ms": int(max(0, position_ms)), "duration_ms": int(max(0, duration_ms)), "state": state}
        return self.send("PUT", "items/" + _q(item_id) + "/progress", body, route="items/{id}/progress")

    def ping_transcode(self, session_id):
        self.send("POST", "transcode/" + _q(session_id) + "/ping", {}, route="transcode/{sid}/ping", expect_body=False)

    def stop_transcode(self, session_id):
        try:
            self.raw("DELETE", "transcode/" + _q(session_id), route="transcode/{sid}")
        except Exception:
            pass

    # MARK: - addresses

    def absolute(self, path):
        """An address Arc gave (artwork, a stream) as a full URL under /api/v1/."""
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return self.base_url + versioned(path)

    @property
    def authorization(self):
        token = self._token()
        return {"Authorization": "Bearer " + token} if token else {}

    # MARK: - Watch Together (server docs/WATCH-TOGETHER-API.md)

    def watch_people(self, item_id=None):
        """Who this profile may invite; with `item_id`, each says whether they may play it."""
        path = "watch-together/people" + ("?" + parse.urlencode({"item_id": item_id}) if item_id else "")
        return (self.get(path, route="watch-together/people") or {}).get("people") or []

    def watch_rooms(self):
        """The rooms this profile made, was invited to or is in, newest first."""
        return (self.get("watch-together/rooms") or {}).get("rooms") or []

    def create_invited_room(self, item_id, profile_ids):
        """A room for chosen people: nobody's in it until they join from their lists."""
        return self.send("POST", "watch-together/rooms", {"item_id": item_id, "profile_ids": list(profile_ids)})

    def create_room(self, item_id):
        """A room with a code, joined at once by this device: {room, invite_code, ...}."""
        return self.send("POST", "watch-together", {"item_id": item_id, "start_ms": 0})

    def join_room(self, code):
        return self.send("POST", "watch-together/join", {"code": code}, route="watch-together/join")

    def accept_room(self, room_id):
        """Joins a room from this profile's list, without a code."""
        return self.send("POST", "watch-together/rooms/" + _q(room_id) + "/join", {},
                         route="watch-together/rooms/{id}/join")

    def dismiss_room(self, room_id):
        """Declines an invitation, or cancels a room this profile made."""
        self.send("POST", "watch-together/rooms/" + _q(room_id) + "/dismiss", None,
                  route="watch-together/rooms/{id}/dismiss", expect_body=False)

    def current_room(self):
        """This device and profile's own room, or None."""
        status, data, _ = self.raw("GET", "watch-together/current", route="watch-together/current")
        if status == 404:
            return None
        if not 200 <= status < 300:
            raise self._failure(status, data, "watch-together/current")
        return self._decode(data, "watch-together/current")

    def room_command(self, room_id, revision, action, position_ms=None, item_id=None):
        """play, pause, seek (position_ms), change_item (item_id, position_ms) or end. A room that
        changed since `revision` raises RoomConflict with the room as it is now."""
        body = {"revision": revision, "action": action}
        if position_ms is not None:
            body["position_ms"] = max(0, int(position_ms))
        if item_id is not None:
            body["item_id"] = item_id
        return self._room_call("watch-together/" + _q(room_id) + "/commands", "watch-together/{id}/commands", body)

    def room_heartbeat(self, room_id, generation, position_ms, state, ready):
        """This player's report, every couple of seconds. A seek or new title since `generation`
        raises RoomConflict."""
        body = {"generation": generation, "position_ms": max(0, int(position_ms)), "state": state,
                "ready": bool(ready)}
        return self._room_call("watch-together/" + _q(room_id) + "/heartbeat", "watch-together/{id}/heartbeat", body)

    def leave_room(self, room_id):
        try:
            self.raw("POST", "watch-together/" + _q(room_id) + "/leave", route="watch-together/{id}/leave")
        except Unreachable:
            pass

    def renew_room_code(self, room_id, revision):
        return self._room_call("watch-together/" + _q(room_id) + "/invite", "watch-together/{id}/invite",
                               {"revision": revision}, whole=True)

    def invite_people(self, room_id, profile_ids):
        return self.send("POST", "watch-together/" + _q(room_id) + "/people", {"profile_ids": list(profile_ids)},
                         route="watch-together/{id}/people")

    def server_time(self, client_sent_ms):
        return self.get("watch-together/time?client_sent_ms=%d" % int(client_sent_ms), route="watch-together/time")

    def open_room_events(self, room_id, timeout=45):
        """The room's live stream (SSE: event "room", the whole room each time)."""
        return self._open_stream("watch-together/" + _q(room_id) + "/events", "watch-together/{id}/events",
                                 None, timeout)

    def _room_call(self, path, route, body, whole=False):
        status, data, _ = self.raw("POST", path, body=body, route=route)
        if status == 409:
            obj = None
            try:
                obj = json.loads(data.decode("utf-8")) if data else None
            except (ValueError, UnicodeDecodeError):
                obj = None
            if isinstance(obj, dict) and isinstance(obj.get("room"), dict):
                raise RoomConflict(obj["room"])
        if not 200 <= status < 300:
            raise self._failure(status, data, route)
        return self._decode(data, route)

    def open_events(self, last_event_id=None, timeout=45):
        """Opens Arc's change-hint stream (Server-Sent Events) and returns the open response, to
        read line by line (arc/events.py). `last_event_id` resumes after a drop. Raises APIError
        (with retry_after for a 429) or Unreachable."""
        return self._open_stream("events", "events", last_event_id, timeout)

    def _open_stream(self, path, route, last_event_id, timeout):
        req = request.Request(self.base_url + "/api/v1/" + path, method="GET")
        req.add_header("Accept", "text/event-stream")
        req.add_header("User-Agent", self.user_agent)
        if last_event_id:
            req.add_header("Last-Event-ID", str(last_event_id)[:80])
        for k, v in self.authorization.items():
            req.add_header(k, v)
        try:
            return self._opener.open(req, timeout=timeout)
        except urlerror.HTTPError as e:
            with e:
                err = self._failure(e.code, e.read(), route)
                err.retry_after = _seconds((e.headers or {}).get("Retry-After"))
                raise err
        except (urlerror.URLError, socket.timeout, ssl.SSLError, ConnectionError, OSError) as e:
            log.debug("%s: can't reach the server (%s)", route, type(getattr(e, "reason", e)).__name__)
            raise Unreachable(str(type(e).__name__))

    # MARK: - plumbing

    def get(self, path, route=None):
        route = route or path
        status, data, _ = self.raw("GET", path, route=route)
        if not 200 <= status < 300:
            raise self._failure(status, data, route)
        return self._decode(data, route)

    def send(self, method, path, body, route=None, expect_body=True):
        route = route or path
        status, data, _ = self.raw(method, path, body=body, route=route)
        if not 200 <= status < 300:
            raise self._failure(status, data, route)
        if not expect_body or not data:
            return None
        return self._decode(data, route)

    def raw(self, method, path, body=None, route=None):
        """Sends a request to /api/v1/`path`; `route` names it in logs without ids or queries.
        Returns (status, body bytes, headers)."""
        route = route or path
        req = request.Request(self.base_url + "/api/v1/" + path, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", self.user_agent)
        for k, v in self.authorization.items():
            req.add_header(k, v)
        data = None
        if body is not None:
            data = json.dumps(body, sort_keys=True).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        try:
            resp = self._opener.open(req, data=data, timeout=self.timeout)
            with resp:
                return resp.status, resp.read(), resp.headers
        except urlerror.HTTPError as e:
            with e:
                return e.code, e.read(), e.headers
        except (urlerror.URLError, socket.timeout, ssl.SSLError, ConnectionError, OSError) as e:
            log.warning("%s: can't reach the server (%s)", route, type(getattr(e, "reason", e)).__name__)
            raise Unreachable(str(type(e).__name__))

    def _decode(self, data, route):
        try:
            return json.loads(data.decode("utf-8")) if data else None
        except (ValueError, UnicodeDecodeError) as e:
            log.warning("unexpected answer from %s: %s", route, str(e)[:200])
            raise UnexpectedAnswer()

    def _failure(self, status, data, route):
        obj = None
        try:
            obj = json.loads(data.decode("utf-8")) if data else None
        except (ValueError, UnicodeDecodeError):
            obj = None
        if not isinstance(obj, dict):
            obj = {}
        message = obj.get("error") or "the server answered %d" % status
        # Signed out, a wrong PIN or a missing profile are expected; a server error is worth a warning.
        if status >= 500:
            log.warning("%s failed: %d %s", route, status, message)
        else:
            log.debug("%s answered %d", route, status)
        return APIError(status, message, needs=obj.get("needs"), code=obj.get("code"),
                        request_id=obj.get("request_id"))


def _seconds(value):
    try:
        return max(1, min(int(value), 300))
    except (TypeError, ValueError):
        return None


class _NoRedirect(request.HTTPRedirectHandler):
    """The token must never follow a redirect to another host; Arc's API doesn't redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if parse.urlsplit(newurl).netloc != parse.urlsplit(req.full_url).netloc:
            return None
        return request.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)
