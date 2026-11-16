# Paused: Arc's controls, never the skin's bar; the resolution setting's name

Two things found while taking the README's screenshots.

## Pausing

- When playback paused with Arc's controls hidden, the skin's own "Paused" bar (its seek bar,
  which the skin opens by itself on pause and seek) showed across the top: Arc's top shading
  (#20) was drawn only while Arc's controls showed.
- Now Arc's controls come up when playback pauses, as Plex's and the Apple player's do (not
  in a Watch Together lobby, or before the stream has started), and stay while paused. The top
  shading shows whenever Arc's controls do or the skin's seek bar is open, so the skin's bar is
  covered after a seek too.

## The resolution setting

The add-on's one Kodi setting (the largest picture to ask for: 4K, 1080p or 720p) was labelled
"Rating" in Kodi's add-on settings: it used the Sort menu's string. It's now "Maximum
Resolution" (a new string, 30454).

## Logging

Nothing new.

## Checked

Kodi on Xvfb against a scratch Arc: Interstellar paused with the controls hidden; Arc's
controls came up with the overview and the top shaded, while Kodi reported its seek bar open
underneath. The settings label wasn't looked at in Kodi's dialog. Not on real hardware.
