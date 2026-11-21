# Player extras

Feature-parity item 3, as the Apple and Android players. Built on PR #5.

## Chapters

- **Each chapter's start is a small gap in the timeline**, as the Apple player marks them. The
  first chapter, at the start, isn't marked; at most 40 are drawn.
- **The Playback menu has Chapters**, naming the one playing. It opens a list of the chapters with
  their start times, the one playing ticked; choosing one jumps there. A chapter without a name is
  "Chapter N".
- The chapters come from the playback answer (`chapters[]`); the ordering, the current chapter and
  the marks' places are `arc/playback.py`, with tests.

Checked in Kodi on a virtual display with four chapters added to a test file: the marks at a
quarter, half and three-quarters; the list naming them with 0:00, 0:45, 1:30, 2:15; The Wormhole
jumping to 1:30.

## Timeline thumbnails

- **While Left/Right builds up a skip, the thumbnail of where it will land shows above the
  marker**, as the Apple and Android players. It follows the marker and goes once it seeks.
- The playing file's thumbnails come from Arc as one BIF file (`GET /items/{id}/trickplay?file=`
  says whether they're made; `…/trickplay/{file}/bif` is the file). The local artwork proxy fetches
  a file's BIF once, keeps the last two in memory, and serves its frames as JPEGs at
  `/bif/<item>/<file>/<n>.jpg`. Kodi loads them like any other image. Kodi can't crop one picture
  out of a sprite sheet, which is why the BIF is used.
- Reading BIF files is `arc/bif.py`, with tests; it reads a real one from Arc (19 frames at 10 s).
- Nothing shows for a file Arc hasn't made thumbnails for (its library doesn't make them, or they
  aren't made yet).

Checked in Kodi on a virtual display with thumbnails turned on for the scratch Films library: the
frame for 0:55 above the marker while skipping.

## Episodes and the overview

- **An episode's Playback menu has Episodes** ("Season 1"): this season's episodes with their
  lengths, the one playing ticked. Choosing one plays it in the same player, from where the
  profile left it, as the Apple player's Episodes tab. The season comes from the show's seasons
  (`GET /series/{id}/seasons`), fetched as the episode starts. A season list's episodes don't
  carry their show's name and pictures, so they take the playing episode's.
- **Paused, the title's overview shows above it**, two lines, as Plex's player. It hides while a
  skip thumbnail shows.
- The player's next-episode path is now one function (`_switch_to`), used by Up Next, a play
  queue and the Episodes list.

The Apple player's Info, Chapters, Cast and Episodes tabs are a panel under the controls. Here
Chapters and Episodes are lists in the Playback menu, and Info is the overview when paused. Cast
isn't in the player (it's on the title page).

Checked in Kodi on a virtual display, with two Firefly episodes made 3 minutes long: the overview
when paused; Playback → Episodes listing Season 1 with Ariel ticked; choosing Safe switched to it.
The show's name carrying over was fixed after that run and not seen on screen: the scratch
Continue Watching had moved on to 3-second clips.

## Speed

- **The Playback menu has Speed** (Normal, or e.g. 1.2x) where Kodi can change it. It opens
  0.8x to 1.5x, the current one ticked. The add-on steps Kodi's tempo there
  (`PlayerControl(TempoUp|TempoDown)`, 0.1 a step) and reads back `Player.PlaySpeed` after each
  step, stopping if Kodi doesn't move.
- Kodi changes speed through its audio, so it offers tempo only when it can: not with audio
  passthrough, without an audio device, or with "Sync playback to display". The add-on asks Kodi
  (`Player.TempoEnabled`) and shows Speed only then, following Kodi's own settings
  rather than adding one.
- **Not checked:** the virtual display has no audio device, so Kodi reports tempo as unavailable
  there and Speed doesn't show. The menu was checked to open as before without it. Speed needs
  trying on real hardware.

## Logging (whole change)

- "speed stayed at N" (info) when Kodi doesn't change its tempo.
- Timeline thumbnail and season lookups log at debug.
- "playing <kind>: <method>" (was "playing a <kind>").
