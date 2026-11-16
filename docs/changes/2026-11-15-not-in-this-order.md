# "Not in This Order" episodes

The owner's next feature for the Kodi add-on (relayed from the server chat), modelled on
arc-roku#12 and arc-tv#16. A show's page showed only the seasons of its episode order. Episodes the
profile has but that order doesn't place (`unplaced` in `GET /api/v1/series/{id}/seasons`)
appeared nowhere, so they couldn't be played from Kodi, against Arc's rule that nothing silently
disappears.

## What changed

- **Title page:** after the season tabs there's a **Not in This Order** tab (the web's name),
  listing those episodes by name, without a number (the order gives them none). Select or Play
  plays one, and Context Menu gives its actions, as in a season. Landing on such an episode (from
  its card) opens that tab. The tabs are 280 wide now (were 220) so the name fits.
- **Play, Resume and Up Next** still follow the order's seasons alone, as on the web: an unwatched
  episode outside the order isn't what Play plays.
- **Never "S0 · E0":** Arc sends season and episode 0/0 for these episodes. `models.placed()`
  says whether an episode has a place, and the episode code on cards, the player's heading, Up
  Next and the page's Play label leave the numbers out when it hasn't (a special, S0 · E3, keeps
  its code).
- **Player:** playing one, the Playback menu's Episodes list is "Not in This Order" and lists the
  others outside the order, by name.
- **Show's name in the player:** the season list's episodes carry neither the show's name nor its
  pictures, so the player's heading named the episode twice for any episode played from a show's
  page. The page now passes them along (as the player's own Episodes list already did).
- The tabs and labels are `titlepage.season_tabs()` and `titlepage.episode_label()`, tested in
  `tests/test_titlepage.py`.

This builds on the open title-page and player work; the branch starts from #10
(`claude/kodi-together`).

## Checked

- `python3 -m pytest -q`: 98 passed. `python3 tools/check.py`: all good.
- Kodi 20 on a virtual display against a scratch Arc (not real hardware). Firefly's display order
  was set to TVDB's DVD Order, which leaves four of the test library's episodes out (Arc sends them
  as `unplaced`, with 0/0), then put back:
  - the page showed "Season 1" and "Not in This Order"; the new tab listed Episode 12, 13, 14 and
    20 with no numbers; Play stayed "Play S1 · E9";
  - Episode 14 played from the tab: the player read "Episode 14" over "Firefly" (no "S0, E0"),
    and Playback → Episodes said "Not in This Order" and listed the four by name.

## Logging

Nothing new; a failed seasons load stays a debug line, as before.
