# Settings, password sign-in and the PIN pad

Feature-parity item 4. Built on PR #6.

## Settings

The Settings screen is now the Apple app's (SettingsView):

- At the left: the profile's name, the server's, and the TMDB/TheTVDB attribution.
- **Playback**, saved to the profile on Arc (`PATCH /me/prefs`) so every app follows them:
  - Auto-Play Next Episode, On or Off;
  - Skip Intros Automatically, On or Off;
  - Subtitles: "In the language I last chose", "When the audio is in another language", "Always"
    or "Only when I choose them" (Arc's `subtitle_mode`).

  The player reads them as it starts, so a change applies from the next title. If Arc can't save
  one, it says so and nothing changes.
- **Profile and Server**: Switch Profile, Sign Out, and Change Server. Change Server asks first,
  then signs out, forgets the server and shows the connect screen.
- **About**: the add-on's version.
- Each row's value shows at its right. After a change only the values update, in place:
  refilling the list moved the focus and lost a key pressed meanwhile.
- The rows, their values and the changes they make are `arc/settings.py`, with tests.

Checked in Kodi on a virtual display: Skip Intros turned on and Subtitles set to "When the audio
is in another language", both seen saved on the scratch server, with quick presses in between.
