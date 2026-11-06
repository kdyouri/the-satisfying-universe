"""Generate TechnoInno / The Satisfying Universe brand assets locally (free)."""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OUT = Path("generated/brand")
OUT.mkdir(parents=True, exist_ok=True)

MIDNIGHT = (10, 16, 38)
MIDNIGHT_SOFT = (18, 28, 62)
PEARL = (240, 244, 252)
CYAN = (110, 220, 235)
LILAC = (186, 160, 240)


def radial(size, inner, outer):
    """RGBA radial gradient image (inner color center -> outer edge)."""
    grad = Image.radial_gradient("L").resize((size, size), Image.LANCZOS)
    return Image.composite(
        Image.new("RGB", (size, size), outer),
        Image.new("RGB", (size, size), inner),
        grad,
    )


def orb_layer(diameter, supersample=4):
    size = diameter * supersample
    # vivid base: pearl-hot core -> cyan body
    orb = radial(size, (250, 252, 255), (96, 205, 232)).convert("RGBA")

    circle = Image.new("L", (size, size), 0)
    dc = ImageDraw.Draw(circle)
    dc.ellipse([0, 0, size - 1, size - 1], fill=255)

    # soft iridescent blobs (lilac lower right, cyan upper left), clipped to the orb
    blob = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    db = ImageDraw.Draw(blob)
    db.ellipse([size * 0.40, size * 0.40, size * 1.25, size * 1.25], fill=LILAC + (115,))
    db.ellipse([size * -0.30, size * -0.30, size * 0.45, size * 0.45], fill=(150, 235, 250, 90))
    blob = blob.filter(ImageFilter.GaussianBlur(size * 0.16))
    blob.putalpha(ImageChops.multiply(blob.getchannel("A"), circle))
    orb = Image.alpha_composite(orb, blob)

    # top-left highlight
    hl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(hl)
    r = size * 0.28
    d.ellipse(
        [size * 0.18, size * 0.12, size * 0.18 + r, size * 0.12 + r],
        fill=(255, 255, 255, 185),
    )
    hl = hl.filter(ImageFilter.GaussianBlur(size * 0.05))
    orb = Image.alpha_composite(orb, hl)

    # crisp specular dot
    d = ImageDraw.Draw(orb)
    dr = size * 0.05
    d.ellipse(
        [size * 0.31, size * 0.235, size * 0.31 + dr, size * 0.235 + dr],
        fill=(255, 255, 255, 240),
    )

    # subtle rim shading only at the very edge (keeps the face vivid)
    ring_only = Image.new("L", (size, size), 0)
    dr3 = ImageDraw.Draw(ring_only)
    dr3.ellipse([size * 0.02, size * 0.02, size * 0.98, size * 0.98], outline=255, width=size // 12)
    ring_only = ring_only.filter(ImageFilter.GaussianBlur(size * 0.035))
    shadow = Image.new("RGBA", (size, size), (10, 30, 70, 0))
    shadow.putalpha(ring_only.point(lambda x: x * 55 // 255))
    orb = Image.alpha_composite(orb, shadow)

    orb.putalpha(circle)
    return orb.resize((diameter, diameter), Image.LANCZOS)


def avatar(path, final=800):
    ss = 4
    size = final * ss
    img = radial(size, MIDNIGHT_SOFT, MIDNIGHT).convert("RGBA")

    # subtle nebula glows
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.ellipse(
        [size * 0.52, size * 0.06, size * 1.02, size * 0.56],
        fill=CYAN + (36,),
    )
    dg.ellipse(
        [size * -0.04, size * 0.52, size * 0.42, size * 0.94],
        fill=LILAC + (30,),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.12))
    img = Image.alpha_composite(img, glow)

    # concentric ripples (thin pearl rings, fading outward)
    rings = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(rings)
    center = size / 2
    for i, (radius, alpha, width) in enumerate(
        [(0.355, 210, 7), (0.415, 140, 6), (0.475, 85, 5), (0.535, 45, 4)]
    ):
        r = radius * size
        dr.ellipse(
            [center - r, center - r, center + r, center + r],
            outline=PEARL + (alpha,),
            width=width * ss // 2,
        )
    rings = rings.filter(ImageFilter.GaussianBlur(size * 0.002))
    img = Image.alpha_composite(img, rings)

    # luminous orb with glow
    orb_radius = size * 0.235
    glow_ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dgl = ImageDraw.Draw(glow_ring)
    gr = orb_radius * 1.18
    dgl.ellipse(
        [center - gr, center - gr, center + gr, center + gr],
        fill=(150, 230, 245, 80),
    )
    glow_ring = glow_ring.filter(ImageFilter.GaussianBlur(size * 0.06))
    img = Image.alpha_composite(img, glow_ring)

    orb = orb_layer(int(orb_radius * 2), supersample=2)
    img.alpha_composite(orb, (int(center - orb_radius), int(center - orb_radius)))

    img = img.resize((final, final), Image.LANCZOS)
    img.save(path)
    print("wrote", path)


def banner(path, width=2560, height=1440):
    w, h = width, height
    img = Image.new("RGB", (w, h), MIDNIGHT)
    grad = Image.radial_gradient("L").resize((w, h), Image.LANCZOS)
    img = Image.composite(
        Image.new("RGB", (w, h), MIDNIGHT),
        Image.new("RGB", (w, h), MIDNIGHT_SOFT),
        grad,
    ).convert("RGBA")

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.ellipse([w * 0.62, h * 0.10, w * 1.06, h * 0.86], fill=CYAN + (26,))
    dg.ellipse([w * -0.06, h * 0.30, w * 0.34, h * 1.02], fill=LILAC + (24,))
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.10))
    img = Image.alpha_composite(img, glow)

    # quiet macro ripples across the banner
    rings = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(rings)
    cx, cy = w * 0.26, h * 0.52
    for i in range(9):
        r = (0.06 + i * 0.055) * h
        alpha = max(18, 150 - i * 16)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=PEARL + (alpha,), width=max(1, h // 480))
    img = Image.alpha_composite(img, rings.filter(ImageFilter.GaussianBlur(h * 0.004)))

    orb_d = int(h * 0.34)
    glow2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dgl = ImageDraw.Draw(glow2)
    dgl.ellipse(
        [cx - orb_d * 0.62, cy - orb_d * 0.62, cx + orb_d * 0.62, cy + orb_d * 0.62],
        fill=(150, 230, 245, 70),
    )
    glow2 = glow2.filter(ImageFilter.GaussianBlur(h * 0.05))
    img = Image.alpha_composite(img, glow2)
    orb = orb_layer(orb_d, supersample=2)
    img.alpha_composite(orb, (int(cx - orb_d / 2), int(cy - orb_d / 2)))

    font_path = "/System/Library/Fonts/Helvetica.ttc"
    text_x = w * 0.46
    max_width = w * 0.80 - text_x
    tagline = "Beautiful things. Perfect moments."
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))

    def fitted_font(text, base_ratio):
        size_px = int(h * base_ratio)
        while size_px > 10:
            font = ImageFont.truetype(font_path, size_px, index=1)
            if probe.textlength(text, font=font) <= max_width:
                return font
            size_px = int(size_px * 0.94)
        return ImageFont.truetype(font_path, 12, index=1)

    name_font = fitted_font("THE SATISFYING", 0.135)
    name2_font = fitted_font("UNIVERSE", 0.135)
    tag_font = fitted_font(tagline, 0.056)

    name = "THE SATISFYING"
    name2 = "UNIVERSE"
    name_y = h * 0.372
    name2_y = name_y + h * 0.132
    tag_y = name2_y + h * 0.128
    # soft shadow for legibility
    d = ImageDraw.Draw(img)
    for text, y, font, fill in (
        (name, name_y, name_font, PEARL),
        (name2, name2_y, name2_font, PEARL),
        (tagline, tag_y, tag_font, CYAN),
    ):
        d.text((text_x + 3, y + 3), text, font=font, fill=(4, 8, 22), anchor="lm")
        d.text((text_x, y), text, font=font, fill=fill, anchor="lm")

    img = img.resize((width, height), Image.LANCZOS)
    img.save(path)
    print("wrote", path)


avatar(OUT / "technoinno-avatar-800.png")
banner(OUT / "technoinno-banner-2560x1440.png")
avatar(OUT / "technoinno-avatar-preview-176.png", final=176)
print("done")
