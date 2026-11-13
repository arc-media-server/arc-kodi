# Arc's own player, and the owner's first-test fixes

The owner's first test on real hardware (13 November) found: rows cut off before the right edge,
Kodi's own player OSD (not matching the other apps, and not usable with Arc's overlay over it),
Down on Home moving two rows, square posters, a jagged logo and jagged pill corners. Playback
worked. This fixes those and adds a feature-parity plan (`docs/plans/feature-parity.md`).

## What changed

- **Arc's own player** (`kodi/player_osd.py`, `skin/script-arc-player.xml`), laid out as the Apple
  and Android players: the title at the bottom left (an episode's "S2, E4 · name" above its
  show), three round buttons (Playback, Audio, Subtitles), the timeline with the time played
  under its marker and the time left at the end.
  - Remote: Left/Right skip 10 s (presses add up, then it seeks); Select or Down shows the
    controls on the timeline, Up on the Subtitles button; Select on the timeline plays/pauses;
    the remote's skip keys skip 10 s / 1 min; Back closes a menu, hides the controls, then stops.
    The controls hide after 5 s while playing and stay while paused.
  - Menus open above their button and size to their rows: **Playback** (Quality, Version when
    there's more than one, Play from the Beginning), **Audio** (language, codec, channels),
    **Subtitles** (Off, then each track: Forced, SDH, External).
  - It's a modal window, so no key reaches Kodi's own player and OSD (that's what made the first
    version unusable). Kodi still pauses and stops itself.
  - Skip Intro/Recap/Credits and Up Next live in it; Up Next counts down 10 s when the profile
    plays on by itself.
- **Tracks without repackaging:** in a file played as it is, Kodi switches audio and subtitle
  tracks itself. Arc repackages whenever the chosen audio isn't the file's default (a browser
  can't switch), so when that's the only reason the add-on now plays the file with its default
  track and has Kodi switch to the profile's (a read-only `playback-preview` decides). In a
  converted stream, audio and picture subtitles ask Arc again; text subtitles are Arc's WebVTT
  through a cast link, shifted to the stream's clock. Choices are saved to the profile, as the
  other apps do; the profile's subtitle mode and language choose the subtitles at the start.
- **Seeking a converted stream** outside what's converted restarts it there; a converted stream
  that ends early is picked up again from where it stopped (three times at most).
- **Resume point on Stop:** Kodi says 0:00 while it stops; the add-on now saves where it last was.
- **Home:** Down/Up move one row whichever Kodi version (Kodi's own move is followed, not
  repeated); rows run to the screen's right edge (also on the title page).
- **Rounded cards:** posters and wide cards are masked with rounded corners drawn at their exact
  size, with a matching focus ring.
- **Crisp logo, icons and pills:** the logo, mark, stacked logo and icons are rendered at exactly
  the size they're shown (they were large pictures shrunk by Kodi, which looked jagged), and the
  rounded shapes are drawn at 4x and scaled down (Pillow doesn't smooth curves).
- **Player icons** are Lucide's (as the web and Android players), in `tools/brand/osd/`.

## Checks

- `python3 -m pytest -q`: 35 passed. `python3 tools/check.py`: all good.
- In Kodi 20.5 (Linux, Xvfb, no GPU or audio device), against a scratch Arc with a 3-minute test
  file with two audio and two subtitle tracks and a sidecar subtitle file:
  - direct play; the controls (Select, Up, Down, Left/Right, the skip keys, Play/Pause, Info,
    Back to hide then stop) with no Kodi OSD appearing;
  - Subtitles menu: a track in the file (shown), a sidecar file (shown as Arc's WebVTT on a
    converted stream);
  - Audio menu on a converted stream (Arc: "another audio track chosen"); a profile's non-default
    audio language now plays the file as it is with Kodi switching to Japanese;
  - Quality 720 kbps (Arc converted from the playing position); seeking back before the
    converted part restarted the conversion there;
  - resume saved on Stop (1:35) and resumed;
  - Home Down/Up one row; rounded posters; rows to the right edge; logo and pills smooth.
- **Not checked:** Skip Intro with real markers, Up Next's countdown on a real episode end,
  passthrough, HDR, Dolby Vision, refresh-rate switching, any real device. Playback timing on the
  virtual display is unreliable (no audio device), so a converted stream ending early there may
  be the setup, not the add-on.
