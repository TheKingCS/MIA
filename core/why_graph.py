"""
core.why_graph
=================

"Remember Why", slice B of docs/COGNITIVE_EXTENSION_PROPOSAL.md: the
owner's reasons as a chain, with live evidence from their own records,
assembled in code so the model can only phrase it, never invent it.

Two layers, deliberately separate (proposal, question 7):

1. **The chain is the owner's.** Intents (core/intent_manager.py) can
   serve a bigger Intent (`serves_intent_id`) and carry a `reason` in the
   owner's words: "Factory work" -> "Pay off debt" -> "Control over my
   time". MIA never invents a reason; she stores what she's told.
2. **The evidence is computed, never stored.** For each link, facts from
   the managers that own them: debt totals, rentals and their rent,
   income, linked Projects. Plus recent wins (completed missions and
   projects, "Wins" memories). Same "live read, not a second source of
   truth" stance as core/context_assembler.py.

The one stored thing is a small **monthly checkpoint** of headline
numbers (data/why_checkpoints.json), which is what makes "look what
changed since June" possible without a history of every record.

**"This used to be why."** A link is *done* when its Intent is marked
Achieved/Archived, or when it's a debt goal and the debt that existed at
the first checkpoint is now paid off. The fact sheet says so, so MIA can
tell the owner their reason has changed instead of repeating an
outdated one.

Keyword matching decides which evidence belongs to a link (a goal named
"Pay off debt" gets debt facts). It's deterministic and inspectable, and
a link it can't place still shows up with the owner's reason and any
linked Projects.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CHECKPOINTS_FILE = _DATA_DIR / "why_checkpoints.json"

DONE_STATUSES = ("Achieved", "Archived")
_RECENT_DAYS = 30

_DEBT_WORDS = re.compile(r"\b(debts?|loans?|owe|owing|credit cards?|pay ?off|payoff|debt[- ]free)\b")
_RENTAL_WORDS = re.compile(r"\b(rent|rental|rentals|landlord|tenants?|propert(?:y|ies)|real estate|duplex)\b")
_LAND_WORDS = re.compile(r"\b(land|homestead|acres?|farm|greenhouse|walipini|wallipini|aquaponics)\b")
_WORK_WORDS = re.compile(r"\b(work|job|shift|factory|paycheck|income|overtime|wages?|salary)\b")


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _month_name(month: str) -> str:
    try:
        return datetime.strptime(month, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return month


@dataclass
class WhyLink:
    intent_id: str
    name: str
    reason: str = ""
    done: bool = False
    done_because: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass
class WhySheet:
    chains: list[list[WhyLink]] = field(default_factory=list)
    wins: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.chains

    def to_text(self) -> str:
        """The fact sheet, plain text, for the model or for reading back."""
        lines: list[str] = []
        for chain in self.chains:
            lines.append("Chain: " + " -> ".join(link.name for link in chain))
            for link in chain:
                header = f"- {link.name}"
                if link.reason:
                    header += f' (their words: "{link.reason}")'
                if link.done:
                    header += f" [DONE: {link.done_because}. This used to be a reason; it's complete now.]"
                lines.append(header)
                lines.extend(f"    * {fact}" for fact in link.evidence)
        if self.changes:
            lines.append("What changed:")
            lines.extend(f"- {c}" for c in self.changes)
        if self.wins:
            lines.append("Recent wins:")
            lines.extend(f"- {w}" for w in self.wins)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Headline numbers (also what a checkpoint stores)
# ---------------------------------------------------------------------------


def headline_numbers(context, today: Optional[date] = None) -> dict:
    today = today or date.today()
    start = (today - timedelta(days=_RECENT_DAYS)).isoformat()
    numbers: dict = {}
    budget = getattr(context, "budget", None)
    if budget is not None:
        debts = budget.all_debts()
        numbers["total_debt"] = round(sum(d.balance for d in debts), 2)
        numbers["open_debts"] = sum(1 for d in debts if d.balance > 0)
        numbers["income_30d"] = round(budget.total_income(start, today.isoformat()), 2)
    real_estate = getattr(context, "real_estate", None)
    if real_estate is not None:
        properties = real_estate.all_properties()
        rentals = [p for p in properties if p.property_type in ("Rental", "Investment")]
        numbers["rentals"] = len(rentals)
        numbers["land"] = sum(1 for p in properties if p.property_type == "Land")
        numbers["rent_30d"] = round(sum(
            e.amount for p in rentals for e in real_estate.income_for_property(p.property_id, start, today.isoformat())
        ), 2)
    projects = getattr(context, "projects", None)
    if projects is not None:
        all_projects = projects.all_projects()
        numbers["projects_complete"] = sum(1 for p in all_projects if p.status == "Complete")
        numbers["projects_active"] = sum(1 for p in all_projects if p.status == "Active")
    return numbers


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


def load_checkpoints() -> list[dict]:
    if not _CHECKPOINTS_FILE.exists():
        return []
    try:
        data = json.loads(_CHECKPOINTS_FILE.read_text(encoding="utf-8"))
        return [c for c in data if isinstance(c, dict) and "month" in c]
    except (json.JSONDecodeError, OSError):
        log.exception("why_checkpoints.json unreadable — ignoring it.")
        return []


def record_checkpoint_if_due(context, today: Optional[date] = None) -> None:
    """One checkpoint per calendar month, taken the first time the why
    is built that month. Cheap, and never overwrites an earlier month."""
    today = today or date.today()
    month = today.strftime("%Y-%m")
    checkpoints = load_checkpoints()
    if any(c["month"] == month for c in checkpoints):
        return
    checkpoints.append({"month": month, **headline_numbers(context, today)})
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_text(_CHECKPOINTS_FILE, json.dumps(checkpoints, indent=2))


def describe_changes(first: dict, now: dict) -> list[str]:
    """Pure logic. Plain statements of what moved since `first`."""
    since = _month_name(first.get("month", ""))
    changes = []
    before, after = first.get("total_debt"), now.get("total_debt")
    if before is not None and after is not None and before != after:
        direction = "down" if after < before else "up"
        changes.append(f"Debt is {direction} {_money(abs(before - after))} since {since} ({_money(before)} then, {_money(after)} now).")
    for key, noun in (("rentals", "rental"), ("land", "land parcel")):
        b, a = first.get(key), now.get(key)
        if b is not None and a is not None and a > b:
            changes.append(f"{a - b} more {noun}{'s' if a - b != 1 else ''} since {since} ({b} then, {a} now).")
    b, a = first.get("projects_complete"), now.get("projects_complete")
    if b is not None and a is not None and a > b:
        changes.append(f"{a - b} project{'s' if a - b != 1 else ''} completed since {since}.")
    return changes


# ---------------------------------------------------------------------------
# Building the sheet
# ---------------------------------------------------------------------------


def _chains(intents) -> list[list]:
    """Each chain runs from a goal nothing else serves, up to the top.
    Primary intent's chain first. Unlinked goals are single-link chains."""
    by_id = {i.intent_id: i for i in intents}
    served_by_someone = {i.serves_intent_id for i in intents if i.serves_intent_id in by_id}
    starts = [i for i in intents if i.intent_id not in served_by_someone]
    chains = []
    for start in starts:
        chain, seen, current = [], set(), start
        while current is not None and current.intent_id not in seen:
            chain.append(current)
            seen.add(current.intent_id)
            current = by_id.get(current.serves_intent_id) if current.serves_intent_id else None
        chains.append(chain)

    def has_primary(chain) -> bool:
        return any(i.primary for i in chain)

    chains.sort(key=lambda c: (not has_primary(c), -len(c)))
    return chains


def _evidence_for(intent, context, numbers: dict, first_checkpoint: Optional[dict]) -> tuple[list[str], str]:
    """(facts, done_because) for one link. done_because is '' unless done."""
    text = f"{intent.name} {intent.description} {intent.reason}".lower()
    facts: list[str] = []
    done_because = ""
    if intent.status in DONE_STATUSES:
        done_because = f"marked {intent.status}"

    if _DEBT_WORDS.search(text) and "total_debt" in numbers:
        total, open_count = numbers["total_debt"], numbers["open_debts"]
        if total > 0:
            facts.append(f"Debt now: {_money(total)} across {open_count} debt{'s' if open_count != 1 else ''}.")
        elif first_checkpoint and first_checkpoint.get("total_debt", 0) > 0:
            facts.append(f"All tracked debt is paid off (it was {_money(first_checkpoint['total_debt'])} in {_month_name(first_checkpoint['month'])}).")
            done_because = done_because or "the debt is paid off"
        elif context.budget is not None and context.budget.all_debts():
            facts.append("All tracked debts are at $0.")
    if _RENTAL_WORDS.search(text) and numbers.get("rentals") is not None:
        names = [p.name for p in context.real_estate.all_properties() if p.property_type in ("Rental", "Investment")]
        if names:
            facts.append(f"You own {len(names)} rental{'s' if len(names) != 1 else ''}: {', '.join(names)}.")
            if numbers.get("rent_30d"):
                facts.append(f"Rent received in the last {_RECENT_DAYS} days: {_money(numbers['rent_30d'])}.")
    if _LAND_WORDS.search(text) and numbers.get("land"):
        names = [p.name for p in context.real_estate.all_properties() if p.property_type == "Land"]
        facts.append(f"You own the land: {', '.join(names)}.")
    if _WORK_WORDS.search(text) and numbers.get("income_30d"):
        facts.append(f"Income in the last {_RECENT_DAYS} days: {_money(numbers['income_30d'])}.")

    projects = getattr(context, "projects", None)
    if projects is not None:
        for project in projects.all_projects():
            if project.intent_id == intent.intent_id:
                facts.append(f"Project '{project.name}': {project.status}.")
    return facts, done_because


def _wins(context, today: date) -> list[str]:
    cutoff = (today - timedelta(days=_RECENT_DAYS)).isoformat()
    wins: list[str] = []
    missions = getattr(context, "missions", None)
    if missions is not None:
        done = [m for m in missions.all_missions() if m.status == "completed" and (m.updated_at or "") >= cutoff]
        done.sort(key=lambda m: m.updated_at or "", reverse=True)
        wins.extend(f"Completed the mission '{m.name}'." for m in done[:3])
    projects = getattr(context, "projects", None)
    if projects is not None:
        finished = [p for p in projects.all_projects() if p.status == "Complete" and (p.updated_at or "") >= cutoff]
        wins.extend(f"Finished the project '{p.name}'." for p in finished[:2])
    memories = getattr(context, "user_memories", None)
    if memories is not None:
        wins.extend(m.text for m in memories.all_memories() if m.category == "Wins")
    return wins[:6]


def build_why_sheet(context, today: Optional[date] = None, record_checkpoint: bool = True) -> WhySheet:
    today = today or date.today()
    intents_manager = getattr(context, "intents", None)
    intents = intents_manager.all_intents() if intents_manager is not None else []
    if record_checkpoint and intents:
        try:
            record_checkpoint_if_due(context, today)
        except OSError:
            log.exception("Couldn't record the monthly why checkpoint.")
    numbers = headline_numbers(context, today)
    checkpoints = sorted(load_checkpoints(), key=lambda c: c["month"])
    this_month = today.strftime("%Y-%m")
    earlier = [c for c in checkpoints if c["month"] < this_month]
    first = earlier[0] if earlier else None

    sheet = WhySheet()
    for chain in _chains(intents):
        links = []
        for intent in chain:
            facts, done_because = _evidence_for(intent, context, numbers, first)
            links.append(WhyLink(
                intent_id=intent.intent_id, name=intent.name, reason=intent.reason,
                done=bool(done_because), done_because=done_because, evidence=facts,
            ))
        sheet.chains.append(links)
    if first is not None:
        sheet.changes = describe_changes(first, numbers)
    sheet.wins = _wins(context, today)
    return sheet


def chain_text_for(context, intent_id: str) -> str:
    """"Factory work -> Pay off debt -> Control over my time" for the chain containing intent_id."""
    for chain in _chains(context.intents.all_intents()):
        if any(i.intent_id == intent_id for i in chain):
            return " → ".join(i.name for i in chain)
    return ""
