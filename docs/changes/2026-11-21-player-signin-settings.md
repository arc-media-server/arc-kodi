# Player, sign-in, profiles and settings, as the Android app's (Kodi visual batch 4 of 4)

The last of four batches matching Kodi to the Android app (arc-android main: `PlayerOsdView.kt`,
`SignInScreen.kt`, `ProfilesScreen.kt`, `SettingsScreen.kt`, `PillTabs`). It builds on batch 3
(#46). Pictures are in `2026-11-21-player-signin-settings/`, as before/after pairs (`signin-*`,
`profiles-*`, `seasons-*`, `settings-*`).

## What changed

1. **Player controls.** The three round buttons are glass (white at 16%), 80 across and 20
   apart, with Android's gauge icon for Playback. The focused one's name shows above them, at the
   right. The Info, Chapters, Cast and Episodes tabs are sized to their words, 12 apart. The
   show's name large with "S1 · E3 · Title" above it, and the time under the playhead, were
   already as Android's.
2. **Audio menu.** An untagged track ("und") reads "Track 2" by its place, as Android's, not
   "Undetermined".
3. **Sign in.** Two columns: on the left the wordmark, "Sign in to Arc", three numbered steps
   (open Arc and choose Link a Device; or go to <server>/link; enter this code), then Get a New
   Code and Use Another Server as outlined pills. On the right the code in four boxes, "Waiting
   for you to enter the code…" with a spinner, and "Server: …". A code that isn't four characters
   shows whole.
4. **Who's watching?** The wordmark above the title, the server's name under it, larger avatars
   (gradient circles, 224 px), a white ring and the name bold when focused, 64 apart, and an
   outlined Sign Out pill below that goes back to the sign-in code (after Arc's question).
5. **Settings.** The profile's avatar (its colour, as on Who's watching?) large on the left with
   its name and the server; the rows are Android's (white at 6%, rounded corners, name at the
   left, value at 60% at the right). The order was already Android's.
6. **Season tabs** use the library's PillTabs (a holder with the chosen season's inner pill).

## Decisions

- **Sign In with Password stays**, as a quieter third choice under the two buttons (muted words,
  no pill until focused). Android has no password sign-in on TV; Kodi keeps it for a keyboard.
- **The avatar's gradient** is the profile's colour with a white sheen at the top left, since
  Kodi can't draw a gradient per item; it reads like Android's lighter-to-deeper fill.
- **The profile's colour is now kept with the chosen profile** (`profile_color` in
  `addon_data`), so Settings can draw the avatar.

## Checks

- `python3 -m pytest -q`: 177 passed. `python3 tools/check.py`: all good.
  `python3 tools/build_skin.py` and `python3 tools/make_media.py` rerun and committed (new: the
  gauge icon, code box, outlined pill, spinner, avatar sheen, Settings' row; removed the unused
  sliders icon).
- On screen, in Kodi 20.5 under Xvfb (1920×1080) with a fresh profile, against the shared
  screenshot library's scratch Arc, driven by remote keys over JSON-RPC: sign-in (code boxes,
  spinner, steps, buttons), Who's watching? (focus ring, Sign Out), the season tab, Settings.
- **Not seen on screen: the player controls and the audio menu.** The scratch episode didn't
  reach Arc's player window under Xvfb (no audio output), so the OSD changes are checked only by
  reading the skin. Sign Out from the profiles, a code of another length and "Track N" were not
  tried either.

No real hardware was used.

## Logging

Nothing new: Sign Out under the profiles goes through the existing sign-out, which logs as before.
