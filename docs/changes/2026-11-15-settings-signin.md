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

## Password sign-in

- **The sign-in screen has "Sign In with Password"** under the code, for a keyboard (Kodi on a
  PC). It asks for the household password, signs in with it (`POST /auth/login`), and goes on to
  "Who's watching?". The code keeps working meanwhile. A wrong password says "That password wasn't
  right." The password goes to Arc and nowhere else: it isn't stored or logged.
- It types into Kodi's own keyboard for now; an Arc on-screen keyboard comes with search
  (feature-parity item 5).

## The PIN pad

- **A profile's PIN goes into Arc's own PIN pad** (`kodi/windows/pin.py`, `script-arc-pin.xml`)
  in place of Kodi's number dialog:
  - the profile's name and four dots that fill as digits go in;
  - round keys 1-9, 0 and Delete, plus the remote's own number keys and Backspace;
  - the fourth digit sends it, as Arc's PINs are four digits.
- The pad opens before asking Arc for a profile with a PIN (no refused request first). A wrong
  PIN brings it back saying "That PIN wasn't right."

Checked in Kodi on a virtual display: signed out from Settings, signed in with the scratch
server's password; with a PIN set on the scratch profile, four wrong digits brought the pad back
with the message, and the right ones on the remote's number keys opened Home.

## Logging

- "settings changed: <key>" (info), or a warning naming the error type when not saved.
- "signed in with the password" (info), or "password sign-in failed (wrong password | error type)".
  Never the password.
