# Arc for Kodi

A full-screen [Kodi](https://kodi.tv) client for
[Arc Media Server](https://github.com/arc-media-server/arc-media-server), in the style of
PM4K (Plex for Kodi): Arc's own interface for browsing and playing your films and shows, rather
than Kodi's library. It signs in to your Arc server with a code and uses only Arc's stable
`/api/v1`. It never changes your Kodi library — no scraping, no `.strm` files, no sync.

The look follows the [Apple app](https://github.com/arc-media-server/arc-apple) (artwork-led,
dark, white focus, an icon sidebar) with Arc's logo; how it behaves inside Kodi (windows, the player, the remote)
follows PM4K and Kodi's own settings.

Status: just started — a first version with sign-in, Home, library browsing, title pages and
playback. See `docs/changes/` for what's built and why.

## Installing

1. `python3 tools/package.py` writes `dist/script.arc-<version>.zip`.
2. In Kodi: **Add-ons → Install from zip file**, and pick that zip. (Allow unknown sources first,
   under Settings → System → Add-ons.)
3. Run **Arc** from Programs/Video add-ons. Enter your server's address, then open Arc on your
   phone or computer and choose **Link a Device** to approve the code.

Kodi 19 (Matrix) or newer. No extra Python packages are needed.

## For developers

- `python3 -m pytest -q` runs the `resources/lib/arc/` tests (the API client, Home rows and
  playback logic) against a stand-in server — no Kodi required.
- `python3 tools/check.py` checks the skin XML, the string ids, and that the `arc/` layer stays
  free of Kodi imports.
- Windows are written in `skin/`; `python3 tools/build_skin.py` builds the files Kodi loads
  (Kodi won't read an add-on's own includes, colours or fonts).
- `python3 tools/make_media.py` redraws the skin's PNGs and renders the logo files in
  `tools/brand/` (needs Pillow, and Node with Playwright's Chromium; dev only).
- Develop against a scratch Arc, never the owner's server. See `CLAUDE.md`.

## Licence

AGPL-3.0-only, copyright "The Arc Media Server Authors". See [LICENSE](LICENSE).
