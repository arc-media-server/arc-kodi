# The player's tabs: Info, Chapters, Cast, Episodes

The owner asked for the player's Info, Cast and the rest as the Apple app has them, and for the
overview not to sit over the picture when paused. Following the Apple player (owner's choice:
the tabs under the timeline, Down to open them).

## What changed

- A row of tabs under the timeline while the controls show: **Info**, **Chapters**, **Cast** and
  **Episodes**, each only when it has something (chapters in the file, a cast, more than one
  episode in the season). The title, round buttons, timeline and times moved up 72 to make room.
- Down from the timeline, or from the picture with the controls hidden, opens **Info**. Left
  and Right move between tabs, each showing its card; Down goes into the card; Up goes back to
  the tabs and then the timeline; Back closes the card. While a card is open the title and
  timeline step aside and the row moves up, as the Apple player's.
- **Info**: the episode's still (or the film's backdrop; the show's picture with Hide Spoilers),
  the title (and the show), the overview, the details (episode code, length, year, quality
  capsules) and how it's playing (played as it is, repackaged or converted); Restart, and
  Previous for an episode whose previous one is on disk.
- **Chapters**: a row of cards, the one playing selected; Select jumps there.
- **Cast**: faces as the title page's (the episode's own cast for an episode), from the whole
  title fetched once per title.
- **Episodes**: the season's stills as the title page's, the one playing selected; Select plays
  another.
- Every card sits in the same dark rounded box (1720 by 384), as Info's (the owner, after the
  first version showed Chapters, Cast and Episodes straight over the picture).
- The overview no longer shows over the picture when paused (it's in Info), and Chapters and
  Episodes left the Playback menu (they're tabs).

`titlepage.previous_episode` is plain Python with tests.

## Logging

Debug: "player details not loaded (<error>)" and "info card not filled (<error>)".

## Checked

Kodi on Xvfb against a scratch Arc: Interstellar (Info, Chapters, Cast; Down, Left/Right, Up and
Back) and Firefly (Info with its still and Previous, Cast with the episode's cast, Episodes with
the one playing selected). The test library's 3-second clips move on to the next episode every
few seconds, so long stays in a card weren't tried. Not on real hardware.
