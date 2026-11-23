import os

from arc.api import APIError
from arc.device_logs import Journal

from . import toast
from .compat import T, ensure_profile

_journal = None


def journal():
    global _journal
    if _journal is None:
        _journal = Journal(os.path.join(ensure_profile(), "device-logs.json"))
    return _journal


def send(api):
    body = journal().payload()
    if not body["entries"]:
        return False, T(30626)
    try:
        api.send("POST", "client-logs", body, expect_body=False)
    except APIError as error:
        return False, T(30625 if error.status == 404 else 30624)
    return True, T(30623)


def send_and_notify(api):
    try:
        sent, label = send(api)
    except Exception:
        sent, label = False, T(30624)
    toast.show(label)
    return sent
