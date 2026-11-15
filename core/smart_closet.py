"""
core.smart_closet
===================

Smart Closet (DEC-0162; Zac, 2026-11-15: "an inventory of my clothes ...
suggest outfits, let me rate them, maybe let me see what they would look
like together"). The design is `docs/specs/SMART_CLOSET.md`.

- **A piece** is one item of clothing: what it is (its category), colour,
  how warm it is, the occasions it's for, whether it's waterproof, its
  condition, whether it's clean or in the wash, a photo, and when it was
  last worn.
- **An outfit** is pieces worn together, with a name, the person's
  ratings (1 to 5 stars, each with an optional note) and when it was last
  worn.
- **A suggestion** (`suggest`) is worked out here in code, never by the
  model. It weighs:
  - the weather (warmth, rain);
  - the day's occasion (a work day from the Loop, the gym or a date from
    the calendar);
  - what hasn't been worn lately;
  - the ratings;
  - simple colour sense: neutrals go with anything, and two different
    bold colours count against an outfit.

  Each pick says why it was chosen. The model only phrases it.
- **Insights** (`insights`): pieces that have gone a long time unworn
  (worth letting go of?), the most-worn pieces, and gaps (no rain layer,
  nothing for an occasion that comes up).

`ClosetBook` is the person's store (smart_closet.json in their folder,
written through atomic_write_text so "undo that" restores it). Photos
live in closet_photos/ beside it.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = DATA_DIR
_FILE = "smart_closet.json"
PHOTO_DIR = "closet_photos"
PHOTO_TYPES = (".jpg", ".jpeg", ".png", ".webp")

CATEGORIES = ("top", "bottom", "dress", "layer", "outerwear", "shoes", "accessory")
WARMTH = ("light", "medium", "warm")
OCCASIONS = ("everyday", "work", "gym", "date", "dressy", "outdoors", "lounge")
CONDITIONS = ("good", "worn", "needs repair")
NEUTRALS = frozenset({"black", "white", "gray", "grey", "navy", "beige", "cream", "brown", "tan", "khaki", "denim",
                      "charcoal", "olive", "ivory", "camel"})

# The occasion a day needs, from words in its calendar events (the first match wins).
_OCCASION_WORDS = (("gym", ("gym", "workout", "run ", "lift", "training", "yoga", "pickleball", "hike")),
                   ("dressy", ("wedding", "funeral", "gala", "interview", "church", "formal")),
                   ("date", ("date", "anniversary", "dinner with")),
                   ("outdoors", ("fishing", "camping", "hiking", "yard", "garden", "greenhouse")))

_UNWORN_DAYS = 180  # a piece not worn this long is offered as one to let go of


def _now() -> str:
    """The time now, as stored."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Piece:
    """One item of clothing: its name, category (CATEGORIES), colour, warmth (WARMTH), the occasions it suits
    (OCCASIONS), whether it's waterproof, its condition, clean or in the wash, a photo file name, notes, and when it was
    last worn and how many times."""
    piece_id: str
    name: str
    category: str = "top"
    color: str = ""
    warmth: str = "medium"
    occasions: list = field(default_factory=lambda: ["everyday"])
    waterproof: bool = False
    condition: str = "good"
    in_wash: bool = False
    photo: str = ""
    notes: str = ""
    last_worn: str = ""
    times_worn: int = 0
    created_at: str = ""


@dataclass
class Outfit:
    """Pieces worn together: a name, the piece ids, ratings ({at, stars, note}), and when it was last worn."""
    outfit_id: str
    name: str
    piece_ids: list = field(default_factory=list)
    ratings: list = field(default_factory=list)
    last_worn: str = ""
    times_worn: int = 0
    created_at: str = ""

    @property
    def stars(self) -> Optional[float]:
        """The average rating, or None before the first."""
        got = [r.get("stars") for r in self.ratings if isinstance(r.get("stars"), (int, float))]
        return round(sum(got) / len(got), 1) if got else None


def _words(raw) -> list[str]:
    """A list from a list or a comma-separated string, trimmed and lower-cased, blanks dropped."""
    items = raw if isinstance(raw, (list, tuple)) else str(raw or "").split(",")
    return [str(x).strip().lower() for x in items if str(x).strip()]


def _yes(raw) -> bool:
    """A yes/no value from a form or a sentence."""
    return raw is True or str(raw).strip().lower() in ("yes", "true", "1", "y", "on")


class ClosetBook:
    """The person's closet (smart_closet.json in their folder, written atomically so undo can restore it)."""

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the person's file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads pieces and outfits, keeping only known fields; an unreadable file is logged, reported and starts
        empty."""
        self.pieces: list[Piece] = []
        self.outfits: list[Outfit] = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(open_text(self._file))
            pick = lambda cls, d: cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # noqa: E731
            self.pieces = [pick(Piece, d) for d in raw.get("pieces", [])]
            self.outfits = [pick(Outfit, d) for d in raw.get("outfits", [])]
        except (ValueError, OSError, TypeError, AttributeError):
            log.exception("smart_closet.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def _save(self) -> None:
        """Writes pieces and outfits atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"pieces": [asdict(p) for p in self.pieces],
                                                  "outfits": [asdict(o) for o in self.outfits]}, indent=2))

    # ---------------------------------------------------------------- pieces

    def get_piece(self, piece_id: str) -> Optional[Piece]:
        """The piece with this id, or None."""
        return next((p for p in self.pieces if p.piece_id == piece_id), None)

    def find_piece(self, words: str) -> Optional[Piece]:
        """The piece a few words name ("the navy hoodie"): an exact name first, else the one whose name holds every
        word; None when none or several do."""
        wanted = " ".join(str(words or "").lower().replace("the ", " ").split())
        if not wanted:
            return None
        exact = [p for p in self.pieces if p.name.lower() == wanted]
        if len(exact) == 1:
            return exact[0]
        hits = [p for p in self.pieces if all(w in f"{p.color} {p.name}".lower() for w in wanted.split())]
        return hits[0] if len(hits) == 1 else None

    def add_piece(self, name: str, **fields) -> Piece:
        """Adds a piece (a name is required), its fields checked by _apply."""
        if not str(name or "").strip():
            raise ValueError("A piece needs a name (\"navy hoodie\", \"black boots\"...).")
        p = Piece(piece_id=uuid.uuid4().hex[:10], name=str(name).strip(), created_at=_now())
        self._apply(p, fields)
        self.pieces.append(p)
        self._save()
        return p

    def update_piece(self, piece_id: str, **fields) -> Piece:
        """Changes a piece (ValueError when it's gone or a value doesn't fit)."""
        p = self.get_piece(piece_id)
        if p is None:
            raise ValueError("That piece isn't in the closet anymore.")
        if "name" in fields:
            if not str(fields["name"] or "").strip():
                raise ValueError("A piece needs a name.")
            p.name = str(fields.pop("name")).strip()
        self._apply(p, fields)
        self._save()
        return p

    def delete_piece(self, piece_id: str) -> None:
        """Removes a piece and takes it out of every outfit (an outfit left with fewer than two pieces goes too); the
        photo file stays, so undo brings it back whole."""
        if self.get_piece(piece_id) is None:
            raise ValueError("That piece isn't in the closet anymore.")
        self.pieces = [p for p in self.pieces if p.piece_id != piece_id]
        for o in self.outfits:
            o.piece_ids = [x for x in o.piece_ids if x != piece_id]
        self.outfits = [o for o in self.outfits if len(o.piece_ids) >= 2]
        self._save()

    @staticmethod
    def _apply(p: Piece, fields: dict) -> None:
        """Checks and sets a piece's fields; ValueError with a plain sentence when one doesn't fit."""
        for key, value in fields.items():
            if value is None:
                continue
            if key == "category":
                v = str(value).strip().lower()
                if v not in CATEGORIES:
                    raise ValueError(f"A category is one of: {', '.join(CATEGORIES)}.")
                p.category = v
            elif key == "warmth":
                v = str(value).strip().lower()
                if v not in WARMTH:
                    raise ValueError("Warmth is light, medium or warm.")
                p.warmth = v
            elif key == "condition":
                v = str(value).strip().lower()
                if v not in CONDITIONS:
                    raise ValueError(f"Condition is one of: {', '.join(CONDITIONS)}.")
                p.condition = v
            elif key == "occasions":
                got = _words(value) or ["everyday"]
                wrong = [w for w in got if w not in OCCASIONS]
                if wrong:
                    raise ValueError(f"Occasions are: {', '.join(OCCASIONS)} (not {', '.join(wrong)}).")
                p.occasions = got
            elif key in ("waterproof", "in_wash"):
                setattr(p, key, _yes(value))
            elif key in ("color", "notes", "photo"):
                setattr(p, key, str(value).strip())
            elif key in ("last_worn",):
                p.last_worn = str(value)
            elif key == "times_worn":
                p.times_worn = max(0, int(value))

    def photo_path(self, piece_id: str) -> Optional[Path]:
        """The piece's photo in closet_photos/, or None (only the stored name's last part is used, so it can't point
        outside the folder)."""
        p = self.get_piece(piece_id)
        if p is None or not p.photo:
            return None
        path = self.data_dir / PHOTO_DIR / Path(p.photo).name
        return path if path.is_file() else None

    def set_photo(self, piece_id: str, source: Path) -> str:
        """Copies a picture in as the piece's photo (the earlier file is kept, so undo shows it again); ValueError for
        an unknown piece or a file that isn't a JPG, PNG or WebP."""
        p = self.get_piece(piece_id)
        if p is None:
            raise ValueError("That piece isn't in the closet anymore.")
        ext = Path(source).suffix.lower()
        if ext not in PHOTO_TYPES:
            raise ValueError("A photo has to be a JPG, PNG or WebP picture.")
        folder = self.data_dir / PHOTO_DIR
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{p.piece_id}-{datetime.now():%Y%m%d%H%M%S}{ext}"
        shutil.copyfile(source, folder / name)
        self.update_piece(piece_id, photo=name)
        return name

    # ---------------------------------------------------------------- outfits

    def get_outfit(self, outfit_id: str) -> Optional[Outfit]:
        """The outfit with this id, or None."""
        return next((o for o in self.outfits if o.outfit_id == outfit_id), None)

    def add_outfit(self, name: str, piece_ids) -> Outfit:
        """Saves pieces worn together as an outfit; ValueError without two known pieces."""
        ids = [i for i in (piece_ids if isinstance(piece_ids, (list, tuple)) else _words(piece_ids))]
        known = [i for i in dict.fromkeys(ids) if self.get_piece(i) is not None]
        if len(known) < 2:
            raise ValueError("An outfit needs at least two pieces from the closet.")
        o = Outfit(outfit_id=uuid.uuid4().hex[:10], name=str(name or "").strip() or self.outfit_name(known),
                   piece_ids=known, created_at=_now())
        self.outfits.append(o)
        self._save()
        return o

    def delete_outfit(self, outfit_id: str) -> None:
        """Removes a saved outfit (its pieces stay)."""
        if self.get_outfit(outfit_id) is None:
            raise ValueError("That outfit isn't saved anymore.")
        self.outfits = [o for o in self.outfits if o.outfit_id != outfit_id]
        self._save()

    def rate_outfit(self, outfit_id: str, stars: int, note: str = "") -> Outfit:
        """Adds a rating (1 to 5 stars, and a note) to an outfit."""
        o = self.get_outfit(outfit_id)
        if o is None:
            raise ValueError("That outfit isn't saved anymore.")
        try:
            n = int(stars)
        except (TypeError, ValueError):
            raise ValueError("A rating is 1 to 5 stars.") from None
        if not 1 <= n <= 5:
            raise ValueError("A rating is 1 to 5 stars.")
        o.ratings.append({"at": _now(), "stars": n, "note": str(note or "").strip()})
        self._save()
        return o

    def wear(self, piece_ids, day: str, outfit_id: str = "") -> list[Piece]:
        """Marks pieces (and the outfit, if named) worn on a day; ValueError when none are known."""
        worn = [p for p in (self.get_piece(i) for i in piece_ids) if p is not None]
        if not worn:
            raise ValueError("Which pieces did you wear?")
        for p in worn:
            p.last_worn = max(p.last_worn or "", day)
            p.times_worn += 1
        o = self.get_outfit(outfit_id) if outfit_id else None
        if o is not None:
            o.last_worn = max(o.last_worn or "", day)
            o.times_worn += 1
        self._save()
        return worn

    def laundry(self, piece_ids=None, in_wash: bool = False) -> int:
        """Marks pieces in the wash or clean (all of them, with no ids: "laundry's done"); how many changed."""
        targets = self.pieces if not piece_ids else [p for p in (self.get_piece(i) for i in piece_ids) if p]
        changed = 0
        for p in targets:
            if p.in_wash != in_wash:
                p.in_wash = in_wash
                changed += 1
        if changed:
            self._save()
        return changed

    def outfit_name(self, piece_ids) -> str:
        """A name from its pieces ("navy hoodie + jeans")."""
        names = [p.name for p in (self.get_piece(i) for i in piece_ids) if p]
        return " + ".join(names[:3]) + ("…" if len(names) > 3 else "")


# ---------------------------------------------------------------- suggestions (pure logic)


def temperature_f(weather: Optional[dict]) -> Optional[float]:
    """The day's feel in °F from a weather card ({temp, high, unit}); the high counts most, since a day's clothes are
    for the day. None without weather."""
    if not weather or weather.get("temp") is None:
        return None
    t = weather.get("high") if weather.get("high") is not None else weather.get("temp")
    t = float(t)
    return t * 9 / 5 + 32 if str(weather.get("unit", "")).upper().endswith("C") else t


def is_wet(weather: Optional[dict]) -> bool:
    """Whether the weather words say rain, showers, drizzle, snow or storms."""
    words = str((weather or {}).get("words", "")).lower()
    return any(w in words for w in ("rain", "shower", "drizzle", "snow", "storm", "sleet", "thunder"))


def warmth_wanted(temp_f: Optional[float]) -> tuple[str, ...]:
    """The warmths that suit a day: hot days light only, mild days light or medium, cold days medium or warm; any
    without weather."""
    if temp_f is None:
        return WARMTH
    if temp_f >= 78:
        return ("light",)
    if temp_f >= 58:
        return ("light", "medium")
    if temp_f >= 40:
        return ("medium", "warm")
    return ("warm", "medium")


def needs_outerwear(temp_f: Optional[float], wet: bool) -> bool:
    """A jacket or coat on a cool day (under 60 °F) or a wet one."""
    return wet or (temp_f is not None and temp_f < 60)


def occasion_for(event_titles: list[str], work_day: bool) -> str:
    """The day's occasion: from words in its events (gym, dressy, date, outdoors), else work on a work day, else
    everyday."""
    text = " " + " ".join(event_titles).lower() + " "
    for occasion, words in _OCCASION_WORDS:
        if any(w in text for w in words):
            return occasion
    return "work" if work_day else "everyday"


def _days_since(day: str, today: date) -> Optional[int]:
    """Days since an ISO date, or None when it's blank or unreadable."""
    try:
        return (today - date.fromisoformat(day[:10])).days
    except (TypeError, ValueError):
        return None


def _bold(color: str) -> Optional[str]:
    """A colour that isn't neutral, or None."""
    c = str(color or "").strip().lower()
    return None if not c or any(n in c for n in NEUTRALS) else c


def _fits_occasion(p: Piece, occasion: str) -> bool:
    """Whether a piece suits the occasion (everyday pieces suit work and outdoors too; shoes and accessories go almost
    anywhere except the gym and dressy days, where they must say so)."""
    if occasion in p.occasions:
        return True
    if occasion in ("work", "outdoors", "date") and "everyday" in p.occasions:
        return True
    return False


def _score_pieces(pieces: list[Piece], occasion: str, warm: tuple, today: date) -> tuple[float, list[str]]:
    """How well a set of pieces suits the day (higher is better) and the reasons, in words."""
    score, why = 0.0, []
    clothing = [p for p in pieces if p.category not in ("shoes", "accessory", "outerwear")]
    if all(p.warmth in warm for p in clothing):
        score += 2
    else:
        score -= 3
    if all(_fits_occasion(p, occasion) for p in pieces):
        score += 2
        if occasion != "everyday":
            why.append(f"right for {_OCCASION_SAY[occasion]}")
    else:
        score -= 2
    rests = [_days_since(p.last_worn, today) for p in pieces]
    rested = [r for r in rests if r is not None]
    if not rested or min(rested) >= 7:
        score += 1
        why.append("nothing worn this past week" if rested else "not worn yet")
    elif min(rested) <= 1:
        score -= 2
    bold = {b for b in (_bold(p.color) for p in pieces) if b}
    if len(bold) > 1:
        score -= 1
    elif bold:
        why.append(f"the {next(iter(bold))} stands out against neutrals")
    if any(p.condition == "needs repair" for p in pieces):
        score -= 4
    return score, why


_OCCASION_SAY = {"work": "work", "gym": "the gym", "date": "a date", "dressy": "a dressy day", "outdoors": "outdoors",
                 "lounge": "a day in", "everyday": "an everyday day"}


def _usable(p: Piece) -> bool:
    """A piece that can be worn today: clean and not waiting on a repair."""
    return not p.in_wash and p.condition != "needs repair"


def _best(candidates: list[Piece], occasion: str, warm: tuple, today: date) -> Optional[Piece]:
    """The piece of a category that suits the day best: the occasion, the warmth, then the longest rested."""
    def rank(p: Piece):
        rest = _days_since(p.last_worn, today)
        return (_fits_occasion(p, occasion), p.warmth in warm, rest if rest is not None else 9999, -p.times_worn)
    pool = [p for p in candidates if _usable(p)]
    return max(pool, key=rank) if pool else None


def suggest(pieces: list[Piece], outfits: list[Outfit], weather: Optional[dict], occasion: str, today: date,
            limit: int = 3) -> dict:
    """Up to `limit` outfits for the day, best first: saved outfits whose pieces are all clean and suit the day (low
    rated ones, 2 stars or under, and ones too warm or too light for a known forecast, left out), then one put together from the pieces (a dress or a top and bottom, shoes,
    and outerwear when it's cool or wet). After the best, a pick that scores below zero (wrong warmth, worn yesterday)
    is dropped. Each pick has its piece ids, a name, a score and why. Also says what the day
    needs (warmth, outerwear, occasion) and when the closet can't dress it (no clean pieces of a kind)."""
    temp = temperature_f(weather)
    wet = is_wet(weather)
    warm = warmth_wanted(temp)
    outer_needed = needs_outerwear(temp, wet)
    by_id = {p.piece_id: p for p in pieces}
    picks = []

    for o in outfits:
        got = [by_id[i] for i in o.piece_ids if i in by_id]
        if len(got) < 2 or not all(_usable(p) for p in got):
            continue
        if o.stars is not None and o.stars <= 2:
            continue
        if temp is not None and not all(p.warmth in warm for p in got
                                        if p.category not in ("shoes", "accessory", "outerwear")):
            continue  # wrong for the weather, however well it's rated
        score, why = _score_pieces(got, occasion, warm, today)
        if o.stars is not None:
            score += (o.stars - 3)
            if o.stars >= 4:
                why.insert(0, f"you rated it {o.stars:g} stars")
        if outer_needed and not any(p.category == "outerwear" for p in got):
            outer = _best([p for p in pieces if p.category == "outerwear" and (p.waterproof or not wet)],
                          occasion, warm, today)
            if outer is not None:
                got = got + [outer]
                why.append(f"add the {outer.name}" + (" for the rain" if wet else " for the cold"))
        picks.append({"outfit_id": o.outfit_id, "name": o.name, "piece_ids": [p.piece_id for p in got],
                      "score": round(score, 1), "why": why, "saved": True})

    made, missing = _put_together(pieces, occasion, warm, outer_needed, wet, today)
    if made:
        score, why = _score_pieces(made, occasion, warm, today)
        ids = [p.piece_id for p in made]
        if not any(set(ids) == set(p["piece_ids"]) for p in picks):
            picks.append({"outfit_id": "", "name": " + ".join(p.name for p in made), "piece_ids": ids,
                          "score": round(score - 0.5, 1), "why": why or ["put together from what's clean"],
                          "saved": False})

    picks.sort(key=lambda x: -x["score"])
    picks = [p for i, p in enumerate(picks) if i == 0 or p["score"] >= 0]  # a pick that doesn't suit the day goes
    return {"occasion": occasion, "temp_f": temp, "wet": wet, "warmth": list(warm), "outerwear": outer_needed,
            "weather_known": temp is not None, "picks": picks[:limit], "missing": missing}


def _put_together(pieces: list[Piece], occasion: str, warm: tuple, outer_needed: bool, wet: bool,
                  today: date) -> tuple[list[Piece], list[str]]:
    """One outfit from the pieces (a dress, or a top and a bottom; shoes; a layer on a cold day; outerwear when
    needed), and what the closet is missing to dress the day."""
    of = lambda cat: [p for p in pieces if p.category == cat]  # noqa: E731
    chosen, missing = [], []
    top, bottom, dress = (_best(of(c), occasion, warm, today) for c in ("top", "bottom", "dress"))
    if dress is not None and (top is None or bottom is None or
                              (_fits_occasion(dress, occasion) and not _fits_occasion(top, occasion))):
        chosen.append(dress)
    elif top is not None and bottom is not None:
        chosen += [top, bottom]
    else:
        missing.append("a clean top and bottom" if not of("dress") else "a clean top and bottom, or a dress")
        return [], missing
    if "warm" in warm and warm[0] == "warm":
        layer = _best(of("layer"), occasion, warm, today)
        if layer is not None:
            chosen.append(layer)
    shoes = _best(of("shoes"), occasion, warm, today)
    if shoes is not None:
        chosen.append(shoes)
    else:
        missing.append("clean shoes")
    if outer_needed:
        outer = _best([p for p in of("outerwear") if p.waterproof or not wet], occasion, warm, today)
        if outer is not None:
            chosen.append(outer)
        else:
            missing.append("a rain jacket" if wet else "a jacket or coat")
    return chosen, missing


def insights(pieces: list[Piece], outfits: list[Outfit], today: date) -> dict:
    """What the closet says about itself: pieces unworn for a long time (or never, half a year after they came in) to
    think about letting go of, the most worn, the best rated outfits, pieces waiting in the wash or on a repair, and
    gaps (no shoes, no outerwear, nothing waterproof, no gym clothes)."""
    unworn = []
    for p in pieces:
        rest = _days_since(p.last_worn, today) if p.last_worn else _days_since(p.created_at, today)
        if rest is not None and rest >= _UNWORN_DAYS:
            unworn.append({"piece_id": p.piece_id, "name": p.name, "days": rest, "never": not p.last_worn})
    most = sorted((p for p in pieces if p.times_worn), key=lambda p: -p.times_worn)[:3]
    rated = sorted((o for o in outfits if o.stars is not None), key=lambda o: -o.stars)[:3]
    gaps = []
    cats = {p.category for p in pieces}
    if pieces and "shoes" not in cats:
        gaps.append("shoes")
    if pieces and "outerwear" not in cats:
        gaps.append("a jacket or coat")
    elif pieces and not any(p.waterproof for p in pieces if p.category == "outerwear"):
        gaps.append("something waterproof")
    if pieces and not any("gym" in p.occasions for p in pieces):
        gaps.append("gym clothes")
    return {"unworn": sorted(unworn, key=lambda x: -x["days"]),
            "most_worn": [{"piece_id": p.piece_id, "name": p.name, "times": p.times_worn} for p in most],
            "top_rated": [{"outfit_id": o.outfit_id, "name": o.name, "stars": o.stars} for o in rated],
            "in_wash": [p.name for p in pieces if p.in_wash],
            "needs_repair": [p.name for p in pieces if p.condition == "needs repair"],
            "gaps": gaps}
