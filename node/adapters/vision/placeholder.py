"""Pillow placeholder scene generator — the zero-dependency fallback.

Draws a simple but readable "security camera" frame: dark room, timestamp
overlay, and N silhouettes for N people (red-tinted for an anomaly). Good
enough for a demo when no AI bank is present, and it makes the pipeline work
out-of-the-box.

Kept OUT of the domain/application core (uses PIL). Adapter-side only.
"""

import os
import random

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL = True
except ImportError:  # pragma: no cover
    _PIL = False

W, H = 640, 480


def _font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _silhouette(draw, x, base_y, scale, color):
    """A crude standing figure centered at x."""
    head_r = int(14 * scale)
    body_w = int(26 * scale)
    body_h = int(70 * scale)
    # head
    draw.ellipse([x - head_r, base_y - body_h - head_r * 2,
                  x + head_r, base_y - body_h], fill=color)
    # body
    draw.rounded_rectangle([x - body_w // 2, base_y - body_h,
                            x + body_w // 2, base_y],
                           radius=int(8 * scale), fill=color)


def render_scene(path: str, count: int, anomaly: bool = False,
                 timestamp: str = "", seed: int = None):
    """Render a placeholder frame with `count` figures to `path`. Returns path."""
    if not _PIL:  # pragma: no cover
        # last-ditch: write an empty file so callers still get a valid ref
        open(path, "wb").close()
        return path

    rng = random.Random(seed)
    bg = (26, 30, 36) if not anomaly else (46, 20, 24)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    # floor line + subtle grid for a "camera" feel
    for gy in range(0, H, 60):
        d.line([(0, gy), (W, gy)], fill=(255, 255, 255, 20), width=1)
    d.line([(0, int(H * 0.75)), (W, int(H * 0.75))], fill=(70, 78, 88), width=2)

    color = (63, 185, 80) if not anomaly else (217, 83, 79)
    n = max(0, min(4, count))
    if n > 0:
        spacing = W // (n + 1)
        for i in range(n):
            x = spacing * (i + 1) + rng.randint(-20, 20)
            scale = rng.uniform(0.9, 1.15)
            _silhouette(d, x, int(H * 0.75), scale, color)

    # overlays
    f = _font(20)
    fsmall = _font(15)
    label = "ANOMALY: glass_break" if anomaly else ("%d person%s" %
                                                    (count, "" if count == 1 else "s"))
    d.rectangle([0, 0, W, 30], fill=(0, 0, 0))
    d.text((10, 6), "CAM-01  " + (timestamp or ""), fill=(200, 200, 200), font=fsmall)
    d.text((10, H - 26), label, fill=color, font=f)
    if anomaly:
        d.rectangle([2, 2, W - 3, H - 3], outline=(217, 83, 79), width=3)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, "JPEG", quality=80)
    return path
