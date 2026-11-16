"""
core.theme_picture
====================

A theme from a picture (prompt 24 §9, appearance phase A7, DEC-0184): "make
a theme from this photo" or "from my ocean painting". The palette is read
in code (Pillow's median cut), never chosen by the model, so the same
picture always gives the same theme, and the result goes through the same
checks as a theme made by hand (core/themes.build_theme: no accent that
reads as a meaning colour, readable text).

- `from_image(source, name)`: the picture (bytes, or a path to one of the
  person's paintings) as {name, line, base, choices, understood, missed},
  the shape core/theme_design.design gives, so the Studio previews it and
  theme.save keeps it the same way.

How the colours are chosen:

- the field (background and panels) takes the hue of the picture's most
  common dark colour, made dark enough for MIA's glass (themes stay dark:
  the glasses and the 3D room need it);
- the accent is the picture's most common vivid colour that isn't a
  meaning colour (amber or orange, red, green: DEC-0014, DEC-0186), at a
  lightness that reads on the dark field; one that is a meaning colour
  goes into the room's palette instead, and is named in `missed`; a picture
  with no vivid colour has its most colourful one brightened;
- the text is a near-white tinted toward the field, the lines between the
  accent and the text, the room's palette the picture's vivid colours.

Pictures are read through a small thumbnail, as PNG, JPEG or WebP only, with
a byte cap and a pixel cap checked from the file's header, so a huge, odd or
broken file is refused with a sentence rather than read in full.
"""

from __future__ import annotations

import colorsys
import io
from pathlib import Path
from typing import Optional, Union

from core.themes import THEMES, accent_problem, as_data, choices_of, contrast, mix

MAX_BYTES = 12 * 1024 * 1024  # a phone photo fits; anything bigger is refused, not read
MAX_PIXELS = 50_000_000  # refused from the header's size, so a small file can't unpack into a huge one
FORMATS = ("PNG", "JPEG", "WEBP")
BASE = "aquatic"  # the glass the picture's colours go onto (DEC-0183)
TINTED = 0.08  # below this saturation a colour is grey, and its hue is noise


def _rgb_of(colour: str) -> tuple[int, int, int]:
    """Pure logic. "#rrggbb" as (r, g, b)."""
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def _hls_hex(h: float, light: float, sat: float) -> str:
    """Pure logic. "#rrggbb" from hue, lightness and saturation (each 0 to 1)."""
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, light)), max(0.0, min(1.0, sat)))
    return "#" + "".join(f"{round(v * 255):02x}" for v in (r, g, b))


def _hls(rgb: tuple) -> tuple[float, float, float]:
    """Pure logic. (hue, lightness, saturation) of an (r, g, b) in 0 to 255."""
    return colorsys.rgb_to_hls(*(v / 255 for v in rgb[:3]))


def _open(source: Union[bytes, Path]):
    """The picture as a small RGB thumbnail, decoded only as PNG, JPEG or WebP and only when its header says it's
    within MAX_PIXELS; ValueError with a sentence when it can't be read (or this device has no image library: the
    phone's build may not)."""
    try:
        from PIL import Image
    except ImportError:
        raise ValueError("Reading a picture's colours needs the PC. Try it there.") from None

    try:
        data = Path(source).read_bytes() if isinstance(source, (str, Path)) else bytes(source)
    except OSError:
        raise ValueError("That picture isn't there any more.") from None
    if not data:
        raise ValueError("That picture is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"That picture is too big to read (over {MAX_BYTES // (1024 * 1024)} MB). Try a smaller copy.")
    try:
        # Only these three decoders: Pillow's others include ones that run outside programs (EPS) or are rarely
        # exercised, and a picture can come from the page (Fable's review, 2026-11-16).
        image = Image.open(io.BytesIO(data), formats=FORMATS)
    except Exception:  # Pillow raises many kinds for a file that isn't a picture
        raise ValueError("MIA can't read that as a picture. Try a JPEG or PNG.") from None
    width, height = image.size
    if width * height > MAX_PIXELS:  # read from the header, before anything is decoded
        raise ValueError("That picture is too large to read. Try a smaller copy.")
    try:
        image.draft("RGB", (320, 320))  # JPEGs decode small
        image = image.convert("RGB")
        image.thumbnail((160, 160))
    except Exception:  # Pillow raises many kinds for a file that isn't a picture
        raise ValueError("MIA can't read that as a picture. Try a JPEG or PNG.") from None
    return image


def _palette(image, colours: int) -> list[tuple[float, tuple]]:
    """Pure-ish. The picture's main colours by median cut: [(share, (r, g, b))], most common first."""
    from PIL import Image

    quantised = image.quantize(colors=colours, method=Image.Quantize.MEDIANCUT)
    palette = quantised.getpalette()
    counts = quantised.getcolors() or []
    total = sum(n for n, _ in counts) or 1
    return sorted(((n / total, tuple(palette[i * 3:i * 3 + 3])) for n, i in counts), reverse=True)


def _vivid(image) -> tuple[float, list[tuple[float, tuple]]]:
    """Pure-ish. (the share of vivid pixels, their main colours): pixels colourful and neither dark nor washed out."""
    from PIL import Image

    flat = getattr(image, "get_flattened_data", None) or image.getdata  # getdata goes in Pillow 14
    pixels = list(flat())
    keep = [p for p in pixels if (lambda h, l, s: s >= 0.35 and 0.22 <= l <= 0.85)(*_hls(p))]
    if not keep:
        return 0.0, []
    strip = Image.new("RGB", (len(keep), 1))
    strip.putdata(keep)
    return len(keep) / len(pixels), _palette(strip, 6)


def _accent_from(rgb: tuple, background: str) -> str:
    """Pure logic. A picture colour as an accent: its hue, colourful enough to read as one, light enough for the field."""
    h, _l, s = _hls(rgb)
    sat = max(0.55, min(0.9, s))
    for light in (0.62, 0.68, 0.74):
        colour = _hls_hex(h, light, sat)
        if contrast(colour, background) >= 4.5:
            return colour
    return _hls_hex(h, 0.78, sat)


def _hue_name(colour: str) -> str:
    """Pure logic. A colour's plain name by hue ("blue", "violet"...), for her sentence."""
    h, light, s = _hls(_rgb_of(colour))
    if s < 0.15:
        return "grey" if light < 0.85 else "white"
    names = ((15, "red"), (45, "orange"), (65, "gold"), (160, "green"), (190, "teal"), (200, "cyan"),
             (250, "blue"), (285, "violet"), (330, "pink"), (361, "red"))
    degrees = h * 360
    return next(name for top, name in names if degrees < top)


def from_image(source: Union[bytes, Path], name: str = "") -> dict:
    """A theme from a picture: {name, line, base, choices, understood, missed} (see the module). Raises ValueError
    with a sentence when the picture can't be read."""
    image = _open(source)
    main = _palette(image, 12)
    vivid_share, vivid = _vivid(image)
    understood: list[str] = []
    missed: list[str] = []

    # The field's hue from its dark colours that have one (a near-black's hue is noise); else a neutral grey.
    tinted = [(share, rgb) for share, rgb in main if _hls(rgb)[1] < 0.4 and _hls(rgb)[2] >= TINTED]
    if tinted:
        field_h, _l, field_s = _hls(max(tinted, key=lambda d: d[0])[1])
        field_s = min(field_s, 0.45)
        understood.append(f"the field: the picture's {_hue_name(_hls_hex(field_h, 0.5, max(field_s, 0.2)))} "
                          "shadows, made dark for the glass")
    else:
        field_h, field_s = 0.0, 0.0
        understood.append("the field: the picture's grey shadows, made dark for the glass")
    background = _hls_hex(field_h, 0.05, field_s)
    panel = _hls_hex(field_h, 0.10, min(field_s, 0.35))

    candidates = vivid if vivid_share >= 0.01 else []
    if not candidates:  # a muted picture: its most colourful main colour, brightened
        candidates = [m for m in sorted(main, key=lambda m: -_hls(m[1])[2]) if _hls(m[1])[2] >= TINTED][:3]
        if candidates:
            understood.append("the picture is soft, so its most colourful tone is brightened for the accent")
    accent, room, refused = "", [], []
    for _share, rgb in candidates:
        colour = _accent_from(rgb, background)
        if accent_problem(colour):
            refused.append(colour)
        elif not accent:
            accent = colour
        hue = _hls(rgb)[0] * 360
        if all(min(abs(hue - h), 360 - abs(hue - h)) >= 12 for h in (_hls(_rgb_of(r))[0] * 360 for r in room)):
            room.append(colour)  # the room's palette: one of each hue
    base = choices_of(as_data(THEMES[BASE]))
    if accent:
        understood.append(f"the accent: its {_hue_name(accent)} ({accent})")
    elif refused:
        accent = base["accent"]
        missed.append("no colour in it could be the accent without looking like a meaning colour, so it keeps "
                      f"{THEMES[BASE].name}'s")
    else:
        accent = base["accent"]
        missed.append(f"the picture has no colour to take an accent from, so it keeps {THEMES[BASE].name}'s")
    if refused:
        word = _hue_name(refused[0])
        missed.append(f"its {word} would look like a meaning colour as the accent (amber or orange: a reward or "
                      "\"needs you\"; red: an error; green: done), so it colours the room's light instead")

    text = _hls_hex(field_h, 0.93, min(field_s, 0.2))
    if contrast(text, panel) < 4.5:
        text = "#eef2f6"
    picks = dict(base)
    picks.update({"accent": accent, "background": background, "panel": panel, "text": text,
                  "line": mix(accent, text, 0.5), "material": "glass", "palette": room[:4]})
    title = " ".join(str(name or "").split())[:40] or "From Your Picture"
    return {"name": title, "line": "Colours read from a picture.", "base": BASE, "choices": picks,
            "understood": understood, "missed": missed}


def summary(result: dict) -> str:
    """Pure logic. What she made from the picture, in one or two sentences (for the voice tool and the Studio)."""
    out = f"I made {result['name']} from the picture: " + "; ".join(result["understood"][:3]) + "."
    if result["missed"]:
        out += " " + result["missed"][0][0].upper() + result["missed"][0][1:] + "."
    return out


def from_painting(context, words: str) -> Optional[dict]:
    """One of the person's paintings their words point at (core/art_studio.find) as a theme, named after it; None
    when none matches. ValueError when its file can't be read."""
    from core.art_studio import find

    item = find(context, words)
    store = getattr(context, "art", None)
    path = store.path(item["id"]) if item is not None and store is not None else None
    if path is None:
        return None
    title = " ".join(w.capitalize() for w in item["description"].split()[:3])
    return from_image(path, name=title)
