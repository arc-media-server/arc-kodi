# Send Invite; Kodi's own player dialogs kept out of sight

The owner asked for the Watch Together invite screen's "Invite" to read "Send Invite", and for a
look at what still brings up Kodi's own menus and dialogs instead of Arc's.

## Send Invite

The invite screen's button (string 30344) now says **Send Invite**.

## Kodi's dialogs in the player

Checked in Kodi (Estuary) with its window log:

- **The skin's seek bar and "Paused" bar.** Kodi's skin opens its own `DialogSeekBar` (and, in
  Estuary, a "Paused 0:03 / 0:03" bar across the top) by itself whenever playback is paused or
  seeking. Closing it doesn't work: the skin reopens it at once while the condition holds (tried:
  it flickered open and closed every 250 ms). So Arc's player now draws above the skin's dialogs
  (`<zorder>100</zorder>`, as PM4K's player) and shades the top of the picture while its controls
  show (`arc-osd-top.png`: solid for the top 120 px, then fading), which covers the skin's bar.
- **The delay slider.** Moving the audio or subtitle offset steps Kodi's AudioDelay/SubtitleDelay
  actions (Kodi has no call to set them), and each step opened Kodi's own slider for a second, at
  the start of every playback when this device has an audio offset saved. Arc now closes it
  straight after the steps.
- **Kodi's OSD, info panel and slider opened some other way** (a key Kodi still handles): Arc's
  player closes them as they appear, as PM4K's does. A busy spinner left open once playing, with
  nothing loading, is closed too (PM4K's rule).

## What still shows Kodi's own dialogs (not changed here)

- **Typing:** the server address on the first screen, the household password and a Watch
  Together code use Kodi's keyboard (`Dialog().input`), drawn by the user's skin.
- **Short messages:** a handful of failures and notices use Kodi's notification toast (sign-in
  errors, a card action not saved, a play queue that couldn't start, Watch Together notices).
- **Opening a stream:** Kodi's busy spinner shows while Kodi opens the stream, as in PM4K.

Each could become Arc's own (its on-screen keyboard from Search, a toast in Arc's windows); left
for the owner to choose.

## Logging

Debug only: "closed Kodi's <dialog>" and "closed a stuck busy dialog".

## Checked

Kodi on Xvfb against a scratch Arc, Estuary skin: Kodi's slider now opens and closes in the same
millisecond at playback start; paused with Arc's controls up, the skin's seek bar is open
underneath but hidden (screenshots). Not on real hardware or other skins.
