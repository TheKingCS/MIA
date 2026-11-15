"""
core.price_book
=================

Prices MIA has seen, and what a thing really costs (Procurement P2, DEC-0172; the proposal's section 5).

**Observations** (`PriceObservation`, `PriceBook`, `price_observations.json` in the person's folder, sealed): each
price seen, with the item in the words it was seen under, a key for the product (`product_key`: its model number when
it has one, else its significant words and its specs), the store, the price, the unit and quantity it's for (so a
unit price can be worked out), whether it was in stock, where it came from (a link, a find, or said by the person),
how it's known (`said` by the person, `observed` on a page), and when. Nothing is ever invented: the history starts
at the first observation.

**Judging a price** (`judge`): against what MIA has seen for the same product in the last 90 days, in code:
- with fewer than three observations: "I've only seen it N times", never a verdict;
- a **genuine low**: below every price seen in those 90 days;
- **usual**: within the range seen;
- **high**: above every price seen;
- a "was" price higher than any price ever seen is called out as not one MIA has seen.

**Total cost** (`total_cost`): the price plus shipping, sales tax, any fee and the trip there and back, each part
named with where it came from; a part that isn't known is listed as unknown, never counted as zero, and the total
says so. The trip uses the person's own cost per mile (Zac, 2026-11-15: "use my own figures"; their setting
`procurement.cost_per_mile`, or worked out from miles per gallon and a fuel price they give); unknown until set.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = DATA_DIR
_FILE = "price_observations.json"
WINDOW_DAYS = 90
MIN_SEEN = 3
KEEP_DAYS = 730  # two years of prices: enough for seasons and recurring sales


@dataclass
class PriceObservation:
    """One price seen (see the module's opening)."""
    observation_id: str
    product_key: str
    item: str
    store: str
    price: float
    quantity: float = 1.0  # how many the price is for
    unit: str = ""
    in_stock: Optional[bool] = None
    was: float = 0.0  # a "was" price the store showed, if any
    link: str = ""
    origin: str = "said"  # "said", a link, or "find:<id>"
    how: str = "said"  # "said" by the person, "observed" on a page
    at: str = ""

    def unit_price(self) -> float:
        """The price for one unit."""
        return self.price / self.quantity if self.quantity else self.price


def product_key(item: str, specs: str = "") -> str:
    """Pure logic. What makes two observations the same product: its model number when the words have one, else its
    significant words in order with its specs (core/product_specs), so "2x4 x 8 ft stud" at two stores is one key."""
    from core import product_specs, relevance

    found = product_specs.models(f"{item} {specs}")
    if found:
        return "model:" + sorted(found)[0]
    words = sorted(relevance.words_of(item))
    specs_read = product_specs.read(f"{item} {specs}")
    tail = ",".join(f"{k}={v}" for k, v in sorted(specs_read.items()))
    return "words:" + " ".join(words) + (f"|{tail}" if tail else "")


def judge(observations: list, price: float, now: datetime, was: float = 0.0) -> dict:
    """Pure logic. How a price compares with the observations of the same product in the last 90 days (see the
    module's opening): {verdict: too_few | low | usual | high, seen, lowest, highest, said, was_note}."""
    since = (now - timedelta(days=WINDOW_DAYS)).isoformat()
    recent = [o.unit_price() for o in observations if o.at >= since]
    out = {"seen": len(recent), "lowest": min(recent) if recent else None, "highest": max(recent) if recent else None,
           "was_note": ""}
    if was and observations and was > max(o.unit_price() for o in observations):
        out["was_note"] = "the “was” price is higher than any price I've seen for it"
    if len(recent) < MIN_SEEN:
        out.update(verdict="too_few", said=f"I've only seen it {len(recent)} time{'s' if len(recent) != 1 else ''}, "
                                           f"so I can't say yet whether that's a good price")
        return out
    if price < out["lowest"]:
        out.update(verdict="low", said="the lowest I've seen in 90 days")
    elif price > out["highest"]:
        out.update(verdict="high", said="higher than any price I've seen in 90 days")
    else:
        out.update(verdict="usual", said="within what I've seen in 90 days")
    return out


def total_cost(price: float, quantity: float = 1.0, shipping: Optional[float] = None,
               tax_rate: Optional[float] = None, fees: float = 0.0, miles: Optional[float] = None,
               cost_per_mile: Optional[float] = None) -> dict:
    """Pure logic. {parts: [{what, amount or None, how}], known_total, unknown: [what]} (see the module's opening).
    `miles` is one way; the trip is counted there and back."""
    parts = [{"what": "price", "amount": round(price * quantity, 2), "how": f"{quantity:g} at {price:.2f}"}]
    parts.append({"what": "shipping", "amount": None if shipping is None else round(shipping, 2),
                  "how": "as listed" if shipping is not None else "not known"})
    parts.append({"what": "tax", "amount": None if tax_rate is None else round(price * quantity * tax_rate, 2),
                  "how": f"at {tax_rate * 100:g}%" if tax_rate is not None else "rate not known"})
    if fees:
        parts.append({"what": "fees", "amount": round(fees, 2), "how": "as listed"})
    if miles is not None or cost_per_mile is not None:
        known = miles is not None and cost_per_mile is not None
        parts.append({"what": "trip", "amount": round(2 * miles * cost_per_mile, 2) if known else None,
                      "how": (f"{2 * miles:g} miles there and back at {cost_per_mile:.2f} a mile" if known
                              else "distance not known" if miles is None else "your cost per mile isn't set")})
    known = round(sum(p["amount"] for p in parts if p["amount"] is not None), 2)
    return {"parts": parts, "known_total": known, "unknown": [p["what"] for p in parts if p["amount"] is None]}


def cost_per_mile(context) -> Optional[float]:
    """The person's own cost per mile (their setting `procurement.cost_per_mile`, or `procurement.mpg` with
    `procurement.fuel_price`), or None when they haven't given it."""
    from core import person_settings

    try:
        direct = float(person_settings.get(context, "procurement.cost_per_mile", 0) or 0)
        if direct > 0:
            return direct
        mpg = float(person_settings.get(context, "procurement.mpg", 0) or 0)
        fuel = float(person_settings.get(context, "procurement.fuel_price", 0) or 0)
        return round(fuel / mpg, 3) if mpg > 0 and fuel > 0 else None
    except (TypeError, ValueError):
        return None


class PriceBook:
    """The person's price observations (price_observations.json, sealed, written atomically so undo restores it)."""

    # The epistemic contract (DEC-0173, G3): where each price came from, when, how it's known.
    EPISTEMIC = {"record": PriceObservation, "source": "origin", "at": "at", "how": "how"}

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the person's file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads the observations; an unreadable file is logged, reported and starts empty."""
        self.observations: list[PriceObservation] = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(open_text(self._file))
            fields = PriceObservation.__dataclass_fields__
            self.observations = [PriceObservation(**{k: v for k, v in d.items() if k in fields})
                                 for d in raw.get("observations", [])]
        except (ValueError, OSError, TypeError, AttributeError):
            log.exception("price_observations.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def _save(self) -> None:
        """Writes the observations atomically, keeping two years."""
        cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).isoformat()
        self.observations = [o for o in self.observations if o.at >= cutoff]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"observations": [asdict(o) for o in self.observations]}, indent=2))

    def record(self, item: str, store: str, price: float, quantity: float = 1.0, unit: str = "", specs: str = "",
               in_stock: Optional[bool] = None, was: float = 0.0, link: str = "", origin: str = "said",
               how: str = "said", at: Optional[str] = None) -> PriceObservation:
        """Keeps one price seen; ValueError without an item, a store or a positive price."""
        item, store = " ".join(str(item or "").split()), " ".join(str(store or "").split())
        if not item or not store:
            raise ValueError("What was it, and where?")
        if float(price) <= 0 or float(quantity or 1) <= 0:
            raise ValueError("What did it cost?")
        obs = PriceObservation(uuid.uuid4().hex[:10], product_key(item, specs), item[:120], store[:60], float(price),
                               float(quantity or 1), str(unit or ""), in_stock, float(was or 0), str(link or ""),
                               origin, how, at or datetime.now().isoformat(timespec="seconds"))
        self.observations.append(obs)
        self._save()
        return obs

    def for_product(self, key: str) -> list[PriceObservation]:
        """Every observation of one product, oldest first."""
        return sorted((o for o in self.observations if o.product_key == key), key=lambda o: o.at)

    def for_item(self, item: str, specs: str = "") -> list[PriceObservation]:
        """Every observation of the product these words name."""
        return self.for_product(product_key(item, specs))

    def best(self, item: str, specs: str = "", days: int = WINDOW_DAYS) -> list[PriceObservation]:
        """The latest price at each store in the last `days` for anything these words name (every significant word of
        the item in the observation's own words), cheapest per unit first. Matched by words, not the exact product
        key: a need's specs are what it requires, so whether each offer meets them is product_specs.verdict's call,
        and each offer's own price history stays under its product key. `specs` is accepted for symmetry."""
        from core.relevance import words_of

        wanted = words_of(item)
        since = (datetime.now() - timedelta(days=days)).isoformat()
        latest: dict = {}
        for o in sorted(self.observations, key=lambda o: o.at):
            if o.at >= since and wanted and wanted <= words_of(o.item):
                latest[(o.store.lower(), o.product_key)] = o
        return sorted(latest.values(), key=lambda o: o.unit_price())


_MONEY = re.compile(r"\$?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)")


def money_in(text: str) -> Optional[float]:
    """Pure logic. The first amount of money in some words ("$3.98", "12.50"), or None."""
    m = _MONEY.search(str(text or ""))
    return float(m.group(1).replace(",", "")) if m else None
