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
| Row looks from the server (posters, thumbnails, Backdrops) | Both | Done | Yes | Backdrops are the web's squarer cards with the logo. |
| An episode's card opens its show, on its season and episode | Apple | Done | Yes | No episode page. |
| Remove from Continue Watching | Android | Done | Yes | In the card menu, on Continue Watching. |
| Menus and questions in Arc's style (card menu, Sort, Filter, pickers, Sign Out) | Both | Done | Yes | One Arc menu; Kodi's keyboard and PIN number pad remain (see Search and PINs). |
| Watch Together row | Apple | Missing | Yes | With Watch Together. |
| Library: Recommended / Browse / Collections / Folders pills | Both | Part | Yes | Recommended (the server's rows under a hero), Browse and Collections; no Folders (Other videos) yet. |
| Library sort and filter (genre, unwatched, decade, resolution...) | Both | Part | Yes | Sort and unwatched only. |
| Posters: unwatched count tab, progress bar, watched tick, year · length | Both | Done | Yes | |
| Paging large libraries | Both | Done | Yes | |
| Collection, playlist, person and folder pages | Both | Part | Yes | Playlists, the watchlist, a person (from Cast) and a collection open as a plain grid; no proper person, collection or folder pages yet. |
| Search as you type; results in rows (films, shows, episodes, people, collections, genres) | Both | Part | Yes | Kodi's keyboard dialog, then one grid of films/shows/episodes. An on-screen keyboard gives as-you-type. |
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
| Context menu on any card (Play, watched, watchlist, go to show) | Both | Done | Yes | Arc's own menu on Home, grids, search and the title page. |

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
| Subtitle style (size, colour, background) | Both | Missing | Part | Kodi draws subtitles with its own style settings; follow Kodi's. |
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
| Passthrough (AC3, E-AC3, DTS, TrueHD, DTS-HD) | Both | Yes (Kodi) | Yes | Kodi's own audio output settings (owner, 13 November); not yet checked on hardware. |
| HDR10 / HLG / HDR10+ | Both | Yes (Kodi) | Yes | The original is sent and Kodi handles HDR output and tone mapping (owner, 13 November); not yet checked on hardware. |
| Dolby Vision (profile 5, 7 with FEL, 8) | Both (by device) | Yes (Kodi) | Part | The add-on no longer limits DV profiles: the original is sent and Kodi (e.g. CoreELEC on the AM6B+) plays or converts it (owner, 13 November). Not a promise of native DV output; not yet checked on hardware. |
| Refresh rate / resolution matching | Both | Yes (Kodi) | Yes | Kodi's own "Adjust display refresh rate" setting. |

## Platform integration

| Feature | Apple / Android | Kodi now | Kodi can | Notes |
|---|---|---|---|---|
| Top Shelf (Apple) / Watch Next channel (Android) | Both | Missing | Part | Kodi's nearest is skin home widgets, which need a `plugin://` source; that's against this add-on's rule today. An owner decision (#80). |
| Updates without a zip (a Kodi repository) | Stores | Missing | Yes | A repository add-on, as other Kodi add-ons ship. |
| Automatic build of the install zip | — | Missing | Yes | A GitHub Action on push. |

## Suggested order

Done: real-device policy (owner, 13 November: Kodi owns format compatibility, so no per-device
rules; hardware checks still to do on the AM6B+), title page parity, and Arc's own menus.

1. **Library parity:** Recommended, Collections and Folders pills; filters; the unwatched tab;
   person, collection and folder pages; Play All / Shuffle.
2. **Player extras:** chapters, timeline thumbnails, the Info/Episodes tabs, speed.
3. **Settings screen** (Auto-Play, Skip Intros, subtitle mode), a password sign-in and an Arc
   PIN pad.
4. **Search** with an on-screen keyboard and rows; **live updates**.
5. **Watch Together**.
6. **Distribution:** the zip built on push, then a Kodi repository for updates.
