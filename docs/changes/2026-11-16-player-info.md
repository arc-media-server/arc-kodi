# Player Info: what the player reports, in Arc's look

The owner wanted what the player is reporting while it plays, as Kodi's Player Process Info and
CoreELEC skins show it (the Dolby Vision profile, the layers, what the TV is sent), and in
Arc's look rather than the skin's.

## What changed

- **Player Info** in Arc's player: the O key (Kodi's Player Process Info key) or Playback >
  Player Info opens it, Back or O again closes it. A dark rounded panel at the top left with
  sections (Video, Dolby Vision, Display, Audio, Arc), muted names and white values, read from
  Kodi again every second. It stays while the film plays.
- What it shows, from Kodi's live labels:
  - **Video:** the decoder and whether it's hardware or software, size, frame rate and scan,
    pixel format, HDR type (`VideoPlayer.HdrType`), deinterlacing.
  - **Dolby Vision** (CoreELEC builds with `Player.Process(video.sidedata)`): the profile with
    its base layer's compatibility and level ("7.6 · level 6"), single or dual layer and how a
    dual layer stream is packaged (one track or two), and what the device changed
    (converted, RPU removed, HDR10+ removed, L5 zeroed). Read from the Dolby Vision
    configuration record in the side data (`arc/playerinfo.py`, tested).
  - **Display:** on CoreELEC, `amlogic.displaymode` and the EOTF, colour space and pixel format
    sent to the TV (`amlogic.eoft_gamut`, `amlogic.pixformat`); elsewhere Kodi's screen mode.
  - **Audio:** decoder and channels, sample rate and bits, and on CoreELEC what the audio sink
    was opened with.
  - **Arc:** played as it is, repackaged or converted, and why.
- Rows Kodi doesn't know are left out: Kodi hands back a label's own text for one it doesn't
  know (CoreELEC's on other builds), or says "unknown" or 0; a section with nothing is left out.
- The skin's own Player Process Info is closed if Kodi opens it, as Arc's player does with
  Kodi's other dialogs.

The CoreELEC label names are CoreELEC's own (`xbmc/guilib/guiinfo/CEGUIInfoLabels.dox` in
CoreELEC/xbmc, branch aml-6.12.69-23.0); older CoreELEC builds have only the `amlogic.*` three.

## Not done

FEL or MEL for profile 7: the side data's RPU says which, but reading it means parsing the RPU
bitstream; the panel says "dual layer" until that's added. Needs a CoreELEC box to check.

## Logging

Debug: "player info shown", and "player info not drawn (<error>)" if drawing fails.

## Checked

Kodi on Xvfb (plain Kodi, software decoding, no audio device) against a scratch Arc: the panel
opened with O, showed Video, Display and Arc, left out the unknown rows, and Back closed it.
The Dolby Vision and CoreELEC rows are covered by tests with made-up side data only: they need a
CoreELEC box to check on real hardware.
