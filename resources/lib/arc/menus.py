"""What a card's menu offers (Context Menu, C or long OK, on any card), as the Apple app's
TitleActions and the Android app's card menu: Play or Resume, From the Beginning, Watched,
Watchlist, Go to Show and, on Home's Continue Watching row, Remove from Continue Watching.
Plain Python: the Kodi side words and draws the menu."""

from . import models


def card_actions(item, continue_row=False, on_page=False, in_show=False, together=False):
    """The action keys for a card's menu, in order. `on_page`: the title's own page (its buttons
    play it); `in_show`: an episode on its show's page (no Go to Show); `together`: Watch Together
    is offered (Arc allows it), for a film or an episode."""
    item = item or {}
    out = []
    kind = item.get("kind")
    if not on_page and models.playable(item):
        out += ["resume", "from_start"] if models.resume_ms(item) > 0 else ["play"]
    if models.playable(item) or models.is_series(item):
        out.append("unwatched" if models.watched(item) else "watched")
    if kind in ("movie", "series"):
        out.append("watchlist_remove" if models.watchlisted(item) else "watchlist_add")
    if not on_page and not in_show and models.is_episode(item) and item.get("parent_id"):
        out.append("go_to_show")
    if continue_row and models.playable(item):
        out.append("remove_continue")
    if together and models.playable(item) and kind in ("movie", "episode"):
        out.append("watch_together")
    return out


def show_ref(episode):
    """The series an episode belongs to, as an item to open its page with (its art shows at once)."""
    img = models.images(episode)
    images = {k: img.get(src) for k, src in (("backdrop", "series_backdrop"), ("logo", "series_logo"),
                                             ("primary", "series_primary")) if img.get(src)}
    return {"id": episode.get("parent_id"), "kind": "series",
            "title": episode.get("series_title") or episode.get("title", ""), "images": images}
