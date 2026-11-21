# Rows land in the same place going down or up; Recommended's first row at the foot

**What:** on Home and a library's Recommended tab the focused row now always lands at the foot
of the screen, whether you move down or back up (it used to land at the foot going down but at
the top going up). On Recommended the rows now have Home's sizes, so Continue Watching sits at
the foot under the hero as on Home, instead of with empty space below it.

**How:** Kodi's grouplist scrolls only as far as the focused control: to its top going up, to its
foot going down. Each row is now a group as tall as the row list (1080 on Home, 950 under
Recommended's tabs) with the title and cards at its foot, so both scrolls show the row in the same
place. A negative item gap (half the list's height) overlaps those groups, and a spacer before
each row (the row's own height, shown with it) sets the distance between rows, so the rows look as
before. `home.py` sizes the hero on Recommended too (it used the skin's fixed height), from the
list's height. Other windows using the row includes are unchanged (the new `title_top` parameter
defaults to 0).

**Checks:** `tools/build_skin.py`, `tools/check.py` (all good), pytest (186 passed). Real Kodi 20.5
(Linux, Xvfb) against a scratch server: Home down three rows and back up, and Recommended down two
and back up. The rows focused going down and going back up are pixel-identical in place; Up
from Recommended's first row still reaches the tabs. Screenshots in `2026-11-21-row-scroll/`.
Not tried on a TV box or with a mouse.

**Logging:** nothing new.
