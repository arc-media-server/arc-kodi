"""Star rating icons for existing menu rows; generated with the same Pillow pipeline."""
import math
import os

from PIL import Image, ImageDraw


def write_rating_stars(media):
    scale = 4
    for rating in range(1, 11):
        count = (rating + 1) // 2
        image = Image.new("RGBA", (28 * count * scale, 32 * scale))
        for slot in range(count):
            star = Image.new("RGBA", (28 * scale, 32 * scale))
            points = []
            for point in range(10):
                angle = -math.pi / 2 + point * math.pi / 5
                radius = (12 if point % 2 == 0 else 5.2) * scale
                points.append((14 * scale + math.cos(angle) * radius,
                               16 * scale + math.sin(angle) * radius))
            ImageDraw.Draw(star).polygon(points, fill=(255, 255, 255, 255))
            if 2 * slot + 2 > rating:
                ImageDraw.Draw(star).rectangle((14 * scale, 0, 28 * scale, 32 * scale), fill=(0, 0, 0, 0))
            image.paste(star, (28 * slot * scale, 0))
        image.resize((28 * count, 32), Image.LANCZOS).save(os.path.join(media, "arc-rating-%d.png" % rating))
