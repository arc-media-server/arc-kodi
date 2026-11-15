"""Arc's play queues (POST/PATCH /play-queues), for Play All and Shuffle on a collection or a
playlist: the queue is made from the titles (a show expands to its episodes), shuffled on the
server if asked, and the player asks it for the next title as each one ends. Only this
device and profile see the queue; changing it never controls a player, so the add-on plays each
title itself. Plain Python, tested against the stand-in server."""




from .api import APIError


class PlayQueue(object):
    def __init__(self, api, data):
        self.api = api
        self._set(data)

    def _set(self, data):
        data = data or {}
        self.id = data.get("id")
        self.revision = data.get("revision", 0)
        self.current = data.get("current_entry_id")
        self.entries = data.get("entries") or []

    @classmethod
    def create(cls, api, item_ids=None, playlist_id=None, shuffle=False):
        body = {"playlist_id": playlist_id} if playlist_id else {"item_ids": list(item_ids or [])}
        try:
            data = api.send("POST", "play-queues", body, route="play-queues")
        except APIError as e:
            if e.status != 409:
                raise
            # This device and profile already have a queue (the last Play All): replace it.
            old = api.get("play-queues/current", route="play-queues/{id}") or {}
            body = dict(body, replace_id=old.get("id"), revision=old.get("revision", 0))
            data = api.send("POST", "play-queues", body, route="play-queues")
        queue = cls(api, data)
        if shuffle and len(queue.entries) > 1:
            queue._patch({"operation": "shuffle"})
        return queue

    def _patch(self, change):
        change = dict(change, revision=self.revision)
        self._set(self.api.send("PATCH", "play-queues/" + self.id, change, route="play-queues/{id}"))

    def _index(self):
        for i, e in enumerate(self.entries):
            if e.get("id") == self.current:
                return i
        return -1

    def current_item(self):
        """The title to play now: the current entry, or the first one Arc can play."""
        i = self._index()
        for e in self.entries[max(i, 0):]:
            if e.get("available", True) and e.get("item"):
                return e["item"]
        return None

    def peek_next(self):
        """The next playable title after the current one, for Up Next, without moving."""
        for e in self.entries[self._index() + 1:]:
            if e.get("available", True) and e.get("item"):
                return e["item"]
        return None

    def advance(self):
        """Moves on and returns the title now current, or None at the end of the queue. Entries
        Arc can't play (removed or restricted) are passed over."""
        while self._index() + 1 < len(self.entries):
            self._patch({"operation": "advance"})
            item = self.entries[self._index()].get("item") if self._index() >= 0 else None
            if item and self.entries[self._index()].get("available", True):
                return item
        return None
