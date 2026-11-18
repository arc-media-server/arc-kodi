"""Theme music eligibility and the narrow route used by the local media proxy."""
import re

_THEME = re.compile(r"^/api/(?:v1/)?items/[a-f0-9]+/theme(?:\?v=[A-Za-z0-9._-]+)?$")


def is_theme_path(path):
    return bool(isinstance(path, str) and _THEME.fullmatch(path))


def theme_path(item, prefs):
    if not item or (prefs or {}).get("theme_music") is False:
        return None
    if item.get("kind") not in ("movie", "series"):
        return None
    path = item.get("theme_url")
    return path if is_theme_path(path) else None
