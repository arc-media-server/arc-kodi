# Feature parity with the Apple and Android apps (plan)

What the Apple TV app (arc-apple) and the Android TV app (arc-android) do, what Arc for Kodi does
today, and how close Kodi can get. Written 13 November from those repos' `docs/changes/` and code;
update it as items land. Product decisions it raises go on arc-media-server#80.

Status: **Done**, **Part** (started, gaps named), **Missing**. Kodi: **Yes** (Kodi can match it),
**Part** (close, with a Kodi limit named), **No** (Kodi can't, or it isn't wanted here).

## Sign-in, profiles, settings

| Feature | Apple / Android | Kodi now | Kodi can | Notes |
|---|---|---|---|---|
| Connect by address | Both | Done | Yes | |
| Sign in with a code (Link a Device) | Both | Done | Yes | |
| Sign in with the password | Android | Missing | Yes | For keyboards (PC Kodi). |
| "Who's watching?" with PINs | Both | Part | Yes | Uses Kodi's number dialog; an Arc PIN pad would match. |
| Switch profile, sign out | Both | Done | Yes | |
| Settings: Auto-Play, Skip Intros automatically, subtitle mode (saved to the profile) | Both | Missing | Yes | They're read from the profile already; there's no screen to change them. |
| About (server, version) | Both | Part | Yes | |

## Home and browsing

| Feature | Apple / Android | Kodi now | Kodi can | Notes |
|---|---|---|---|---|
| Icon sidebar, opens on focus | Both | Done | Yes | |
| Hero follows the focused card (logo, details, overview) | Both | Done | Yes | |
| Rows as the web arranges them (Continue/Up Next, libraries, watchlist, collections, playlists, seasonal) | Both | Done | Yes | |
| Continue Watching shows the show's art | Both | Done | Yes | |
| Remove from Continue Watching | Android | Missing | Yes | Context menu. |
| Watch Together row | Apple | Missing | Yes | With Watch Together. |
| Library: Recommended / Browse / Collections / Folders pills | Both | Part | Yes | Browse only; no Recommended, Collections or Folders pages. |
| Library sort and filter (genre, unwatched, decade, resolution...) | Both | Part | Yes | Sort and unwatched only. |
| Posters: unwatched count tab, progress bar, watched tick, year · length | Both | Part | Yes | No unwatched count tab yet. |
| Paging large libraries | Both | Done | Yes | |
| Collection, playlist, person and folder pages | Both | Part | Yes | Playlists and the watchlist use a plain grid; no person, collection or folder pages. |
| Search as you type; results in rows (films, shows, episodes, people, collections, genres) | Both | Part | Yes | Kodi's keyboard dialog, then one grid of films/shows/episodes. An on-screen keyboard (as PM4K's) gives as-you-type. |
| Live updates (new titles, watched state from other devices) | Both | Missing | Yes | Arc's event stream (SSE) with urllib; refetch on change. |

## Title page

| Feature | Apple / Android | Kodi now | Kodi can | Notes |
|---|---|---|---|---|
| Hero: logo, info line, overview | Both | Done | Yes | |
| Background in the artwork's four colours (palette) | Apple | Done | Part | Kodi has no mesh gradient; four tinted corner glows under the artwork. |
| Quality badges as capsules (4K, DV, HDR10, Atmos, 5.1) | Both | Done | Yes | |
| Play label says what plays (Resume 1:02:03, Play S1 E4) | Both | Done | Yes | |
| Play from the beginning on the page | Both | Done | Yes | Round button beside Play. |
| Watched, Watchlist buttons | Both | Done | Yes | Round icon buttons; the focused one's name shows beside them. |
| Seasons and episodes; opens on the next to watch | Both | Done | Yes | |
| Episode browser rises over the hero (reference look) | Apple | Part | Yes | The page scrolls the hero up as focus moves down; no separate sheet. |
| Upcoming episodes dimmed with "Releases 8 Nov" | Apple | Done | Yes | |
| About, Details, Crew and Playback cards | Both | Done | Yes | |
| Cast & Crew row (opens the person) | Both | Done | Yes | The person opens as a grid of their titles; a proper person page comes with library parity. |
| Related / More like this | Both | Done | Yes | |
| Collections row | Both | Done | Yes | |
| Trailers & Extras | Both | Done | Yes | Played through Arc's player, without progress. Not yet seen with real extras (the test library has none). |
| Versions (editions) choice before playing | Android | Missing | Yes | In the player's Playback menu now. |
| Play All / Shuffle (play queues) | Android | Missing | Yes | Arc's play-queues API. |
| Context menu on any card (Play, watched, watchlist, go to show) | Both | Part | Yes | Kodi's context menu now; an Arc-styled one would match. |

## Player

| Feature | Apple / Android | Kodi now | Kodi can | Notes |
|---|---|---|---|---|
| Arc's own controls: title, round buttons, timeline | Both | Done | Yes | This change. |
| Left/Right skip 10 s, presses add up | Both | Done | Yes | |
| Chapters marked on the timeline; Chapters list | Both | Missing | Yes | |
| Timeline thumbnails while skipping | Both | Missing | Part | Arc's BIF files hold single JPEGs: the add-on can unpack them; Kodi can't crop a sprite sheet. |
| Tabs: Info, Chapters, Cast, Episodes | Apple | Missing | Yes | |
| Audio menu | Both | Done | Yes | Kodi switches tracks itself in a file played as it is. |
| Subtitles menu (in the file, beside it, picture subtitles burnt in when converted) | Both | Done | Yes | |
| Subtitles chosen by the profile's mode and language | Both | Done | Yes | |
| Quality and Version menus | Both | Done | Yes | |
| Playback speed | Android | Missing | Part | Kodi 20+ has tempo (0.8–1.5×) where the platform supports it. |
| Subtitle style (size, colour, background) | Both | Missing | Part | Kodi draws subtitles with its own style settings; follow Kodi's (PM4K does). |
| Audio and subtitle delay | — | Missing | Yes | Kodi's own; not in the other apps either. |
| Skip Intro / Recap / Credits; skip by itself | Both | Done | Yes | Not yet seen with real markers (the test library has none). |
| Up Next with countdown | Both | Done | Yes | |
| Resume and progress on the source timeline; conversions kept alive and ended | Both | Done | Yes | |
| Seek outside what's converted restarts there | Both | Done | Yes | |
| A file Kodi can't play is tried again converted | Both | Done | Yes | |
| Watch Together | Both | Missing | Yes | Room events (SSE), heartbeats, following the room's position. A larger piece. |

## Playback technology (Kodi's own player does the work)

| Feature | Apple / Android | Kodi now | Kodi can | Notes |
|---|---|---|---|---|
| Direct play of MKV/MP4, HEVC/AV1, TrueHD/DTS | Both (by device) | Done | Yes | Kodi plays more as it is than either app. |
| Passthrough (AC3, E-AC3, DTS, TrueHD, DTS-HD) | Both | Part | Yes | Read from Kodi's settings; needs checking on hardware. |
| HDR10 / HLG / HDR10+ | Both | Part | Yes | Read from Kodi's display info (Kodi 20+). Unchecked. |
| Dolby Vision (profile 5, 7 with FEL, 8) | Both (by device) | Part | Part | Kodi reports DV only where the platform has it. On CoreELEC (Ugoos AM6B+) profiles 5, 7 (FEL) and 8 play; the add-on claims only 8 now, so 5 and 7 would be converted. Needs widening and checking on the AM6B+. |
| Refresh rate / resolution matching | Both | Yes (Kodi) | Yes | Kodi's own "Adjust display refresh rate" setting, as PM4K. |

## Platform integration

| Feature | Apple / Android | Kodi now | Kodi can | Notes |
|---|---|---|---|---|
| Top Shelf (Apple) / Watch Next channel (Android) | Both | Missing | Part | Kodi's nearest is skin home widgets, which need a `plugin://` source; that's against this add-on's rule today. An owner decision (#80). |
| Updates without a zip (a Kodi repository) | Stores | Missing | Yes | A repository add-on, as PM4K ships. |
| Automatic build of the install zip | — | Missing | Yes | A GitHub Action on push. |

## Suggested order

1. **Real-device checks on the AM6B+** (direct play, passthrough, HDR10, DV) and widening the DV
   profiles Kodi claims on CoreELEC.
2. **Title page parity:** About/Details/Crew/Playback cards, cast row, badges as capsules, Play
   labels, Play from the beginning, extras, collections row, the episode browser.
3. **Library parity:** Recommended, Collections and Folders pills; filters; the unwatched tab;
   person, collection and folder pages.
4. **Player extras:** chapters, timeline thumbnails, the Info/Episodes tabs, speed.
5. **Settings screen** (Auto-Play, Skip Intros, subtitle mode) and a password sign-in.
6. **Search** with an on-screen keyboard and rows; **live updates**.
7. **Watch Together**.
8. **Distribution:** the zip built on push, then a Kodi repository for updates.
