"""Star rating: the profile's 1–10 half stars, or zero to clear."""
CHOICES = tuple(range(10, 0, -1))
TEXTURES = ("", "arc-rating-1.png", "arc-rating-2.png", "arc-rating-3.png", "arc-rating-4.png",
            "arc-rating-5.png", "arc-rating-6.png", "arc-rating-7.png", "arc-rating-8.png",
            "arc-rating-9.png", "arc-rating-10.png")


def stars(rating):
    r = max(0, min(10, int(rating or 0)))
    return "★" * (r // 2) + ("½" if r % 2 else "")


def out_of_five(rating):
    return "%g" % (max(0, min(10, int(rating or 0))) / 2)


def row_properties(rating, detail=False):
    """Local textures keep stars legible when Kodi's active skin font lacks the glyph."""
    r = max(0, min(10, int(rating or 0)))
    return {"arc.ratingtexture": TEXTURES[r],
            "arc.ratingposition": ("detail" if detail else "label") if r else ""}
