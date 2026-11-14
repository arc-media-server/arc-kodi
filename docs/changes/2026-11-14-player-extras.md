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
