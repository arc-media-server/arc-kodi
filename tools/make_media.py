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

# Sizes the skin shows the logos and icons at (skin/includes.xml, the sign-in windows).
SIDEBAR_LOGO_H = 40
SIDEBAR_ICON = 44
LOGO_STACKED_H = 190
OSD_ICONS = {"sliders-horizontal": 34, "volume-2": 34, "captions": 34, "check": 30, "play": 26, "pause": 26,
             "rotate-ccw": 34, "circle-check": 34, "bookmark": 34, "bookmark-check": 34, "circle-check-filled": 34}


def _rounded(size, radius, fill=None, outline=None, width=0):
    """A rounded rectangle drawn at 4x and scaled down, so its curves are smooth (Pillow draws
    them without anti-aliasing)."""
    w, h = size
    big = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=radius * S, fill=fill,
                                          outline=outline, width=width * S)
    return big.resize((w, h), Image.LANCZOS)


def pill(name, fill):
    # A nine-slice pill for 76-high buttons: 76x76, radius 38, used with border="38".
    _rounded((76, 76), 38, fill).save(os.path.join(MEDIA, name))


# Cards are drawn at the exact size the skin shows them (skin/includes.xml), so Kodi never
# stretches their corners: a mask that rounds the picture, and the focus ring around it.
CARDS = {"poster": (244, 366), "thumb": (464, 261)}
CARD_RADIUS = 14


def cards():
    for kind, (w, h) in CARDS.items():
        _rounded((w, h), CARD_RADIUS, fill=WHITE).save(os.path.join(MEDIA, "arc-mask-%s.png" % kind))
        # The ring sits 6 px outside the card: 4 px of white, a 2 px gap.
        _rounded((w + 12, h + 12), CARD_RADIUS + 6, outline=WHITE, width=4).save(
            os.path.join(MEDIA, "arc-ring-%s.png" % kind))


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

    # Each is rendered large, cropped to its drawing (so the skin can place it by its real edges:
    # the sidebar lines the TV up with the icons), then scaled to exactly the height the skin shows
    # it at, so Kodi draws it 1:1 instead of shrinking a big picture (which looked jagged).
    jobs = [  # (svg, png, shown height in pixels; None keeps the size)
        ("arc-logo-stacked-white.svg", os.path.join(MEDIA, "arc-logo-stacked.png"), LOGO_STACKED_H),
        ("arc-logo-white.svg", os.path.join(MEDIA, "arc-logo.png"), SIDEBAR_LOGO_H),
        ("arc-mark-white.svg", os.path.join(MEDIA, "arc-mark.png"), SIDEBAR_LOGO_H),
        ("arc-icon-square.svg", os.path.join(RES, "icon.png"), None),
    ]
    # The sidebar's icons: Lucide's, as Arc's web and Android apps draw them (tools/brand/icons),
    # rendered by Chromium at the size they're shown (it anti-aliases the strokes itself).
    for name in sorted(os.listdir(os.path.join(BRAND, "icons"))):
        if name.endswith(".svg"):
            jobs.append((os.path.join("icons", name), os.path.join(MEDIA, "arc-icon-%s.png" % name[:-4]), "icon"))
    # The player's icons (tools/brand/osd, Lucide's too), at the sizes the player shows them.
    for name, size in OSD_ICONS.items():
        jobs.append((os.path.join("osd", name + ".svg"), os.path.join(MEDIA, "arc-osd-%s.png" % name), ("icon", size)))
    args = []
    for svg, out, height in jobs:
        if isinstance(height, tuple):
            width = height[1]
        else:
            width = SIDEBAR_ICON if height == "icon" else 512 if height is None else 2000
        args += [os.path.join(BRAND, svg), out, str(width)]
    subprocess.run(["node", os.path.join(ROOT, "tools", "render_svg.js")] + args, check=True)
    for svg, out, height in jobs:
        if height is None or height == "icon" or isinstance(height, tuple):
            continue
        img = Image.open(out)
        img = img.crop(img.getbbox())
        w = round(img.width * height / float(img.height))
        img.resize((w, height), Image.LANCZOS).save(out)
        print("%s: %dx%d" % (os.path.basename(out), w, height))


def player():
    """The player's pieces (skin/script-arc-player.xml): the shading behind the controls, the
    timeline (a capsule 12 high, played part white over 35% white) and its marker."""
    w, h = 16, 300
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1.0)
        a = 0.0 if t < 0.15 else min(0.85, (t - 0.15) / 0.85 * 0.85)
        for x in range(w):
            px[x, y] = (0, 0, 0, int(255 * a))
    img.save(os.path.join(MEDIA, "arc-osd-scrim.png"))
    _rounded((24, 12), 6, fill=(255, 255, 255, 90)).save(os.path.join(MEDIA, "arc-tl-bg.png"))
    _rounded((24, 12), 6, fill=WHITE).save(os.path.join(MEDIA, "arc-tl-fg.png"))
    _rounded((8, 32), 4, fill=WHITE).save(os.path.join(MEDIA, "arc-tl-marker.png"))


def title_page():
    """The title page (skin/script-arc-details.xml): four corner glows Kodi tints with the
    artwork's toned colours, the mask that fades the artwork into them at the left and the foot
    (as the Apple app's), a circle for cast photos, badge capsules and the cards' panels."""
    w, h = 192, 108
    for name, (cx, cy) in {"tl": (0, 0), "tr": (w, 0), "bl": (0, h), "br": (w, h)}.items():
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                d = (((x - cx) / float(w)) ** 2 + ((y - cy) / float(h)) ** 2) ** 0.5
                a = max(0.0, 1.0 - d / 1.1) ** 1.3
                px[x, y] = (255, 255, 255, int(255 * a))
        img.save(os.path.join(MEDIA, "arc-glow-%s.png" % name))
    w, h = 384, 216
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        fy = y / (h - 1.0)
        for x in range(w):
            fx = x / (w - 1.0)
            left = min(1.0, max(0.0, (fx - 0.12) / 0.45))   # gone at the left, whole from 57%
            foot = min(1.0, max(0.0, (0.95 - fy) / 0.45))   # gone at the foot, whole above half
            px[x, y] = (255, 255, 255, int(255 * (left * foot) ** 1.2))
    img.save(os.path.join(MEDIA, "arc-hero-mask.png"))
    # A soft dark area behind text over bright artwork (the hero's Starring column).
    w, h = 160, 120
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            d = (((x - w / 2.0) / (w / 2.0)) ** 2 + ((y - h / 2.0) / (h / 2.0)) ** 2) ** 0.5
            px[x, y] = (255, 255, 255, int(255 * max(0.0, 1.0 - d) ** 0.8))
    img.save(os.path.join(MEDIA, "arc-shade.png"))
    _rounded((160, 160), 80, fill=WHITE).save(os.path.join(MEDIA, "arc-mask-face.png"))
    face = Image.new("RGBA", (160, 240), (0, 0, 0, 0))
    face.paste(_rounded((160, 160), 80, fill=WHITE), (0, 0))
    face.save(os.path.join(MEDIA, "arc-mask-face-portrait.png"))
    _rounded((172, 172), 86, outline=WHITE, width=4).save(os.path.join(MEDIA, "arc-ring-face.png"))
    _rounded((40, 40), 20, fill=WHITE).save(os.path.join(MEDIA, "arc-badge-fill.png"))
    _rounded((40, 40), 20, outline=(255, 255, 255, 170), width=2).save(os.path.join(MEDIA, "arc-badge-line.png"))
    _rounded((64, 64), 24, fill=(255, 255, 255, 30)).save(os.path.join(MEDIA, "arc-panel.png"))
    _rounded((64, 64), 26, outline=WHITE, width=4).save(os.path.join(MEDIA, "arc-panel-ring.png"))
    Image.new("RGBA", (8, 8), WHITE).save(os.path.join(MEDIA, "arc-white.png"))  # dims behind Arc's menu


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
    cards()
    wash()
    hero_scrim()
    tick()
    circle_and_ring()
    bars()
    side_panel()
    player()
    title_page()
    brand_renders()
    fanart()
    print("media written to", MEDIA)


if __name__ == "__main__":
    main()
