"""The device token and the chosen server, kept in the add-on's profile folder (addon_data), never
in Kodi's settings UI, a URL, a log line or Kodi's databases."""

import json
import os

import xbmcvfs

from . import compat
from .log import log

_FILE = "session.json"


def _path():
    return os.path.join(compat.ensure_profile(), _FILE)


def load():
    """{"base_url", "token", "profile_id", "profile_name"} or {}."""
    try:
        with xbmcvfs.File(_path()) as f:
            data = f.read()
        return json.loads(data) if data else {}
    except Exception as e:
        log.warning("couldn't read the saved session (%s)", type(e).__name__)
        return {}


def save(data):
    try:
        with xbmcvfs.File(_path(), "w") as f:
            f.write(json.dumps(data))
        return True
    except Exception as e:
        log.warning("couldn't save the session (%s)", type(e).__name__)
        return False


def update(**changes):
    data = load()
    data.update({k: v for k, v in changes.items()})
    save(data)
    return data


def clear():
    try:
        if xbmcvfs.exists(_path()):
            xbmcvfs.delete(_path())
    except Exception:
        pass
