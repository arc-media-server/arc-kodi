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


def pill(name, fill, size=76):
    # A nine-slice pill: size x size with radius size/2, used with border="size/2" on a control
    # exactly `size` high. A pill drawn for another height loses its round ends (the corner
    # slices hold only part of the curve), so each height has its own: 76 for buttons, 64 for
    # menu rows.
    _rounded((size, size), size // 2, fill).save(os.path.join(MEDIA, name))


# Cards are drawn at the exact size the skin shows them (skin/includes.xml), so Kodi never
# stretches their corners: a mask that rounds the picture, and the focus ring around it.
CARDS = {"poster": (244, 366), "thumb": (464, 261), "backdrop": (400, 300)}
CARD_RADIUS = 14


def cards():
    for kind, (w, h) in CARDS.items():
        _rounded((w, h), CARD_RADIUS, fill=WHITE).save(os.path.join(MEDIA, "arc-mask-%s.png" % kind))
        # The ring sits 6 px outside the card: 4 px of white, a 2 px gap.
        _rounded((w + 12, h + 12), CARD_RADIUS + 6, outline=WHITE, width=4).save(
            os.path.join(MEDIA, "arc-ring-%s.png" % kind))


def backdrop_wide_mask():
    """A backdrop card's picture is a 16:9 backdrop shown at its own shape and centred on the 4:3
    card, through this 16:9 mask: clear at the sides, the card's rounded shape in the middle.
    (Kodi lines a mask up with the whole picture before cropping it to the control, so a mask the
    card's own shape would lose its corners with the cropped sides.)"""
    w, h = CARDS["backdrop"]
    wide = int(round(h * 16 / 9.0))
    img = Image.new("RGBA", (wide, h), (0, 0, 0, 0))
    img.paste(_rounded((w, h), CARD_RADIUS, fill=WHITE), ((wide - w) // 2, 0))
    img.save(os.path.join(MEDIA, "arc-mask-backdrop-wide.png"))


def backdrop_fade():
    """The dark fade at the foot of a backdrop card, behind its logo (the web's ArcArtwork: black
    at 70% at the foot to clear halfway up), inside the card's rounded corners."""
    w, h = CARDS["backdrop"]
    mask = _rounded((w, h), CARD_RADIUS, fill=WHITE)
    img = Image.new("RGBA", (w, h))
    px, mp = img.load(), mask.load()
    for y in range(h):
        a = max(0.0, (y - h / 2.0) / (h / 2.0)) * 0.7
        for x in range(w):
            px[x, y] = (0, 0, 0, int(round(255 * a * mp[x, y][3] / 255.0)))
    img.save(os.path.join(MEDIA, "arc-fade-backdrop.png"))


def count_tab():
    """The tab with a show's unwatched episodes at a poster's top right (the Apple app's): black
    at 80%, its bottom left rounded (12) and its top right following the card's corner."""
    w, h = 64, 44
    big = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=12 * S, fill=(0, 0, 0, 204),
                                          corners=(False, False, False, True))
    clip = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(clip).rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=CARD_RADIUS * S, fill=255,
                                           corners=(False, True, False, False))
    alpha = Image.eval(big.getchannel("A"), lambda a: a)
    big.putalpha(Image.composite(alpha, Image.new("L", alpha.size, 0), clip))
    big.resize((w, h), Image.LANCZOS).save(os.path.join(MEDIA, "arc-count-tab.png"))


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
    # A tick box that isn't ticked (Watch Together's people): a ring as heavy as the ticked
    # one's (arc-osd-circle-check-filled.png), at its size.
    n = 34
    img = _canvas(n)
    ImageDraw.Draw(img).ellipse([S, S, n * S - 1 - S, n * S - 1 - S], outline=WHITE, width=3 * S)
    _save_small(img, "arc-tick-ring.png", n)


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
    # The shading at the top while the controls show: solid for the first 120 of 360 (where
    # skins draw their own "Paused" bar, which Arc's player covers), then fading.
    top = Image.new("RGBA", (w, 360))
    px = top.load()
    for y in range(360):
        a = 1.0 if y < 120 else max(0.0, 1.0 - (y - 120) / 240.0) ** 1.5
        for x in range(w):
            px[x, y] = (0, 0, 0, int(255 * a))
    top.save(os.path.join(MEDIA, "arc-osd-top.png"))
    _rounded((24, 12), 6, fill=(255, 255, 255, 90)).save(os.path.join(MEDIA, "arc-tl-bg.png"))
    _rounded((24, 12), 6, fill=WHITE).save(os.path.join(MEDIA, "arc-tl-fg.png"))
    _rounded((8, 32), 4, fill=WHITE).save(os.path.join(MEDIA, "arc-tl-marker.png"))


def title_page():
    """The title page (skin/script-arc-details.xml): four corner glows Kodi tints with the
    artwork's toned colours, the mask that fades the artwork into them at the left and the foot
    (as the Apple app's), a circle for cast photos, badge capsules and the cards' panels."""
    # The page's wash, as the Apple app's MeshGradient: the four colours blended corner to corner
    # (bilinear) over the whole screen. Kodi can only lay tinted images over each other, so the
    # layers' opacities are worked out to give exactly the bilinear blend: the top-left colour
    # everywhere, then top right at x, bottom left at y(1-x)/(1-xy), bottom right at xy.
    w, h = 192, 108
    layers = {
        "tl": lambda x, y: 1.0,
        "tr": lambda x, y: x,
        "bl": lambda x, y: 0.0 if x * y >= 1 else y * (1 - x) / (1 - x * y),
        "br": lambda x, y: x * y,
    }
    for name, alpha in layers.items():
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for yy in range(h):
            for xx in range(w):
                px[xx, yy] = (255, 255, 255, int(round(255 * alpha(xx / (w - 1.0), yy / (h - 1.0)))))
        img.save(os.path.join(MEDIA, "arc-mesh-%s.png" % name))
    # The artwork over the wash, as the Apple app's two masks: bright to 60% down, then softening
    # to 45% at the foot; half strength at the left edge, whole from 55% across.
    w, h = 384, 216
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        fy = y / (h - 1.0)
        for x in range(w):
            fx = x / (w - 1.0)
            down = 1.0 if fy <= 0.6 else 1.0 - 0.55 * (fy - 0.6) / 0.4
            across = 0.5 + 0.5 * min(1.0, fx / 0.55)
            px[x, y] = (255, 255, 255, int(round(255 * down * across)))
    img.save(os.path.join(MEDIA, "arc-hero-mask.png"))
    # Over the artwork, so words stay readable on bright pictures (a yellow cartoon): darker at the
    # left, behind the hero's words, and towards the foot, behind the season tabs and rows.
    w, h = 384, 216
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        fy = y / (h - 1.0)
        for x in range(w):
            fx = x / (w - 1.0)
            left = 0.55 * max(0.0, 1.0 - fx / 0.65) ** 1.2
            foot = 0.65 * max(0.0, (fy - 0.35) / 0.65) ** 1.2
            px[x, y] = (0, 0, 0, int(round(255 * min(0.85, left + foot))))
    img.save(os.path.join(MEDIA, "arc-title-scrim.png"))
    # A soft dark area behind text over bright artwork (the hero's Starring column).
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
    pill("arc-pill-white-64.png", WHITE, 64)
    pill("arc-pill-surface-64.png", SURFACE, 64)  # the smaller buttons (title page, library pills)
    pill("arc-pill-white-56.png", WHITE, 56)   # Settings' rows
    pill("arc-key.png", WHITE, 96)               # the PIN pad's round keys (tinted when not focused)
    cards()
    backdrop_fade()
    backdrop_wide_mask()
    count_tab()
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
