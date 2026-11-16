# Hide Spoilers

The profile's Hide Spoilers switch was already in Arc's Settings (saved to `/me/prefs`, so every
app follows it), but Kodi didn't act on it. Now it does, as the web app's spoiler guard: an
episode the profile hasn't started (not watched, no resume point) keeps back its still and its
description.

## What changed

- `models.spoiler_hidden(prefs, item)`: the web's rule (`useSpoilerGuard`): on, an episode, not
  played and no position.
- Cards (Home rows, libraries, search, Related: everything through `card_list_item`): such an
  episode shows its show's picture in place of its still, labelled with the episode as Continue
  Watching's show-art cards already are (`home.without_spoilers`); with no show picture, the
  card's empty tile. Posters and backdrops are the show's anyway.
- The title page's episodes: the show's backdrop for the still, and "Description hidden until
  you watch it." (the web's words) under the row.
- Home's hero: the same words in place of the episode's description.
- Settings' Playback note no longer says Kodi doesn't hide spoilers.

Turning the switch on or off takes effect on the next redraw: Arc's live update for the profile
reloads the prefs and the open page. The player shows the playing episode's description as
before (it has started), and its Episodes menu is names only.

## Differences

The web blurs the still on the show page; Kodi can't blur an image, so the show's picture stands
in, as on the web's cards. A season of unwatched episodes is a row of the same picture, each
named. For the owner's list on arc-media-server#80.

## Logging

Nothing new: it's drawing only (the settings change is already logged as "settings changed:
hide_spoilers").

## Checked

Kodi on Xvfb against a scratch Arc: switch turned on in Arc's Settings; Firefly's page then
showed the show's picture and the hidden-description line for unstarted episodes; Home's
Continue Watching hero (S1 · E2, not started) hid its description. Not on real hardware.
