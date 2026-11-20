# Episode numbers written the one Arc way

The owner's rule for every Arc app (arc-media-server `docs/AGENT-RULES.md`, "Episode numbers",
arc-media-server#493): "S1 · E4", no leading zeros, "·" as the only separator, "Special 3" for
season 0. A card's line under the show's name is just the number; where the episode itself is
the subject, its title follows ("S1 · E4 · Pilot"); buttons read "Play S1 · E4" and
"Resume S1 · E4".

## What changed

- **One place makes the text:** `arc/models.py` `episode_code` (the number, or "Special 3") and
  `episode_heading` (number then title, or the title alone outside the show's order). The words
  come from the catalogue: `S%d · E%d` (30172) and the new `Special %d` (30603), passed in by the
  Kodi side's `episode_code()` and `episode_heading()` beside `T()` in `kodi/compat.py`.
- **Cards** (Continue Watching, search, library, More Like This): the line under the title is now
  just "S1 · E4". Continue Watching's cards used to add the title again ("S1 · E2 · Half Loop"
  under "Half Loop").
- **Home's info line** over the artwork: "S1 · E2 · Half Loop" (it was "S1 · E2  Half Loop").
- **Episode lists** (the title page's season row and the player's Episodes list): "S1 · E4 ·
  Pilot" (they were "4. Pilot"). Episodes outside the show's order still show only their title.
- **The player's title line and Up Next:** "S1 · E4 · Pilot" (they were "S1, E4 · Pilot"); string
  30222 (`S%d, E%d · %s`) is gone.
- **Specials** everywhere: "Special 3", never "S0 · E3".
- The title page's Play and Resume buttons already read "Play S1 · E4" / "Resume S1 · E4"; they
  now share the same helper, so a special reads "Play Special 3". The add-on has no "Start
  watching" button.

## Pictures

The README's Home and show pictures are retaken: Home's Continue Watching cards now read
"S1 · E2" under the title, and Breaking Bad's episode row reads "S1 · E1 · Pilot". The other
pictures show no episode numbers.

## Checks

- `python3 -m pytest -q`: 167 passed (new tests for the number, specials, the heading and the
  catalogue's words; the old `episode_label` test is replaced).
- `python3 tools/check.py`: all good. `python3 tools/build_skin.py`: no change to the built
  windows (only a comment in `skin/script-arc-player.xml`).
- Kodi 20.5 under Xvfb (1920×1080) with a fresh profile against the shared screenshot library's
  scratch Arc (arc-media-server main, `node tools/screenshots.mjs --serve`), signed in as Jordan
  the same way as `tools/readme_shots.py`: looked at Home, Breaking Bad's page and the player's
  Up Next ("S1 · E4 · Cancer Man"). No special was on screen there; specials are covered by the
  tests.

No real hardware was used.

## Logging

None: only text on screen changes.
