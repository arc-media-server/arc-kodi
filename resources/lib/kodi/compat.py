"""The Kodi modules, found once, and the add-on's own paths. Importing this is how the Kodi side
reaches xbmc*; the arc/ layer never imports it."""

import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_VERSION = ADDON.getAddonInfo("version")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
SKIN_PATH = os.path.join(ADDON_PATH, "resources", "skins")


def ensure_profile():
    if not xbmcvfs.exists(PROFILE_PATH):
        xbmcvfs.mkdirs(PROFILE_PATH)
    return PROFILE_PATH


def T(string_id):
    """A localised string from strings.po (ids 30000+)."""
    return ADDON.getLocalizedString(string_id)
