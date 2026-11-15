"""Turning Arc items and cards into Kodi ListItems, with artwork fetched through the proxy. Shared
by Home, the library grid, Related and search."""

from arc import home as homerows
from arc import models

from ..compat import T
from .base import list_item


def item_art(session, item):
    img = models.images(item)
    return {
        "poster": session.art(img.get("series_primary") if models.is_episode(item) else img.get("primary")),
        "thumb": session.art(img.get("backdrop") or img.get("primary")),
        "fanart": session.art(img.get("backdrop_full") or img.get("backdrop") or img.get("series_backdrop")),
        "clearlogo": session.art(img.get("logo") or img.get("series_logo")),
    }


def card_list_item(session, card, style, season_posters=False):
    """A card (from arc.home.card / recent_card) as a ListItem with the right picture for `style`."""
    item = card["item"]
    picture = homerows.card_art(card, style, season_posters)
    art = {"thumb": session.art(picture), "poster": session.art(card.get("poster")),
           "fanart": session.art(card.get("backdrop")), "clearlogo": session.art(card.get("logo"))}
    label = card.get("label") or item.get("title", "")
    sub = card["subtitle"] if card.get("subtitle") is not None else _subtitle(card)
    props = {
        "id": card["id"],
        "item_id": item.get("id"),
        "kind": item.get("kind", ""),
        "playable": "true" if models.playable(item) else "",
        "series": item.get("series_title") or "",
        "watched": "true" if models.watched(item) else "",
        "unwatched": item.get("unwatched_count") or "",
        "progress": "" if card.get("progress") is None else str(int(card["progress"] * 100)),
        "showart": "true" if card.get("show_art") else "",
        "subtitle": sub,
    }
    if card.get("new_episodes"):
        props["badge"] = T(30107) % card["new_episodes"]
    if card.get("tag"):
        props["tag"] = card["tag"]   # a word on a wide card's picture (Watch Together)
    li = list_item(label, sub, art=art, props=props)
    set_progress(li, item)
    return li


def update_list_item(li, item):
    """Shows a changed watched state on a card already in a list (after its menu marked it)."""
    if li is None:
        return
    li.setProperty("watched", "true" if models.watched(item) else "")
    li.setProperty("unwatched", str(item.get("unwatched_count") or ""))
    if models.resume_ms(item) <= 0:
        li.setProperty("progress", "")
        try:
            li.getVideoInfoTag().setResumePoint(0, 0)
        except AttributeError:
            li.setProperty("ResumeTime", "0")


def set_progress(li, item):
    """Gives a part-watched card Kodi's resume point for display only, so the skin's progress bar
    can read ListItem.PercentPlayed. Playback ignores Kodi's resume points (Arc's are the truth)."""
    resume, duration = models.resume_ms(item), models.duration_ms(item)
    if resume <= 0 or duration <= 0:
        return
    try:
        li.getVideoInfoTag().setResumePoint(resume / 1000.0, duration / 1000.0)  # Kodi 20+
    except AttributeError:
        li.setProperty("ResumeTime", str(resume / 1000.0))  # Kodi 19
        li.setProperty("TotalTime", str(duration / 1000.0))


def _subtitle(card):
    item = card["item"]
    if item.get("kind") == "folder":
        n = int(item.get("count") or 0)
        return T(30275) if n == 1 else T(30274) % n
    if card.get("season_number") is not None:
        return T(30155) % card["season_number"]
    if models.is_episode(item):
        code = models.episode_code(item)
        return ("%s · %s" % (code, item.get("title", ""))) if card.get("show_art") else code
    bits = []
    if item.get("year"):
        bits.append(str(item["year"]))
    rt = models.runtime_text(models.duration_ms(item))
    if rt:
        bits.append(rt)
    return " · ".join(bits)


def item_list_item(session, item, style="poster"):
    """A plain Arc item as a card (library grid, Related, search results)."""
    return card_list_item(session, homerows.card(item), style)
