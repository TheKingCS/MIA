"""
core.insurance
================

The insurance check-up (Zac, 2026-10-18 idea, picked 2026-10-19:
`docs/future/IDEAS.md` #1, DEC-0034): keep your policies in one place,
see what they cost and what's worth a look, and shop them with quotes
you collect, compared fairly.

**Policies** (InsuranceBook, a household store, `insurance.json`): car,
home, renters, health, life, umbrella. Each has its insurer, premium and
how often it's paid, renewal date, deductible, and coverage written one
per line ("Bodily injury: 100,000/300,000", "Collision: included"). A
policy's PDF (the declarations page) can fill the form for you to check
(`read_policy`); nothing is saved until you approve it.

**What's worth a look** (`checks`, pure logic, said as questions, never
advice from a licensed agent): a renewal coming up; a price that went up
since last term; full coverage on an older car; a low deductible your
savings could cover; car and home with different insurers (a bundle).

**Shopping it:** what an agent will ask for (`CHECKLISTS`), and a
quote-request email MIA drafts with your current coverage (you press
Send; MIA never sends, and never fills in an insurer's website). The
quotes you get back go in as quotes, and `compare` lines them up against
the policy, same coverage against same coverage, so a cheaper quote that
covers less is called out, never hidden.

**Switching:** "Switch To This" makes a mission with the steps (start the
new policy before cancelling the old one, no gap); "I Switched" puts the
new insurer, price and coverage on the policy and records what it saves
(`insurance_switched` in the history, a money win the Chronicle counts).

A renewal heads-up goes through the communication gate about 45 days
before (`renewal_notes`). Never on a child's account (not in CHILD_APPS).
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILE_NAME = "insurance.json"
KINDS = ("Car", "Home", "Renters", "Health", "Life", "Umbrella", "Other")
EVERY = ("Month", "Quarter", "6 Months", "Year")
PER_YEAR = {"Month": 12, "Quarter": 4, "6 Months": 2, "Year": 1}
RENEWAL_HEADS_UP_DAYS = 45
ROSE_WORTH_A_LOOK = 0.10
OLD_CAR_YEARS = 10
ICONS = {"Car": "🚗", "Home": "🏠", "Renters": "🔑", "Health": "🩺", "Life": "🕊️", "Umbrella": "☂️", "Other": "📄"}

# What an agent asks for, by kind (shown on Shop It; nothing is sent anywhere).
CHECKLISTS = {
    "Car": ["Each driver's name, birth date and license number", "Each vehicle's year, make, model and VIN",
            "Where it's parked overnight and about how many miles a year", "Accidents or tickets in the last 5 years",
            "Your current declarations page (same limits make the quotes comparable)"],
    "Home": ["The address, year built, square feet and roof age", "Updates (roof, wiring, plumbing, heating) and when",
             "Claims in the last 5 years", "Your current declarations page", "Alarms, sprinklers, or a dog"],
    "Renters": ["The address and how much your things are worth", "Claims in the last 5 years",
                "Your current declarations page"],
    "Health": ["Everyone to be covered and their birth dates", "Your doctors and prescriptions",
               "What you paid out of pocket last year", "Your current plan's summary of benefits"],
    "Life": ["Your birth date, height, weight and health history", "How much coverage and for how long",
             "Who the beneficiaries are"],
    "Umbrella": ["Your car and home policies' liability limits", "Drivers in the household, pools, trampolines, dogs"],
    "Other": ["Your current policy's declarations page", "Claims in the last 5 years"],
}

# Coverage names people (and policies) write differently.
COVERAGE_NAMES = {
    "bi": "bodily injury", "bodily injury liability": "bodily injury", "bodily injury": "bodily injury",
    "pd": "property damage", "property damage liability": "property damage", "property damage": "property damage",
    "um": "uninsured motorist", "uninsured motorist": "uninsured motorist", "uim": "underinsured motorist",
    "underinsured motorist": "underinsured motorist", "uninsured/underinsured motorist": "uninsured motorist",
    "med pay": "medical payments", "medical payments": "medical payments", "pip": "personal injury protection",
    "personal injury protection": "personal injury protection", "collision": "collision",
    "comprehensive": "comprehensive", "other than collision": "comprehensive", "rental": "rental reimbursement",
    "rental reimbursement": "rental reimbursement", "roadside": "roadside assistance",
    "roadside assistance": "roadside assistance", "towing": "roadside assistance",
    "dwelling": "dwelling", "coverage a": "dwelling", "other structures": "other structures",
    "coverage b": "other structures", "personal property": "personal property", "coverage c": "personal property",
    "loss of use": "loss of use", "coverage d": "loss of use", "personal liability": "personal liability",
    "coverage e": "personal liability", "liability": "personal liability", "medical payments to others": "medical payments",
    "coverage f": "medical payments", "out-of-pocket maximum": "out-of-pocket maximum",
    "out of pocket maximum": "out-of-pocket maximum", "death benefit": "death benefit",
}


# ------------------------------------------------------------------ the records


@dataclass
class Policy:
    policy_id: str
    kind: str
    insurer: str
    premium: float = 0.0  # per `every`
    every: str = "6 Months"
    renews: Optional[str] = None  # ISO date
    deductible: float = 0.0
    coverage: str = ""  # one per line: "Bodily injury: 100,000/300,000"
    asset_id: str = ""  # what it covers (a vehicle, the house), optional
    policy_number: str = ""
    agent_email: str = ""
    last_premium: float = 0.0  # last term's premium, per `every` (to see the change)
    note: str = ""
    name: str = ""  # "Truck insurance"; made from the kind when left out
    created_at: str = ""
    updated_at: str = ""
    chosen_quote_id: str = ""  # "Switch To This" pressed for this quote


@dataclass
class Quote:
    quote_id: str
    policy_id: str
    insurer: str
    premium: float = 0.0
    every: str = "6 Months"
    deductible: float = 0.0
    coverage: str = ""
    received: Optional[str] = None
    note: str = ""
    name: str = ""
    created_at: str = ""


def _clean(cls, data: dict) -> dict:
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in names}


class InsuranceBook:
    """The household's policies and the quotes collected for them."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self.policies: list[Policy] = []
        self.quotes: list[Quote] = []
        self.noted: list[str] = []  # renewal heads-ups already given (once per renewal)
        self._load()

    def _load(self) -> None:
        self.policies, self.quotes, self.noted = [], [], []
        if not self._file.exists():
            return
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            self.policies = [Policy(**_clean(Policy, p)) for p in data.get("policies") or []]
            self.quotes = [Quote(**_clean(Quote, q)) for q in data.get("quotes") or []]
            self.noted = [str(n) for n in data.get("noted") or []]
        except (OSError, ValueError, TypeError):
            log.exception("Couldn't read %s; starting with no policies.", FILE_NAME)

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "policies": [asdict(p) for p in self.policies],
                                                  "quotes": [asdict(q) for q in self.quotes],
                                                  "noted": self.noted[-100:]}, indent=2))

    def note_given(self, fingerprint: str) -> bool:
        """Remember a renewal heads-up; False if it was already given."""
        if fingerprint in self.noted:
            return False
        self.noted.append(fingerprint)
        self._save()
        return True

    # -- policies
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return next((p for p in self.policies if p.policy_id == policy_id), None)

    def add_policy(self, kind: str, insurer: str, premium: float = 0.0, every: str = "6 Months", **values) -> Policy:
        _check(kind, every, premium)
        now = datetime.now().isoformat(timespec="seconds")
        policy = Policy(policy_id=uuid.uuid4().hex[:10], kind=kind, insurer=insurer.strip(), premium=float(premium or 0),
                        every=every or "6 Months", created_at=now, updated_at=now,
                        **{k: v for k, v in values.items() if k in Policy.__dataclass_fields__ and v is not None})
        if not policy.name:
            policy.name = f"{kind} insurance"
        self.policies.append(policy)
        self._save()
        return policy

    def update_policy(self, policy_id: str, **values) -> Policy:
        policy = self.get_policy(policy_id)
        if policy is None:
            raise ValueError("That policy isn't there anymore.")
        for key, value in values.items():
            if key in Policy.__dataclass_fields__ and key != "policy_id":
                setattr(policy, key, "" if value is None and isinstance(getattr(policy, key), str) else value)
        _check(policy.kind, policy.every, policy.premium)
        policy.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return policy

    def delete_policy(self, policy_id: str) -> None:
        if self.get_policy(policy_id) is None:
            raise ValueError("That policy isn't there anymore.")
        self.policies = [p for p in self.policies if p.policy_id != policy_id]
        self.quotes = [q for q in self.quotes if q.policy_id != policy_id]
        self._save()

    # -- quotes
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        return next((q for q in self.quotes if q.quote_id == quote_id), None)

    def quotes_for(self, policy_id: str) -> list[Quote]:
        return [q for q in self.quotes if q.policy_id == policy_id]

    def add_quote(self, policy_id: str, insurer: str, premium: float = 0.0, every: str = "6 Months", **values) -> Quote:
        policy = self.get_policy(policy_id)
        if policy is None:
            raise ValueError("Pick the policy this quote is for.")
        _check(policy.kind, every, premium)
        quote = Quote(quote_id=uuid.uuid4().hex[:10], policy_id=policy_id, insurer=insurer.strip(),
                      premium=float(premium or 0), every=every or "6 Months",
                      created_at=datetime.now().isoformat(timespec="seconds"),
                      **{k: v for k, v in values.items() if k in Quote.__dataclass_fields__ and v is not None})
        if not quote.name:
            quote.name = f"{quote.insurer} quote"
        self.quotes.append(quote)
        self._save()
        return quote

    def update_quote(self, quote_id: str, **values) -> Quote:
        quote = self.get_quote(quote_id)
        if quote is None:
            raise ValueError("That quote isn't there anymore.")
        for key, value in values.items():
            if key in Quote.__dataclass_fields__ and key not in ("quote_id",):
                setattr(quote, key, "" if value is None and isinstance(getattr(quote, key), str) else value)
        self._save()
        return quote

    def delete_quote(self, quote_id: str) -> None:
        if self.get_quote(quote_id) is None:
            raise ValueError("That quote isn't there anymore.")
        self.quotes = [q for q in self.quotes if q.quote_id != quote_id]
        for p in self.policies:
            if p.chosen_quote_id == quote_id:
                p.chosen_quote_id = ""
        self._save()

    def switched(self, policy_id: str, quote_id: str) -> tuple[Policy, float]:
        """The person switched to this quote: the policy becomes it, the
        quotes for it are cleared. Returns (policy, saved per year)."""
        policy, quote = self.get_policy(policy_id), self.get_quote(quote_id)
        if policy is None or quote is None or quote.policy_id != policy_id:
            raise ValueError("That quote isn't there anymore.")
        saved = round(annual(policy.premium, policy.every) - annual(quote.premium, quote.every), 2)
        policy.last_premium, old_every = policy.premium, policy.every
        policy.insurer, policy.premium, policy.every = quote.insurer, quote.premium, quote.every
        policy.deductible = quote.deductible
        if quote.coverage.strip():
            policy.coverage = quote.coverage
        if old_every != policy.every:  # last term in the new term's length, so the change reads right
            policy.last_premium = round(annual(policy.last_premium, old_every) / PER_YEAR.get(policy.every, 1), 2)
        policy.chosen_quote_id = ""
        policy.renews = None  # the new policy's own date: put it in when it comes
        policy.updated_at = datetime.now().isoformat(timespec="seconds")
        self.quotes = [q for q in self.quotes if q.policy_id != policy_id]
        self._save()
        return policy, saved


def _check(kind: str, every: str, premium) -> None:
    if kind not in KINDS:
        raise ValueError("Pick what kind of insurance it is.")
    if every not in PER_YEAR:
        raise ValueError("Pick how often it's paid.")
    if float(premium or 0) < 0:
        raise ValueError("The premium can't be negative.")


# ------------------------------------------------------------------ pure logic


def annual(premium: float, every: str) -> float:
    """Pure logic. A premium paid `every` as a year's cost."""
    return round(float(premium or 0) * PER_YEAR.get(every, 1), 2)


def _amounts(text: str) -> list[float]:
    """Pure logic. "100,000/300,000" → [100000, 300000]; "$1,000 deductible" → [1000];
    "100/300" (thousands, the way policies write them) → [100000, 300000]."""
    found = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]
    if "/" in text and found and all(x < 1000 for x in found) and not re.search(r"\$\s*\d", text):
        found = [x * 1000 for x in found]
    return found


def coverage_key(name: str) -> str:
    plain = re.sub(r"\s+", " ", re.sub(r"[^a-z/ -]", " ", name.lower())).strip(" -")
    return COVERAGE_NAMES.get(plain, plain)


def parse_coverage(text: str) -> list[dict]:
    """Pure logic. One coverage a line, "Name: limit" → [{name, key, limit, amounts, included}]."""
    out = []
    for line in str(text or "").splitlines():
        line = line.strip(" -•*\t")
        if not line:
            continue
        name, sep, limit = line.partition(":")
        if not sep:
            m = re.match(r"(.*?)\s+(\$?\d.*)$", line)
            name, limit = (m.group(1), m.group(2)) if m else (line, "")
        name, limit = name.strip(), limit.strip()
        lowered = limit.lower()
        included = not lowered.startswith(("no", "none", "excluded", "declined", "not covered", "-"))
        out.append({"name": name, "key": coverage_key(name), "limit": limit or "included",
                    "amounts": _amounts(limit), "included": included})
    return out


def compare(policy: Policy, quotes: list[Quote]) -> dict:
    """Pure logic. The quotes against the policy, same coverage against same
    coverage. Each quote: what it costs a year, what it saves, and anything
    it covers less (a lower limit, a coverage it leaves out, a higher
    deductible), so a cheaper quote that covers less is never hidden."""
    current = parse_coverage(policy.coverage)
    now_year = annual(policy.premium, policy.every)
    rows_keys = [c["key"] for c in current]
    out_quotes = []
    for q in quotes:
        theirs = {c["key"]: c for c in parse_coverage(q.coverage)}
        less = []
        if q.coverage.strip():
            for c in current:
                if not c["included"]:
                    continue
                t = theirs.get(c["key"])
                if t is None or not t["included"]:
                    less.append(f"no {c['name']}")
                elif c["amounts"] and t["amounts"] and max(t["amounts"]) < max(c["amounts"]):
                    less.append(f"lower {c['name']} ({t['limit']} vs {c['limit']})")
        if q.deductible and policy.deductible and q.deductible > policy.deductible:
            less.append(f"higher deductible ({_money(q.deductible)} vs {_money(policy.deductible)})")
        year = annual(q.premium, q.every)
        out_quotes.append({"id": q.quote_id, "insurer": q.insurer, "per_year": year, "saves": round(now_year - year, 2),
                           "covers_less": less, "same_coverage": not less and bool(q.coverage.strip()),
                           "unknown_coverage": not q.coverage.strip(), "received": q.received or "",
                           "deductible": q.deductible, "note": q.note,
                           "coverage": {k: v["limit"] for k, v in theirs.items()},
                           "chosen": policy.chosen_quote_id == q.quote_id})
    for k in [k for q in quotes for k in (c["key"] for c in parse_coverage(q.coverage))]:
        if k not in rows_keys:
            rows_keys.append(k)
    names = {c["key"]: c["name"] for c in current}
    for q in quotes:
        for c in parse_coverage(q.coverage):
            names.setdefault(c["key"], c["name"])
    rows = [{"key": k, "name": names.get(k, k.title()),
             "current": next((c["limit"] for c in current if c["key"] == k), "—"),
             "quotes": [oq["coverage"].get(k, "—") for oq in out_quotes]} for k in rows_keys]
    out_quotes.sort(key=lambda q: (bool(q["covers_less"]), q["per_year"]))
    best = next((q for q in out_quotes if q["same_coverage"] and q["saves"] > 0), None)
    return {"per_year": now_year, "rows": rows, "quotes": out_quotes,
            "best": best["id"] if best else "", "best_saves": best["saves"] if best else 0.0}


def _money(value: float) -> str:
    from core.region import money

    try:
        return money(value)
    except Exception:
        return f"${value:,.2f}"


def _vehicle_year(context, asset_id: str) -> Optional[int]:
    maintenance = getattr(context, "maintenance", None)
    asset = maintenance.get_asset(asset_id) if maintenance is not None and asset_id else None
    if asset is None:
        return None
    m = re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", f"{asset.name} {asset.model}")
    if m:
        return int(m.group(1))
    return int(asset.purchase_date[:4]) if (asset.purchase_date or "")[:4].isdigit() else None


def checks(context, policy: Policy, policies: list[Policy], today: Optional[date] = None) -> list[dict]:
    """What's worth a look on a policy: [{tone, text}], plain questions."""
    today = today or date.today()
    out = []
    if policy.renews:
        try:
            days = (date.fromisoformat(policy.renews) - today).days
        except ValueError:
            days = None
        if days is not None and 0 <= days <= RENEWAL_HEADS_UP_DAYS:
            out.append({"tone": "soon", "text": f"Renews in {days} days: a good time to get a couple of quotes."})
        elif days is not None and days < 0:
            out.append({"tone": "soon", "text": "The renewal date has passed: put in the new term's date and price."})
    if policy.last_premium and policy.premium > policy.last_premium * (1 + ROSE_WORTH_A_LOOK):
        rise = (policy.premium - policy.last_premium) / policy.last_premium
        extra = annual(policy.premium - policy.last_premium, policy.every)
        out.append({"tone": "soon", "text": f"Up {rise:.0%} since last term ({_money(extra)} more a year): worth shopping."})
    coverage = {c["key"]: c for c in parse_coverage(policy.coverage)}
    if policy.kind == "Car" and any(coverage.get(k, {}).get("included") for k in ("collision", "comprehensive")):
        year = _vehicle_year(context, policy.asset_id)
        if year and today.year - year >= OLD_CAR_YEARS:
            out.append({"tone": "info", "text": f"Collision and comprehensive on a {year} vehicle: compare what they cost "
                                                f"with what it's worth now. Dropping them can save a lot on an older car."})
    if policy.kind in ("Car", "Home", "Renters") and 0 < policy.deductible < 1000:
        out.append({"tone": "info", "text": f"A {_money(policy.deductible)} deductible: if your savings could cover "
                                            f"{_money(1000)}, ask for a quote with that too. A higher deductible usually costs less."})
    if policy.kind == "Car":
        homes = [p for p in policies if p.kind in ("Home", "Renters")]
        if homes and all(h.insurer.strip().lower() != policy.insurer.strip().lower() for h in homes):
            out.append({"tone": "info", "text": "Your car and home are with different insurers: ask each for a bundle quote."})
    return out


def renewal_notes(context, today: Optional[date] = None) -> list[tuple[str, str, str]]:
    """The renewal heads-up, about 45 days before: (title, message, fingerprint)."""
    book = getattr(context, "insurance", None)
    today = today or date.today()
    out = []
    for p in book.policies if book is not None else []:
        if not p.renews:
            continue
        try:
            days = (date.fromisoformat(p.renews) - today).days
        except ValueError:
            continue
        if not 0 <= days <= RENEWAL_HEADS_UP_DAYS:
            continue
        rose = ""
        if p.last_premium and p.premium > p.last_premium:
            rose = f" Last term it went up {(p.premium - p.last_premium) / p.last_premium:.0%}."
        out.append((f"{ICONS.get(p.kind, '📄')} {p.name} renews in {days} days",
                    f"Your {p.name.lower()} with {p.insurer} renews on {_day(p.renews)}.{rose} "
                    f"Want to shop it? Insurance → Shop It drafts the quote requests.",
                    f"insurance_renewal:{p.policy_id}:{p.renews}"))
    return out


def _day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%B} {d.day}"


# ------------------------------------------------------------------ reading a policy


def read_policy(text: str) -> dict:
    """Pure logic. What a declarations page says, as the Add form's
    values for the person to check: insurer, kind, premium and how often,
    renewal date, deductible, coverage, policy number. Only what it finds."""
    t = " ".join(str(text or "").split())
    low = t.lower()
    out: dict = {}
    insurer = next((name for name in INSURERS if name.lower() in low), "")
    if insurer:
        out["insurer"] = insurer
    kind = ("Car" if re.search(r"\b(auto|vehicle|vin|collision|bodily injury)\b", low) else
            "Renters" if "renters" in low else
            "Home" if re.search(r"\b(homeowners?|dwelling)\b", low) else
            "Umbrella" if "umbrella" in low else
            "Life" if "life insurance" in low or "death benefit" in low else
            "Health" if re.search(r"\b(deductible.*out-of-pocket|out-of-pocket maximum|copay)\b", low) else "")
    if kind:
        out["kind"] = kind
    m = re.search(r"(?:total|policy|term|annual|6[- ]month)?\s*premium[^$\d]{0,30}\$?\s*([\d,]+\.\d{2})", t, re.I)
    if m:
        out["premium"] = float(m.group(1).replace(",", ""))
        out["every"] = ("6 Months" if re.search(r"6[- ]month|six[- ]month", low)
                        else "Month" if re.search(r"monthly|per month", low) else "Year")
    dates = re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", t)
    parsed = []
    for mm, dd, yy in dates:
        try:
            parsed.append(date(int(yy) + (2000 if len(yy) == 2 else 0), int(mm), int(dd)))
        except ValueError:
            continue
    if parsed:
        out["renews"] = max(parsed).isoformat()  # the policy period's end
    m = re.search(r"deductible[^$\d]{0,20}\$?\s*([\d,]{3,})", t, re.I)
    if m:
        out["deductible"] = float(m.group(1).replace(",", ""))
    m = re.search(r"policy (?:number|no\.?|#)\s*:?\s*([A-Z0-9-]{5,})", t, re.I)
    if m:
        out["policy_number"] = m.group(1)
    lines = []
    for name in ("Bodily Injury", "Property Damage", "Uninsured Motorist", "Underinsured Motorist", "Medical Payments",
                 "Personal Injury Protection", "Collision", "Comprehensive", "Rental Reimbursement", "Roadside",
                 "Dwelling", "Other Structures", "Personal Property", "Loss Of Use", "Personal Liability"):
        m = re.search(re.escape(name) + r"[^$\d]{0,30}(\$?\s*[\d,]+(?:\s*/\s*\$?\s*[\d,]+)?)", t, re.I)
        if m:
            lines.append(f"{name}: {m.group(1).replace(' ', '')}")
    if lines:
        out["coverage"] = "\n".join(lines)
    return out


# A few insurers by the name a policy prints (only to fill the form; type any other).
INSURERS = ("State Farm", "GEICO", "Progressive", "Allstate", "USAA", "Liberty Mutual", "Farmers", "Nationwide",
            "American Family", "Travelers", "Erie", "Auto-Owners", "The Hartford", "Kemper", "Mercury", "Safeco",
            "Country Financial", "Shelter", "Amica", "Root", "Lemonade", "Esurance", "MetLife", "Chubb",
            "Desjardins", "Intact", "Aviva", "Direct Line", "Admiral", "AAMI", "NRMA")


# ------------------------------------------------------------------ the quote request


def quote_request(context, policy: Policy) -> tuple[list[str], str, str]:
    """(to, subject, body) of the quote-request email MIA drafts."""
    profiles = getattr(context, "profiles", None)
    me = profiles.get_active_profile() if profiles is not None else None
    lines = ["Hello,", "", f"I'd like a quote for {policy.kind.lower()} insurance, with coverage the same as what I have now "
             "so I can compare them side by side.", ""]
    covered = parse_coverage(policy.coverage)
    if covered:
        lines += ["What I have now:"] + [f"- {c['name']}: {c['limit']}" for c in covered]
    if policy.deductible:
        lines.append(f"- Deductible: {_money(policy.deductible)}")
    maintenance = getattr(context, "maintenance", None)
    asset = maintenance.get_asset(policy.asset_id) if maintenance is not None and policy.asset_id else None
    if asset is not None:
        lines += ["", f"It covers: {asset.name}"]
    if policy.renews:
        lines += ["", f"My current policy renews on {_day(policy.renews)}, so I'd like the quote before then."]
    lines += ["", "Please include the price per term, the deductible and every limit.", "", "Thank you,",
              getattr(me, "name", "") or ""]
    to = [policy.agent_email] if policy.agent_email else []
    return to, f"Quote request: {policy.kind.lower()} insurance", "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------ the screen


def insurance_page(context, today: Optional[date] = None) -> dict:
    book = getattr(context, "insurance", None)
    if book is None:
        return {"available": False}
    today = today or date.today()
    policies = []
    could_save = 0.0
    for p in sorted(book.policies, key=lambda p: (KINDS.index(p.kind) if p.kind in KINDS else 99, p.name)):
        cmp = compare(p, book.quotes_for(p.policy_id))
        could_save += max(0.0, cmp["best_saves"])
        maintenance = getattr(context, "maintenance", None)
        asset = maintenance.get_asset(p.asset_id) if maintenance is not None and p.asset_id else None
        policies.append({**asdict(p), "id": p.policy_id, "icon": ICONS.get(p.kind, "📄"), "per_year": annual(p.premium, p.every),
                         "covers": asset.name if asset is not None else "", "coverage_lines": parse_coverage(p.coverage),
                         "checks": checks(context, p, book.policies, today), "compare": cmp,
                         "checklist": CHECKLISTS.get(p.kind, CHECKLISTS["Other"])})
    soon = [p for p in policies if p["renews"] and 0 <= (date.fromisoformat(p["renews"]) - today).days <= 60]
    from core.record_actions import record_form

    from core.insurance_actions import POLICY, QUOTE

    from core.region import currency_symbol_for

    return {"available": True, "policies": policies,
            "summary": {"policies": len(policies), "per_year": round(sum(p["per_year"] for p in policies), 2),
                        "renewing_soon": len(soon), "could_save": round(could_save, 2),
                        "currency_symbol": currency_symbol_for(context)},
            "forms": {"policy": record_form(POLICY), "quote": record_form(QUOTE)},
            "kinds": list(KINDS), "every": list(EVERY),
            "assets": [{"id": a.asset_id, "name": a.name} for a in
                       (getattr(context, "maintenance", None).all_assets()
                        if getattr(context, "maintenance", None) is not None else [])]}
