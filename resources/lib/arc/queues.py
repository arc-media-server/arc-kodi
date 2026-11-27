"""Arc's play queues (POST/PATCH /play-queues), as the Android and Apple apps': playing a title
starts a queue of it; Play All and Shuffle make one from a collection's or a playlist's titles (a
show expands to its episodes); Play Next and Add to Queue add to it; Home's Queue row shows it and
arranges it (Move Earlier, Move Later, Remove from Queue). The player asks it for the next title
as each one ends. Only this device and profile see the queue; changing it never controls a
player, so the add-on plays each title itself. Plain Python, tested against the stand-in server."""

from .api import APIError


def available(features):
    """Queues show only when GET /capabilities says play_queues is supported, available and
    allowed, as the Android app; an older Arc gets none of it."""
    f = (features or {}).get("play_queues") or {}
    return bool(f.get("supported") and f.get("available") and f.get("allowed"))


def moved(order, protected, entry_id, step):
    """The whole order with `entry_id` moved one place earlier (-1) or later (+1), never into or
    out of the first `protected` entries (the one playing and those before it); None if it can't."""
    if entry_id not in order:
        return None
    i = order.index(entry_id)
    j = i + step
    if i < protected or j < protected or j >= len(order):
        return None
    order = list(order)
    order[i], order[j] = order[j], order[i]
    return order


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

    @classmethod
    def current(cls, api):
        """This device and profile's queue (GET /play-queues/current), or None if there's none."""
        try:
            data = api.get("play-queues/current", route="play-queues/{id}")
        except APIError as e:
            if e.status in (404, 410):
                return None
            raise
        return cls(api, data) if data and data.get("id") else None

    def _patch(self, change, retry=True):
        try:
            self._set(self.api.send("PATCH", "play-queues/" + self.id, dict(change, revision=self.revision),
                                    route="play-queues/{id}"))
        except APIError as e:
            if e.status != 409 or not retry:
                raise
            # Changed elsewhere (another window, the web): read it again and try once more.
            self._set(self.api.get("play-queues/" + self.id, route="play-queues/{id}"))
            self._patch(change, retry=False)

    def delete(self):
        self.api.send("DELETE", "play-queues/%s?revision=%d" % (self.id, self.revision), None,
                      route="play-queues/{id}")

    def add(self, item_ids, next_=False):
        """Play Next (`next_`) or Add to Queue: the titles (a show adds its episodes)."""
        self._patch({"operation": "next" if next_ else "append", "item_ids": list(item_ids)})

    def select(self, entry_id):
        if entry_id != self.current:
            self._patch({"operation": "select", "entry_id": entry_id})

    def remove(self, entry_id):
        self._patch({"operation": "remove", "entry_ids": [entry_id]})

    def move(self, entry_id, step):
        """Move Earlier (-1) or Later (+1) among the titles after the one playing."""
        order = moved([e.get("id") for e in self.entries], self._index() + 1, entry_id, step)
        if order:
            self._patch({"operation": "reorder", "entry_ids": order})

    def editable(self, entry_id):
        """Which of earlier/later/remove an entry offers: none for the one playing or before it."""
        ids = [e.get("id") for e in self.entries]
        protected = self._index() + 1
        return {"earlier": moved(ids, protected, entry_id, -1) is not None,
                "later": moved(ids, protected, entry_id, 1) is not None,
                "remove": entry_id in ids and ids.index(entry_id) >= protected}

    def upcoming(self):
        """Home's Queue row: the current entry and those after it that can be played, as
        (entry id, item) pairs."""
        return [(e.get("id"), e["item"]) for e in self.entries[max(self._index(), 0):]
                if e.get("available", True) and e.get("item")]

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
