# Keep Arc on screen when opening a profile

Kodi's profile picker closes before Arc loads the chosen profile's settings and
libraries. Kodi used to restore its own interface during that wait. Arc now
keeps its loading screen underneath the picker and Home, so the transition stays
inside Arc. Exiting Arc returns to the Kodi interface.

Home and Recommended cards use two caption lines again. Episode cards show
the series name and season/episode number with the same left alignment as the
other media cards.

## Checks

- Regenerated the skin. `tools/check.py`, `git diff --check`, and all 191 pytest
  tests passed.
- Used Kodi on a virtual display with a two-second profile load. The profile
  picker handed off to Arc's loading screen and then Home. Back from Home
  returned to Kodi. Checked the episode card caption on Home with fixture data.
  Physical hardware was outside these checks.

[Profile picker](2026-11-26-kodi-profile-transition/picker.jpg) ·
[Loading screen](2026-11-26-kodi-profile-transition/transition.jpg) ·
[Home](2026-11-26-kodi-profile-transition/home.jpg)

## Logging

Existing launch and profile-loading logs cover the transition.
