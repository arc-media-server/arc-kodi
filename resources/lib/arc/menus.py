"""What a card's menu offers (Context Menu, C or long OK, on any card), as the Apple app's
TitleActions and the Android app's card menu: Play or Resume, From the Beginning, Watched,
Watchlist, Play Next, Add to Queue, Add to Playlist, Go to Show and, on Home's Continue Watching
row, Remove from Continue Watching; on Home's Queue row, Move Earlier, Move Later and Remove from
Queue.
Plain Python: the Kodi side words and draws the menu."""

from . import models


def card_actions(item, continue_row=False, on_page=False, in_show=False, together=False, playlists=False,
                 queue=False, queue_edit=None):
    """The action keys for a card's menu, in order. `on_page`: the title's own page (its buttons
    play it); `in_show`: an episode on its show's page (no Go to Show); `together`: Watch Together
    is offered (Arc allows it), for a film or an episode; `playlists`: Add to Playlist… is
    offered, for a film, an episode or a show (what a playlist can hold); `queue`: Play Next and
    Add to Queue are offered (Arc has play queues), for the same; `queue_edit`: a Queue row card's
    {"earlier", "later", "remove"} flags (arc.queues.PlayQueue.editable)."""
    item = item or {}
    out = []
    kind = item.get("kind")
    if not on_page and models.playable(item):
        out += ["resume", "from_start"] if models.resume_ms(item) > 0 else ["play"]
    if models.playable(item) and len(models.versions(item)) > 1:
        out.append("play_version")   # Plex's Play Version…, for a title with more than one
    if models.playable(item) or models.is_series(item):
        out.append("unwatched" if models.watched(item) else "watched")
    if kind in ("movie", "series"):
        out.append("watchlist_remove" if models.watchlisted(item) else "watchlist_add")
    if queue and kind in ("movie", "episode", "series"):
        out += ["play_next", "add_to_queue"]
    if playlists and kind in ("movie", "episode", "series"):
        out.append("add_to_playlist")
    if not on_page and not in_show and models.is_episode(item) and item.get("parent_id"):
        out.append("go_to_show")
    if continue_row and models.playable(item):
        out.append("remove_continue")
    if together and models.playable(item) and kind in ("movie", "episode"):
        out.append("watch_together")
    edit = queue_edit or {}
    out += [key for key, flag in (("queue_earlier", "earlier"), ("queue_later", "later"),
                                  ("queue_remove", "remove")) if edit.get(flag)]
    return out


def show_ref(episode):
    """The series an episode belongs to, as an item to open its page with (its art shows at once)."""
    img = models.images(episode)
    images = {k: img.get(src) for k, src in (("backdrop", "series_backdrop"), ("logo", "series_logo"),
                                             ("primary", "series_primary")) if img.get(src)}
    return {"id": episode.get("parent_id"), "kind": "series",
            "title": episode.get("series_title") or episode.get("title", ""), "images": images}
