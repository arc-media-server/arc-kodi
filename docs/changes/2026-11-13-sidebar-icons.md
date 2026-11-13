# Sidebar: the apps' icons, and the logo on the icons' column

Owner's request: the sidebar uses the same icons as the Android and Apple apps, and the Arc logo
lines up with the buttons when the sidebar is closed.

## What changed

- **Icons:** the sidebar now draws the web and Android apps' icons (Lucide): search, home,
  bookmark (Watchlist), film / tv / clapperboard by library type, list-video (Playlists) and
  settings. They're kept as SVGs in `tools/brand/icons/` (the same shapes as Android's
  `ArcIcons.kt`) and rendered by `tools/make_media.py`, replacing the ones it used to draw.
  Lucide is ISC-licensed; its notice ships as `resources/LICENSE-lucide.txt`.
- **Alignment:** the logo files are cropped to their drawing, so the TV mark can be centred on the
  icons' column (x 84). When the sidebar opens, the full logo starts with the same TV at the same
  place and height, so only the name appears beside it.

## Decisions

- **Lucide, not SF Symbols.** The Apple app uses Apple's SF Symbols, which Apple licenses only for
  apps on its own platforms, so they can't ship in a Kodi add-on. Lucide is what the web and
  Android apps use, and the Apple app's sidebar shows the same set of places.

## Checks

- `python3 tools/check.py`: all good; `python3 -m pytest -q`: 29 passed.
- In Kodi 20.5 (Linux, Xvfb): measured on a 1920x1080 screenshot, the closed sidebar's TV mark is
  centred at x 83 and every icon at x 83.5; open, the full logo's TV starts at x 58, as closed.
