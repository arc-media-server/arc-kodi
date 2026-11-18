# Theme Music

Film and show pages now play their `theme_url` once per visit when the profile's `theme_music` preference is on (the default). Playback Settings includes **Theme Music**, immediately after Skip Intros Automatically, matching Android #38. String id 30540 is reserved for this feature.

The existing loopback artwork proxy also accepts the exact item-theme route, including its cache version. It adds the Bearer header locally and refuses theme redirects; Kodi only receives a loopback media URL. The session token stays out of Kodi's media URLs and databases. Episodes, missing themes and existing native playback do not start a tune.

## Decisions

Use Kodi's native audio player and existing device volume. Kodi's Python player API exposes no independent gain, so this client stops through its native stop rather than reproducing Android's quiet fade. Changing global system volume would affect other playback; no system volume is changed. This is the platform departure from Android/Plex-style quiet page themes.

Create the player on the main thread. A native onAVStarted callback cancels a theme that finishes opening after its visit was stopped, without stopping another source. Modal dialogs are detected with Kodi's `System.HasActiveModalDialog`, since the underlying window id does not change when a menu opens. Cancel a pending start before film/trailer playback or page navigation, stop on window close, screensaver or display sleep, and never stop a different source that has taken the native player. Returning from another page or playback does not replay a tune. Existing live profile updates stop a disabled theme; an initially disabled theme can start if enabled during its first visit.

## Checks and limits

- `python3 -m pytest -q`: 145 passed, including authenticated real loopback delivery against a stand-in Arc twice, refused non-theme routes, preference defaults and position, pending-start cancellation, native-player ownership, redirect refusal, cache-version routes and inactivity stops (navigation, closing, screensaver, display sleep, modal dialogs and shutdown).
- `python3 tools/check.py`: passed.
- `python3 tools/build_skin.py`: 16 windows rebuilt with no generated differences; source skin was unchanged.
- Actual Kodi 21.2 on Xvfb: the Settings switch saved both off and on against an isolated Arc, with three real 960×540 screenshots beside this note. Native audio played the generated MP3 through the authenticated loopback route, stopped on opening the title menu and did not replay after closing it. Live profile disable stopped the native theme; re-enabling did not replay it, and Kodi volume stayed unchanged. Modal-dialog and late-start regressions were observed failing before their fixes and pass afterwards.
- Not tried on a TV. Physical audio output, codec compatibility across Kodi devices and real-device volume behavior remain unverified. The virtual ALSA null sink consumes generated audio faster than real time; no listening or timing-quality claim is made.

## Logging

Only generic debug messages if starting or stopping a tune is unavailable. No names, credentials, URLs or query strings are logged. Existing proxy failures report an exception class only.
