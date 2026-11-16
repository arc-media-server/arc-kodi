# Play Version…

A title with more than one version (a 4K and a 1080p file, a Director's Cut beside the standard
cut) can now be played in a chosen version before playback starts, as Plex's and the Android
app's Play Version….

## What changed

- The ⋯ menu (Context Menu) of a film or episode with more than one version on disk offers
  **Play Version…**, after Play/Resume. It opens **Choose Version**: each version by its edition
  (or else its resolution), with its picture, sound and size beside it ("Final Cut · SD · 47 KB",
  "4K · DV · HDR10 · Atmos · 7.1 · 60.0 GB"). The chosen one plays from the profile's resume
  point; the player then keeps that file for the whole playback (a restart, a seek outside what's
  converted, a track change).
- Play itself is unchanged: Arc picks the version (the standard edition, one that needs no
  conversion, then the sharpest within the add-on's resolution limit). The player's Playback
  menu still switches version mid-playback.
- Versions are a title's files on disk, the first part of each (as the player's list and the
  Android app's `versionsOf`). Arc's lists of titles leave out files, so the entry shows where
  the whole title is known: the title page's ⋯ menu always, and cards from rows that carry files
  (Continue Watching, Up Next).

`models.versions`, `models.file_badges` (the title page's quality badges, now for any file) and
`titlepage.version_label` are plain Python with tests; `menus.card_actions` adds `play_version`.

## Logging

Info: "playing a chosen version (N of M)". Then the player's usual lines.

## Checked

Kodi on Xvfb against a scratch Arc: Blade Runner (Final Cut and Theatrical Cut) offers Play
Version… on its page; Choose Version lists both; choosing the Theatrical Cut played it. Films
with one version don't offer it. Not on real hardware.
