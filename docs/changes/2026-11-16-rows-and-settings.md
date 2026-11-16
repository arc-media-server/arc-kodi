# Row titles, the episode description, and Settings redone

The owner tested the add-on and reported three problems (relayed from the server chat).

## 1. Row titles cut off going up

On Home, going down was fine, but going back up left the row's title scrolled off. Each row's
title and list were separate children of the vertical grouplist, and a grouplist scrolls only
far enough to show the focused control: going up it lined the list's top up with its own, so the
title above it was off-screen.

- Each row (`PosterRow`, `ThumbRow`, `BackdropRow` in `skin/includes.xml`, and the hand-written
  Cast, People and Genres rows) is now one `group`: the title on top, the list under it. The
  group is what the grouplist scrolls into view, so the title shows whichever way the focus comes.
  The includes take `list_top` and `group_height` (Kodi's includes can't add).
- Kodi's grouplist can't move the focus into a child group (vertical as well as horizontal, even
  with `<defaultcontrol>`). Home already stepped between rows itself; the title page and search
  now do too, through `ArcWindow.ROW_STOPS` (their rows top to bottom): when Up/Down leave the
  focus where it was, the window focuses the next visible row that way. Search's Right from the
  keyboard's edge goes into the first row of matches the same way.
- Same rows on Recommended, a person's page, the title page and search.

## 2. The episode description off-screen

On a show's page, landing on the episodes didn't show the focused episode's description (textbox
202): it was a separate grouplist child under the episode list, so the page stopped scrolling at
the list's foot. The episodes and their description are now one group (room for three lines), so
the description shows the first time the focus lands there.

## 3. Settings, as the Android and Apple apps'

The owner called the old screen awful: every row 88 high with a section line inside it (uneven
gaps, headings inside rows), bare text with no row backgrounds, and only three of the profile's
choices.

- **Layout:** the page's name at the top; at the left, centred, the profile's initials in a
  circle, its name, the server and the add-on's version, with the TMDB/TheTVDB attribution at the
  foot; at the right the list.
- **Sections with real headings** between them: Playback, Subtitles, Watch Together (where Arc
  allows it), Profile and Server, About. Every row is a dark rounded pill with its name at the left
  and its value at the right; the focused row is white with black text. Headings and notes can't
  be chosen: the window steps over them (and Up from the first row stays put).
- **The profile's choices** (all keys `/api/v1/me/prefs` already has):
  - Playback: Auto-Play Next Episode, Skip Intros Automatically, **Hide Spoilers**
    (`hide_spoilers`), **Preferred Audio Language** (`audio_language`, or the file's default);
  - Subtitles: Show Subtitles (`subtitle_mode`), **Subtitle Language** (`subtitle_language`), and
    **Size, Colour, Background, Position** (`subtitle_style`, sent whole, as the apps do), with
    the Android app's choices and words.
  - Choices open Arc's menu with the current one ticked. Languages are the apps' list, named by
    Kodi.
- **Said plainly under the sections:** Kodi doesn't hide spoilers yet (the next feature on the
  owner's list), and Kodi draws subtitles in its own style, so size, colour, background and
  position apply in Arc's other apps.
- Kodi checks a list's layout `condition` once for the whole list, not per entry, so headings,
  rows and notes share one 76-high slot and show their parts by `ListItem.Property(kind)`.
- The entries and values are `arc/settings.py` (`layout`, `choices`, `value`, `change`), tested
  in `tests/test_settings.py`.

## Checked

- `python3 -m pytest -q`: 96 passed. `python3 tools/check.py`: all good. `python3
  tools/build_skin.py`: built 13 windows.
- Kodi 20 on a virtual display against a scratch Arc (not real hardware), with before (main) and
  after screenshots in `docs/screens/2026-11-16-rows-settings/`:
  - Home: down two rows and up one: on main "Recently Added in Films" was gone; now it shows.
    Down still shows each title. Recommended: down three rows and up one keeps the title.
  - Firefly's page: down to the episodes: on main no description; now Ariel's shows under the row.
    Down and up through every row moves one row per press (seasons, episodes, Cast, Related, the
    cards).
  - Search: Right from the keyboard's edge into the matches.
  - Settings: the new list; Down and Up step over the headings and the notes; Background →
    "Outline only" saved `subtitle_style` whole (put back afterwards).

## Logging

Nothing new: "settings changed: <keys>" (info) and "settings change not saved" (warning), as
before.
