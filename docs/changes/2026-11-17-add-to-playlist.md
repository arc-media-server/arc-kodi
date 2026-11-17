# Add to Playlist from Kodi

Playlists already showed and played in Arc for Kodi, but titles could only be added to them on the
web. The web's, Android TV's and LG/Samsung's menus have **Add to Playlist…**; Kodi now has it too.

## What changed

- **Where:** in every card's menu (Context Menu: C or long OK) and so in a title page's ⋯, after
  Add to Watchlist. Offered for films, episodes and shows, which is what a playlist can hold.
- **The list:** Arc's own menu, titled Add to Playlist, saying what's being added ("Add “Parasite”
  to:", or "Add every episode of “Severance” to:" for a show), then the profile's playlists with
  how many titles each holds. Smart playlists aren't listed, since they fill themselves (as on the
  web).
- **Choosing one** adds the title (`POST /api/v1/playlists/{id}/items`, in the v1 contract) and
  shows "Added “Parasite” to Weekend Picks", or that it couldn't.
- **No playlists to add to:** the menu says to make one on the web first, with Close. If the
  playlists don't load, a note says so.
- **Code:** `menus.card_actions(..., playlists=True)` offers it (tested); `api.add_to_playlist`
  sends it (tested); `app._add_to_playlist` draws the list.

## Decisions

- **Existing playlists only**, as on Android TV and LG/Samsung: the web can also make a new one by
  name, but typing a name with a remote is slow.

## Checks

- `python3 -m pytest -q`: 131 passed (new: the menu offers Add to Playlist for films, episodes and
  shows only when asked; the POST's body and answer).
- `python3 tools/check.py`: all good.
- In real Kodi 20.5 on a virtual display (Linux, Xvfb) against a scratch Arc with two ordinary
  playlists and one smart one, from Parasite's card on Home:
  - the card menu has Add to Playlist… after Add to Watchlist (`card-menu.jpg`);
  - the list shows Weekend Picks (1 title) and Movie Night (0 titles), not the smart playlist
    (`picker.jpg`);
  - choosing Weekend Picks shows "Added “Parasite” to Weekend Picks" (`added.jpg`); the server then
    counts 2 titles in it, and kodi.log has "[Arc] added a title to a playlist".
- Not driven: the no-playlists and failed states. Not tried on Kodi on real hardware.

## Logging

- Info: "added a title to a playlist" (no ids or names).
- Warnings with the exception type only: "playlists failed to load for Add to Playlist", "adding
  to a playlist failed".
