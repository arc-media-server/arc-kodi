#!/usr/bin/env python3
"""Draws the skin's PNGs (icons, pills, gradients, logo) so none are committed by hand. Run it
after changing a colour or shape and commit what it writes. Needs Pillow (dev only; Kodi never
runs this).

    python3 tools/make_media.py
"""

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "resources", "skins", "Main", "media")
RES = os.path.join(ROOT, "resources")

BG = (28, 29, 33, 255)
SURFACE = (38, 39, 45, 255)
SURFACE2 = (47, 48, 56, 255)
WHITE = (255, 255, 255, 255)
ACCENT_LIGHT = (127, 220, 205)
ACCENT_DARK = (11, 125, 114)


def _rounded(size, radius, fill):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=fill)
    return img


def pill(name, fill):
    # A nine-slice rounded pill: 80x80, radius 40, so border=8..40 keeps the corners crisp.
    _rounded((80, 80), 40, fill).save(os.path.join(MEDIA, name))


def round_button(name, fill):
    img = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([0, 0, 79, 79], fill=fill)
    img.save(os.path.join(MEDIA, name))


def card_border():
    img = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(3):
        d.rounded_rectangle([i, i, 23 - i, 23 - i], radius=6 - i, outline=WHITE)
    img.save(os.path.join(MEDIA, "arc-card-border.png"))


def wash():
    # Arc's soft grey blend, cooler top-left to warmer bottom-right.
    w, h = 320, 180
    img = Image.new("RGB", (w, h))
    px = img.load()
    tl, br = (37, 40, 45), (30, 31, 30)
    for y in range(h):
        for x in range(w):
            t = (x / w + y / h) / 2
            px[x, y] = tuple(int(tl[i] + (br[i] - tl[i]) * t) for i in range(3))
    img.save(os.path.join(MEDIA, "arc-wash.png"))


def scrim(name, top_alpha, bottom_alpha, left_bias=False):
    w, h = 16, 256
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        a = int(top_alpha + (bottom_alpha - top_alpha) * (y / (h - 1)))
        for x in range(w):
            px[x, y] = (0, 0, 0, a)
    img.save(os.path.join(MEDIA, name))


def side_focus():
    img = _rounded((360, 88), 16, SURFACE2)
    img.save(os.path.join(MEDIA, "arc-side-focus.png"))


def progress_scrim():
    # A faint dark band across the foot of a poster that's part-watched.
    w, h = 244, 366
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, h - 10, w, h], fill=(0, 0, 0, 160))
    d.rectangle([0, h - 6, int(w * 0.45), h - 2], fill=(*WHITE[:3], 255))
    img.save(os.path.join(MEDIA, "arc-progress-scrim.png"))


def logo(path, size=(512, 512), mark_only=False):
    # The Arc mark: an arc stroke with a dot, in the logo gradient (#7fdccd -> #0b7d72).
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = size
    grad = Image.new("RGBA", size, (0, 0, 0, 0))
    gpx = grad.load()
    for y in range(h):
        for x in range(w):
            t = (x / w + y / h) / 2
            gpx[x, y] = tuple(int(ACCENT_LIGHT[i] + (ACCENT_DARK[i] - ACCENT_LIGHT[i]) * t) for i in range(3)) + (255,)
    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)
    cx, cy, r = w // 2, int(h * 0.62), int(w * 0.32)
    sw = max(8, int(w * 0.09))
    md.arc([cx - r, cy - r, cx + r, cy + r], start=200, end=340, fill=255, width=sw)
    md.ellipse([cx - sw // 2, cy - sw // 2, cx + sw // 2, cy + sw // 2], fill=255)
    img = Image.composite(grad, img, mask)
    img.save(path)


def icon():
    img = Image.new("RGBA", (512, 512), BG)
    logo_img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    logo(os.path.join(MEDIA, "_tmp_logo.png"))
    mark = Image.open(os.path.join(MEDIA, "_tmp_logo.png"))
    img.alpha_composite(mark)
    img.convert("RGB").save(os.path.join(RES, "icon.png"))
    os.remove(os.path.join(MEDIA, "_tmp_logo.png"))


def fanart():
    img = Image.new("RGB", (1280, 720))
    px = img.load()
    for y in range(720):
        for x in range(1280):
            t = (x / 1280 + y / 720) / 2
            px[x, y] = tuple(int((37, 40, 45)[i] + ((18, 18, 20)[i] - (37, 40, 45)[i]) * t) for i in range(3))
    img.save(os.path.join(RES, "fanart.jpg"), quality=88)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    pill("arc-pill-white.png", WHITE)
    pill("arc-pill-surface.png", SURFACE)
    pill("arc-pill-surface2.png", SURFACE2)
    round_button("arc-round-white.png", WHITE)
    round_button("arc-round-surface.png", SURFACE)
    card_border()
    wash()
    scrim("arc-scrim.png", 40, 230)
    side_focus()
    progress_scrim()
    logo(os.path.join(MEDIA, "arc-logo.png"), (512, 200))
    icon()
    fanart()
    print("media written to", MEDIA)


if __name__ == "__main__":
    main()
