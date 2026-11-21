# Kodi focus, standalone pills and Recently Added (#51)

- Window-local memory restores each list's selected item after visiting another
  section and each grid row's previous item, including a short final row.
- Library and season tabs have no holder. Relevant header/tab pills use #499's
  doubled geometry/colours: 72px height, 32px text insets, white 10% / selected
  18%, white/black focus at ×1.04. Standalone pills are 20px apart. Season list
  slots keep fixed widths; their label viewport has 32px insets. Existing other
  title-page controls are outside this batch.
- Recently Added seasons say “Season N”, with the batch count in the existing
  corner badge; multi-season batches say “N new episodes”; episodes keep
  “S1 · E4”. Existing added_at keys keep repeat batches distinct. Series badges
  retain their unwatched totals. Updating watched state preserves season counts.
- Removed the nine obsolete holder-slice textures and their generator. Edited
  skin/, rebuilt generated windows with tools/build_skin.py and rebuilt media.

## Outstanding exact-spec limitation

Kodi add-on WindowXML uses the active skin's fonts. Existing arc-label maps to
font13: stock Estuary supplies 30px light text, not #499's 28px medium. This PR
**does not claim exact typography** or modify the user's skin. It stays draft
pending a supported solution or an explicit exception to that font requirement.
Player Info Dolby Vision remains parked; no player code changed.

## Checks and pictures

Starting main: 45ec03a. Full pytest run once: 183 passed, three failed (two
loopback socket permissions; one new assertion expected an absent field instead
of None). Corrected the assertion and reran only those three with loopback access:
3 passed. **All 186 tests pass across those runs.** One existing pytest plugin warning.
Full tools/check.py initially flagged only the nine obsolete textures; after
removing them, its targeted repeat passed. Skin/media builds and final generated
skin consistency check passed. No dependency changes or additional tests run.

[Pictures](2026-11-21-focus-pills/): one before/after pair each for Library,
show seasons and Home. Actual Kodi 20.5 on Xvfb at 1920×1080, with recorded shared
library titles/descriptions and placeholder artwork; not a provider-connected
server. The fixture needed supervisor/RPC isolation corrections before capture.
Verified native grid focus: item 21 → short final row item 25 → back to item 21;
focused season pills and grouped captions/counts inspected. Unit tests also
cover independent row/section positions and clamping after removal.

No Ugoos/CoreELEC or other real hardware, physical remote, playback, HDR/DV,
audio or sustained-use checks. No owner server/data/settings/keys used. Recorded
metadata is from TMDB; titles belong to their owners. No media included.

No new logging for focus/skin presentation work; existing failures remain logged.
Memory is per window, without settings or disk writes. The owner's explicit #499
appearance governs this change rather than claiming Plex pixel parity.
