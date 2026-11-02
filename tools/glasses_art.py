"""MIA's orb as pictures for the real glasses (DEC-0061).

Meta's display views can only show images from a public https address, so
the orb is drawn here, once per state, in the same look as web/glasses.css:
a cyan core, two broken rings, a few sparks. Black is see-through on the
glasses. Fixed artwork only, never anything of a person's.

    python -m tools.glasses_art <folder>
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = 240
SCALE = 3  # drawn large, then shrunk for smooth edges
ACCENT = np.array([53, 212, 255], dtype=float)  # --rgb-accent, web/tokens.css
SOFT = np.array([223, 246, 255], dtype=float)

# state: core size, brightness, ring radii (of the half-width), ring turn, ring width
STATES = {
    "idle": (0.30, 0.85, (0.60, 0.80), 0.0, 0.012),
    "listening": (0.40, 1.00, (0.56, 0.74), 0.5, 0.018),
    "thinking": (0.26, 0.80, (0.50, 0.84), 1.6, 0.012),
    "speaking": (0.46, 1.00, (0.66, 0.86), 2.4, 0.020),
}
SPARKS = ((-0.62, -0.42), (0.68, 0.24), (-0.46, 0.60))


def ring(radius, angle, turn, width, r, reach):
    """A ring lit along part of its way round, fading at the ends."""
    lit = np.clip(np.cos(angle - turn) * 1.4 + 0.15, 0, 1) ** reach
    return np.exp(-((r - radius) / width) ** 2) * lit


def orb(core, brightness, radii, turn, width) -> Image.Image:
    n = SIZE * SCALE
    y, x = np.mgrid[-1:1:complex(n), -1:1:complex(n)]
    r = np.hypot(x, y)
    angle = np.arctan2(y, x)

    centre = np.exp(-(r / (core * 0.55)) ** 2)
    glow = np.exp(-(r / core) ** 1.4) * 0.75
    rings = ring(radii[0], angle, turn, width, r, 1.0) + ring(radii[1], angle, turn + np.pi, width, r, 1.6) * 0.8
    sparks = sum(np.exp(-(np.hypot(x - sx, y - sy) / 0.018) ** 2) for sx, sy in SPARKS)

    edge = np.clip((1 - r) / 0.08, 0, 1)  # nothing reaches the square's edge
    light = np.clip((centre + glow + rings * 0.9 + sparks * 0.8) * brightness * edge, 0, 1)
    white = np.clip(centre * brightness + rings * 0.35, 0, 1)
    pixels = ACCENT[None, None] * light[..., None] + (SOFT - ACCENT)[None, None] * (light * white)[..., None]
    return Image.fromarray(np.clip(pixels, 0, 255).astype("uint8"), "RGB").resize((SIZE, SIZE), Image.LANCZOS)


def main(folder: str) -> None:
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    for name, shape in STATES.items():
        orb(*shape).save(out / f"orb-{name}.png", optimize=True)
        print(f"orb-{name}.png", (out / f"orb-{name}.png").stat().st_size, "bytes")


if __name__ == "__main__":
    main(sys.argv[1])
