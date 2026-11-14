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
