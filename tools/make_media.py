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


S = 4  # supersampling for smooth edges


def _rounded(size, radius, fill):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=fill)
    return img


def pill(name, fill):
    # A nine-slice rounded pill: 80x80, radius 40, so border=8..40 keeps the corners crisp.
    _rounded((80, 80), 40, fill).save(os.path.join(MEDIA, name))


def hero_scrim():
    """Darkens artwork behind text: strongest at the left and the foot, as the Apple app's hero."""
    w, h = 384, 216
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        fy = y / (h - 1.0)
        for x in range(w):
            fx = x / (w - 1.0)
            left = max(0.0, 1.0 - fx / 0.7) ** 1.4      # fades out by 70% across
            foot = max(0.0, (fy - 0.35) / 0.65) ** 1.2  # builds from a third down
            a = 0.30 + 0.55 * left + 0.65 * foot
            px[x, y] = (18, 19, 22, int(255 * min(0.97, a)))
    img.save(os.path.join(MEDIA, "arc-scrim.png"))


def card_border():
    """The white focus ring around a card: a nine-slice outline, 4 px thick, round corners."""
    img = Image.new("RGBA", (32 * S, 32 * S), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, 32 * S - 1, 32 * S - 1], radius=10 * S, outline=WHITE, width=4 * S)
    img.resize((32, 32), Image.LANCZOS).save(os.path.join(MEDIA, "arc-card-border.png"))


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


def _canvas(size):
    return Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))


def _save_small(img, name, size):
    img.resize((size, size), Image.LANCZOS).save(os.path.join(MEDIA, name))


def icons():
    """The sidebar's icons, white on clear (tinted in the skin), 96x96."""
    n = 96
    w = 7 * S  # stroke

    def draw(name, fn):
        img = _canvas(n)
        fn(ImageDraw.Draw(img), n * S)
        _save_small(img, "arc-icon-%s.png" % name, n)

    def search(d, z):
        d.ellipse([z * .16, z * .16, z * .62, z * .62], outline=WHITE, width=w)
        d.line([z * .56, z * .56, z * .84, z * .84], fill=WHITE, width=w + 2 * S)

    def home(d, z):
        d.line([z * .14, z * .48, z * .5, z * .16, z * .86, z * .48], fill=WHITE, width=w, joint="curve")
        d.rectangle([z * .24, z * .44, z * .76, z * .84], outline=WHITE, width=w)

    def film(d, z):
        d.rounded_rectangle([z * .18, z * .14, z * .82, z * .86], radius=z * .06, outline=WHITE, width=w)
        for y in (.26, .42, .58, .74):
            d.rectangle([z * .25, z * y - S * 4, z * .31, z * y + S * 4], fill=WHITE)
            d.rectangle([z * .69, z * y - S * 4, z * .75, z * y + S * 4], fill=WHITE)

    def tv(d, z):
        d.rounded_rectangle([z * .12, z * .2, z * .88, z * .72], radius=z * .06, outline=WHITE, width=w)
        d.line([z * .34, z * .84, z * .66, z * .84], fill=WHITE, width=w)

    def video(d, z):
        d.rounded_rectangle([z * .1, z * .28, z * .64, z * .72], radius=z * .06, outline=WHITE, width=w)
        d.polygon([(z * .68, z * .5), (z * .9, z * .32), (z * .9, z * .68)], fill=WHITE)

    def bookmark(d, z):
        d.line([z * .28, z * .86, z * .28, z * .14, z * .72, z * .14, z * .72, z * .86, z * .5, z * .66, z * .28, z * .86],
               fill=WHITE, width=w, joint="curve")

    def lst(d, z):
        for y in (.28, .5, .72):
            d.ellipse([z * .14, z * y - S * 6, z * .14 + S * 12, z * y + S * 6], fill=WHITE)
            d.line([z * .32, z * y, z * .86, z * y], fill=WHITE, width=w)

    def settings(d, z):
        import math
        c = z / 2
        for k in range(8):
            a = k * math.pi / 4
            d.line([c + math.cos(a) * z * .2, c + math.sin(a) * z * .2, c + math.cos(a) * z * .4, c + math.sin(a) * z * .4],
                   fill=WHITE, width=w + 4 * S)
        d.ellipse([c - z * .27, c - z * .27, c + z * .27, c + z * .27], fill=WHITE)
        d.ellipse([c - z * .11, c - z * .11, c + z * .11, c + z * .11], fill=(0, 0, 0, 0))

    for name, fn in (("search", search), ("home", home), ("film", film), ("tv", tv), ("video", video),
                     ("bookmark", bookmark), ("list", lst), ("settings", settings)):
        draw(name, fn)


def tick():
    n = 48
    img = _canvas(n)
    d = ImageDraw.Draw(img)
    z = n * S
    d.ellipse([0, 0, z - 1, z - 1], fill=WHITE)
    d.line([z * .27, z * .52, z * .44, z * .68, z * .74, z * .34], fill=(0, 0, 0, 255), width=5 * S, joint="curve")
    _save_small(img, "arc-tick.png", n)


def circle_and_ring():
    n = 256
    img = _canvas(n)
    ImageDraw.Draw(img).ellipse([0, 0, n * S - 1, n * S - 1], fill=WHITE)
    _save_small(img, "arc-circle.png", n)
    img = _canvas(n)
    ImageDraw.Draw(img).ellipse([0, 0, n * S - 1, n * S - 1], outline=WHITE, width=8 * S)
    _save_small(img, "arc-ring.png", n)


def bars():
    _rounded((16, 8), 4, (255, 255, 255, 70)).save(os.path.join(MEDIA, "arc-bar-bg.png"))
    _rounded((16, 8), 4, WHITE).save(os.path.join(MEDIA, "arc-bar-fg.png"))


def side_panel():
    # The open sidebar's glass: dark, fading out to the right.
    w, h = 460, 16
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for x in range(w):
        a = 235 if x < 400 else int(235 * (1 - (x - 400) / 60.0))
        for y in range(h):
            px[x, y] = (24, 25, 29, a)
    img.save(os.path.join(MEDIA, "arc-side-panel.png"))


BRAND = os.path.join(ROOT, "tools", "brand")


def brand_renders():
    """The owner's logo files (arc-media-server docs/brand, copied into tools/brand/) as PNGs,
    rendered by Chromium (tools/render_svg.js) so the lettering is exact. Needs Node with
    Playwright's Chromium (dev only)."""
    import subprocess

    jobs = [  # (svg, png, width in pixels)
        ("arc-logo-stacked-white.svg", os.path.join(MEDIA, "arc-logo-stacked.png"), 600),
        ("arc-logo-white.svg", os.path.join(MEDIA, "arc-logo.png"), 900),
        ("arc-mark-white.svg", os.path.join(MEDIA, "arc-mark.png"), 192),
        ("arc-icon-square.svg", os.path.join(RES, "icon.png"), 512),
    ]
    args = []
    for svg, out, width in jobs:
        args += [os.path.join(BRAND, svg), out, str(width)]
    subprocess.run(["node", os.path.join(ROOT, "tools", "render_svg.js")] + args, check=True)


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
    for name in os.listdir(MEDIA):
        if name.endswith(".png"):
            os.remove(os.path.join(MEDIA, name))
    pill("arc-pill-white.png", WHITE)
    pill("arc-pill-surface.png", SURFACE)
    card_border()
    _rounded((24, 24), 8, SURFACE).save(os.path.join(MEDIA, "arc-card-bg.png"))
    wash()
    hero_scrim()
    icons()
    tick()
    circle_and_ring()
    bars()
    side_panel()
    brand_renders()
    fanart()
    print("media written to", MEDIA)


if __name__ == "__main__":
    main()
