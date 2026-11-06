"""
core.question_plans
=====================

Question plans (DEC-0052 step 2a; docs/INTELLIGENCE_BENCHMARK.md section
4). The detailed questions people ask most ("What are my priorities
today?", "Which debt should I prioritize?") each get a plan: the lookups
it needs, run by code at once, the arithmetic between them done by code,
and every line of the result marked as a **fact** (from the records), a
**calculation**, an **estimate** or **missing**. The model then writes
one answer from that sheet, following Zac's answer protocol, and an
answer that states a number the sheet doesn't hold is replaced by the
sheet in plain words (`answer()`). The model never gathers, plans or
adds up; it phrases.

Which plan a question wants is decided by meaning: the question is
compared with each plan's example questions (Zac's benchmark questions
and a few more phrasings) through a small local embedding model
(`core/meaning.py`). Measured 2026-10-30: 23 of 25 rephrasings reached
the right plan and no small talk came near (docs/TOOL_CALLING_RESEARCH.md).
Without the embedding model (the phone) each plan's own words decide.

Facts come from MIA's own lookups (the Assistant's registry), so a plan
says exactly what the matching tool would, and a fix to a tool fixes
the plan too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

FACT, CALCULATION, ESTIMATE, MISSING = "fact", "calculation", "estimate", "missing"
MATCH_AT = 0.66  # cosine similarity to the nearest example (measured: small talk stayed below)
EXAMPLE_AT = 0.92  # this close to a plan's own example, a "how can I...?" question is that plan's, not a how-to


@dataclass
class Fact:
    kind: str  # FACT | CALCULATION | ESTIMATE | MISSING
    text: str
    source: str = ""  # the app or lookup it came from


@dataclass
class Sheet:
    plan: str
    title: str
    facts: list = field(default_factory=list)
    looked_up: list = field(default_factory=list)  # tool names run
    composed: list = field(default_factory=list)  # other plans gathered onto it (step 8)

    def add(self, kind: str, text: str, source: str = "") -> None:
        text = " ".join(str(text or "").split())
        if text and not any(f.text == text for f in self.facts):  # two plans on one sheet: each fact once
            self.facts.append(Fact(kind, text, source))

    def as_text(self) -> str:
        """The sheet for the model: one line each, marked."""
        return "\n".join(f"- [{f.kind}{', ' + f.source if f.source else ''}] {f.text}" for f in self.facts)

    def plain(self) -> str:
        """The sheet in plain words, for when there's no model (or its
        answer failed the number check)."""
        found = [f.text for f in self.facts if f.kind != MISSING]
        missing = [f.text for f in self.facts if f.kind == MISSING]
        out = " ".join(found) if found else "I don't have anything recorded for that yet."
        if missing and found:
            out += " Not recorded yet: " + " ".join(missing)
        return out


@dataclass
class Plan:
    name: str
    title: str
    examples: tuple  # questions it answers (Zac's benchmark, plus phrasings)
    words: str  # a regex: the plan's own words, used when there's no embedding model
    gather: Callable  # (context, sheet, prompt, today) -> None


# ---------------------------------------------------------------- lookups

_NOTHING = re.compile(r"^(you don't have|you have no|no |nothing|there (are|is) no|i don't have|none)", re.IGNORECASE)


def _look(context, sheet: Sheet, tool: str, source: str, **arguments) -> str:
    """Run one of MIA's own lookups and put what it says on the sheet."""
    registry = getattr(context, "assistant_actions", None)
    if registry is None or tool not in getattr(registry, "_actions", {}):
        return ""
    try:
        text = registry.execute(context, tool, arguments)
    except Exception:
        log.exception("Question plan lookup %s failed", tool)
        return ""
    sheet.looked_up.append(tool)
    sheet.add(MISSING if _NOTHING.match(text.strip()) else FACT, text, source)
    return text


def _money(context, amount: float) -> str:
    from core.region import money

    return money(amount)


def _month_bounds(day: date) -> tuple[date, date]:
    first = day.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return first, last


# ---------------------------------------------------------------- the plans' gathering


def _today(context, sheet, prompt, today):
    _look(context, sheet, "get_today", "Today")
    _look(context, sheet, "get_deadlines", "Compliance")
    _look(context, sheet, "list_calendar_events", "Calendar")
    _look(context, sheet, "show_my_why", "your goals")


def _play(context, sheet):
    from core import recreation

    for line in recreation.lines(context):
        sheet.add(CALCULATION, line, "Recreation")


def _week_review(context, sheet, prompt, today):
    _look(context, sheet, "get_weekly_checkin", "the weekly check-in")
    _play(context, sheet)
    _look(context, sheet, "get_life_events", "your history", period="week")
    _look(context, sheet, "get_workout_summary", "Workout")
    _look(context, sheet, "get_dungeon_loot", "the Dungeon (their job)")


def _money_month(context, sheet, prompt, today):
    budget = getattr(context, "budget", None)
    if budget is None:
        sheet.add(MISSING, "No budget is set up.", "Money")
        return
    first, last = _month_bounds(today)
    prev_first, prev_last = _month_bounds(first - timedelta(days=1))
    came_in, went_out = budget.total_income(first.isoformat(), today.isoformat()), \
        budget.total_expenses(first.isoformat(), today.isoformat())
    sheet.add(CALCULATION, f"This month so far ({first:%B} 1 to {today:%B} {today.day}): {_money(context, came_in)} came in, "
                           f"{_money(context, went_out)} went out, net {_money(context, came_in - went_out)}.", "Money")
    p_in, p_out = budget.total_income(prev_first.isoformat(), prev_last.isoformat()), \
        budget.total_expenses(prev_first.isoformat(), prev_last.isoformat())
    if p_in or p_out:
        sheet.add(CALCULATION, f"Last month ({prev_first:%B}): {_money(context, p_in)} in, {_money(context, p_out)} out, "
                               f"net {_money(context, p_in - p_out)}.", "Money")
    spent = [e for e in budget.all_expenses() if first.isoformat() <= (e.date or "")[:10] <= today.isoformat()]
    by_category: dict[str, float] = {}
    for e in spent:
        by_category[e.category] = by_category.get(e.category, 0.0) + float(e.amount or 0)
    if by_category:
        top = sorted(by_category.items(), key=lambda kv: -kv[1])[:5]
        sheet.add(CALCULATION, "Biggest spending this month: " + "; ".join(
            f"{name} {_money(context, amount)}" for name, amount in top) + ".", "Money")
        from_bank = sum(float(e.amount or 0) for e in spent if getattr(e, "plaid_transaction_id", ""))
        sheet.add(FACT, f"Of this month's spending, {_money(context, from_bank)} came from the bank sync and "
                        f"{_money(context, went_out - from_bank)} was entered by hand.", "Money")
    else:
        sheet.add(MISSING, "No spending recorded this month.", "Money")
    _look(context, sheet, "list_bills", "Money")
    _look(context, sheet, "list_untagged_charges", "Money")


def _debts(context, sheet, prompt, today):
    from core.debt_math import simulate

    budget = getattr(context, "budget", None)
    _look(context, sheet, "list_debts", "Money")
    _look(context, sheet, "get_debt_payoff_plan", "Money")
    if budget is None:
        return
    ranked = [p.debt for p in budget.debt_payoff_priority()]
    if not ranked:
        return
    if any(not (d.minimum_payment or 0) for d in ranked):
        sheet.add(MISSING, "Minimum payments missing for: " + ", ".join(d.name for d in ranked if not d.minimum_payment)
                  + ". The payoff dates assume nothing is paid on those.", "Money")
    now = simulate(ranked, 0, today)
    if now.debt_free:  # checked when it comes (core/calibration.py, step 8)
        from core.calibration import project

        project(context, "debt_free", now.debt_free, "debts")
    lines = [f"{r.name} paid off {r.paid_off}" if r.paid_off else f"{r.name} never, at its minimum" for r in now.debts]
    sheet.add(CALCULATION, f"At the minimums ({_money(context, now.monthly)} a month), in the payoff order: "
                           + "; ".join(lines) + (f". Debt-free {now.debt_free}" if now.debt_free else "")
                           + f"; about {_money(context, now.interest)} in interest.", "a payoff calculation")
    extra = _amount_in(prompt) or 200.0
    more = simulate(ranked, extra, today)
    if more.months is not None and (now.months is None or more.months < now.months):
        saved = now.interest - more.interest
        sheet.add(CALCULATION, f"With {_money(context, extra)} more a month to {ranked[0].name} first: debt-free "
                               f"{more.debt_free}" + (f", {now.months - more.months} months sooner" if now.months else "")
                               + f", about {_money(context, saved)} less interest.", "a payoff calculation")


def _freedom(context, sheet, prompt, today):
    _look(context, sheet, "get_freedom_progress", "Freedom")
    try:
        from core.web_dungeon import job_pay

        pay = job_pay(context, today)
    except Exception:
        pay = None
    if pay:
        hourly = pay["take_home_hourly"] or pay["hourly"]
        sheet.add(FACT, f"Pay ({pay['dungeon']}): {_money(context, hourly)} an hour "
                        f"{'take-home' if pay['take_home_hourly'] else 'before taxes'}, "
                        f"{pay['shift_hours']:g}-hour shifts; about {_money(context, pay['weekly_pace'])} a week lately.",
                  "the Dungeon (their job)")
    else:
        sheet.add(MISSING, "No pay rate in the Dungeon.", "the Dungeon (their job)")
    _look(context, sheet, "get_ledger_summary", "the business")
    _look(context, sheet, "get_financial_checkin", "Money")


def _next_dollar(context, sheet, prompt, today):
    amount = _amount_in(prompt)
    if amount:
        sheet.add(FACT, f"The amount asked about: {_money(context, amount)}.", "your question")
    _debts(context, sheet, "", today)
    _look(context, sheet, "get_freedom_progress", "Freedom")
    _look(context, sheet, "get_financial_checkin", "Money")
    sheet.add(ESTIMATE, "A common rule of thumb: an emergency fund of three to six months of living costs before "
                        "extra debt payments beyond the highest-rate debt; a rule of thumb, not advice for this person.",
              "general guidance")


def _rentals(context, sheet, prompt, today):
    estate = getattr(context, "real_estate", None)
    _look(context, sheet, "list_properties", "Real Estate")
    for p in (estate.all_properties() if estate is not None and hasattr(estate, "all_properties") else [])[:5]:
        _look(context, sheet, "get_property_summary", "Real Estate", property_name=p.name)


def _products(context, sheet, prompt, today):
    _look(context, sheet, "list_products", "Workshop")
    _look(context, sheet, "list_goods_on_hand", "Workshop")
    _look(context, sheet, "get_ledger_summary", "the business")


def _product_cost(context, sheet, prompt, today):
    _look(context, sheet, "list_products", "Workshop", query=_subject(prompt))
    _look(context, sheet, "get_build_costs", "Workshop", build=_subject(prompt))
    _look(context, sheet, "list_materials", "Workshop")
    sheet.add(ESTIMATE, "Labour and overhead aren't recorded per product: a price needs your time per piece and "
                        "what you want an hour for it.", "Workshop")


def _business_month(context, sheet, prompt, today):
    _look(context, sheet, "get_ledger_summary", "the business")
    _look(context, sheet, "get_business_use", "the business")
    _look(context, sheet, "list_jobs", "Workshop")


def _market_prep(context, sheet, prompt, today):
    _look(context, sheet, "list_goods_on_hand", "Workshop")
    _look(context, sheet, "list_materials", "Workshop")
    _look(context, sheet, "list_calendar_events", "Calendar")


def _progress(context, sheet, prompt, today):
    _look(context, sheet, "show_my_why", "your goals")
    _look(context, sheet, "list_missions", "Missions")
    _look(context, sheet, "get_learning_progress", "Skills")
    _look(context, sheet, "get_life_events", "your history", period="month")


def _coming_up(context, sheet, prompt, today):
    _look(context, sheet, "get_deadlines", "Compliance")
    _look(context, sheet, "list_calendar_events", "Calendar")
    _look(context, sheet, "list_upcoming_birthdays", "People", within_days=30)
    _look(context, sheet, "list_maintenance_tasks", "upkeep")
    _look(context, sheet, "list_bills", "Money")


def _tonight(context, sheet, prompt, today):
    _look(context, sheet, "get_today", "Today")
    _look(context, sheet, "list_alarms", "Alarms")
    _look(context, sheet, "list_calendar_events", "Calendar")
    _look(context, sheet, "get_loop", "the Loop")


def _noticed(context, sheet, prompt, today):
    """What MIA noticed across apps (core/findings.py), each with its why and next step."""
    from core.findings import DERIVED, as_line, findings

    found = findings(context, today)
    for f in found:
        sheet.add(CALCULATION if f.sureness == DERIVED else FACT, as_line(f), f.title)
    if not found:
        sheet.add(MISSING, "Nothing stands out across the apps right now: no bill before payday, no upkeep before a "
                           "trip, no deadline in a packed week, no stalled mission.", "findings")
    _look(context, sheet, "get_weekly_checkin", "the weekly check-in")
    _look(context, sheet, "list_maintenance_tasks", "upkeep")


def _afford(context, sheet, prompt, today):
    """Cross-domain (build plan step 8): a purchase against the month's money and the freedom date, worked out
    by core/freedom.plan() twice, as things stand and with the purchase."""
    from dataclasses import replace

    from core import freedom

    amount = _amount_in(prompt)
    monthly = bool(re.search(r"\b(a|per|each|every) month\b|\bmonthly\b", prompt.lower()))
    if amount:
        sheet.add(FACT, f"The amount asked about: {_money(context, amount)}{' a month' if monthly else ', once'}.",
                  "your question")
    else:
        sheet.add(MISSING, "The question doesn't say how much it costs.", "your question")
    _money_month(context, sheet, prompt, today)
    try:
        inputs, _history = freedom.gather(context, today)
        now = freedom.plan(inputs, today)
    except Exception:
        log.exception("The afford plan couldn't work out the freedom fund")
        now = None
    if now is None or not now.get("date"):
        sheet.add(MISSING, (now or {}).get("why_no_date") or "No freedom date to compare with.", "Freedom")
        return
    from core.calibration import project

    project(context, "freedom", now["date"], "afford")  # checked when it comes (step 8)
    sheet.add(CALCULATION, f"Freedom date as things stand: {now['date']} ({_money(context, now['left'] or 0)} to go, "
                           f"saving about {_money(context, inputs.pace)} a month).", "Freedom")
    if not amount:
        return
    after = freedom.plan(replace(inputs, pace=inputs.pace - amount) if monthly else
                         replace(inputs, saved=max(0.0, inputs.saved - amount)), today)
    if after.get("date"):
        later = (date.fromisoformat(after["date"]) - date.fromisoformat(now["date"])).days
        sheet.add(CALCULATION, f"With it: {after['date']}, {later} days later." if later > 0 else
                  "With it: the same freedom date.", "a freedom calculation")
    else:
        sheet.add(CALCULATION, "With it the fund stops growing: at that cost there's no freedom date.",
                  "a freedom calculation")
    sheet.add(ESTIMATE, "Both dates assume the last three months' saving pace holds.", "Freedom")


def _slipped(context, sheet, prompt, today):
    """Cross-domain (step 8): what slipped this week and the reasons the records hold, from several apps."""
    _look(context, sheet, "get_life_events", "your history", period="week")
    _look(context, sheet, "get_deadlines", "Compliance")
    _open_loops(context, sheet, prompt, today)
    _noticed(context, sheet, prompt, today)
    _look(context, sheet, "get_workout_summary", "Workout")


def _seasons(context, sheet, prompt, today):
    """Seasons of memory (build plan step 10, core/seasons.py): a month or a year against the one before, in code."""
    from core import seasons

    label, lines = seasons.season(context, seasons.kind_in(prompt, today), today)
    for line in lines:
        sheet.add(MISSING if line.startswith("Nothing recorded") else CALCULATION, line, "your history")


def _operating(context, sheet, prompt, today):
    """The Operating Journal (DEC-0097, core/operating_journal.py): each line against what the records show."""
    from core import operating_journal
    from core.region import money

    lines = operating_journal.picture(context, today, money_word=lambda v: money(v))
    if not lines:
        sheet.add(MISSING, "There's no Operating Journal yet: say \"add to my operating journal\" and how you mean "
                           "to operate (\"work out 4 times a week\", \"cook at home 5 nights a week\").", "the Operating Journal")
    for line in lines:
        sheet.add(CALCULATION, line, "the Operating Journal")
    _look(context, sheet, "get_loop", "the Loop (your routine)")


def _projects(context, sheet, prompt, today):
    """Cross-domain (step 8; G7, G11): the projects, their open tasks, what builds cost, what the business makes."""
    _look(context, sheet, "list_projects", "Projects")
    _look(context, sheet, "list_tasks", "Projects")
    _look(context, sheet, "get_build_costs", "the Workshop")
    _look(context, sheet, "get_ledger_summary", "the business")
    _look(context, sheet, "show_my_why", "your goals")


def _habits(context, sheet, prompt, today):
    """Cross-domain (step 8; D12, D13): how they mean to operate against the records, and the rhythms the Loop
    has learned."""
    _operating(context, sheet, prompt, today)
    _look(context, sheet, "get_workout_summary", "Workout")
    _look(context, sheet, "get_life_events", "your history", period="month")


def _priorities(context, sheet, prompt, today):
    """Cross-domain (step 8; G10, G12, G15): money, freedom, projects, how they mean to operate, and the year."""
    from core import seasons

    _money_month(context, sheet, prompt, today)
    _look(context, sheet, "get_freedom_progress", "Freedom")
    _look(context, sheet, "list_projects", "Projects")
    _operating(context, sheet, prompt, today)
    _label, lines = seasons.season(context, "year", today)
    for line in lines[:4]:
        sheet.add(MISSING if line.startswith("Nothing recorded") else CALCULATION, line, "your year so far")


def _resources(context, sheet, prompt, today):
    """Cross-domain (step 8; G9, G13, C20): what they make and sell, their equipment and land, their skills and
    stock, for ideas from their own records."""
    _look(context, sheet, "list_products", "the Workshop")
    _look(context, sheet, "get_ledger_summary", "the business")
    _look(context, sheet, "list_maintenance_assets", "Maintenance (equipment)")
    _look(context, sheet, "list_properties", "Real Estate (land)")
    _look(context, sheet, "list_goods_on_hand", "the Homestead")
    _progress(context, sheet, prompt, today)
    sheet.add(ESTIMATE, "Ideas from these records are starting points, not market research: what sells where they "
                        "live isn't on the sheet.", "general guidance")


_RECALL_KINDS = (
    ("commitment", re.compile(r"\b(promis\w*|commit\w*|said i'?d|owe)\b", re.IGNORECASE)),
    ("dropped_goal", re.compile(r"\b(abandon\w*|gave up|given up|giving up|set aside|dropp\w*)\b", re.IGNORECASE)),
    ("decision", re.compile(r"\b(decid\w*|decisions?|chose|chosen|went with)\b", re.IGNORECASE)),
    ("idea", re.compile(r"\b(ideas?|never (pursued|tried)|haven'?t tried|want(ed)? to try)\b", re.IGNORECASE)),
)
_RECALL_NONE = {"commitment": "No promises kept yet.", "decision": "No decisions kept yet.", "idea": "No ideas kept yet.",
                "dropped_goal": "No goals set aside kept yet."}


def _notes(context, sheet, kind, open_only=False):
    from core.life_notes import describe

    store = getattr(context, "life_notes", None)
    found = store.of_kind(kind, open_only=open_only) if store is not None else []
    for note in found[-12:]:
        done = " (done)" if note.get("status") == "done" else ""
        sheet.add(FACT, f"{describe(note)}{done}, noted {note.get('at', '')[:10]}.".replace(".,", ","),
                  "what you told MIA")
    return found


def _recall(context, sheet, prompt, today):
    """DEC-0054 (E3, E6, E10, E15): what they promised, decided, want to try and set aside, as kept on their yes."""
    kinds = [k for k, words in _RECALL_KINDS if words.search(prompt or "")] or [k for k, _ in _RECALL_KINDS]
    for kind in kinds:
        if not _notes(context, sheet, kind):
            sheet.add(MISSING, _RECALL_NONE[kind], "what you told MIA")
    sheet.add(ESTIMATE, "Only what they said and agreed to keep is here: when they mention one, MIA offers to keep it.",
              "how MIA remembers")
    if "decision" in kinds or "dropped_goal" in kinds:
        _look(context, sheet, "show_my_why", "your goals")


def _named_person(context, prompt: str):
    """The person in People & Pets the question names, by name or by what they are to them ("my sister")."""
    people = getattr(context, "relationships", None)
    words = set(re.findall(r"[a-z']+", (prompt or "").lower()))
    for person in people.all_people() if people is not None else []:
        if person.name and set(person.name.lower().split()) & words:
            return person
    for person in people.all_people() if people is not None else []:
        rel = (person.relationship or "").lower()
        if rel and re.search(rf"\bmy {re.escape(rel)}\b", (prompt or "").lower()):
            return person
    return None


def _person(context, sheet, prompt, today):
    """E13: what they've told MIA about someone: their People & Pets record, the memories that name them, and the
    promises, decisions and ideas that involve them."""
    from core.life_notes import describe

    person = _named_person(context, prompt)
    if person is None:
        sheet.add(MISSING, "Which person? Say their name (or what they are to you, like \"my sister\"), and they "
                           "need to be in People & Pets.", "People & Pets")
        return
    _look(context, sheet, "get_person", "People & Pets", name=person.name)
    names = {w for w in person.name.lower().split() if len(w) > 1}
    memories = getattr(context, "user_memories", None)
    told = [m for m in (memories.all_memories() if memories is not None else [])
            if names & set(re.findall(r"[a-z']+", m.text.lower()))]
    for m in told[-10:]:
        sheet.add(FACT, f"You told MIA: {m.text}", "Memories")
    notes = getattr(context, "life_notes", None)
    for note in (notes.notes if notes is not None else []):
        if names & set(re.findall(r"[a-z']+", f"{note.get('who', '')} {note.get('what', '')}".lower())):
            sheet.add(FACT, describe(note) + (" (done)" if note.get("status") == "done" else ""), "what you told MIA")
    if not told:
        sheet.add(MISSING, f"No memories about {person.name} yet.", "Memories")


def _patterns(context, sheet, prompt, today):
    """E4, E8: what they keep running into, as they told MIA, and the patterns her code found in their records."""
    memories = getattr(context, "user_memories", None)
    found = [m for m in (memories.all_memories() if memories is not None else [])
             if m.category == "Struggles & Patterns"]
    for m in found[-10:]:
        sheet.add(FACT, f"You told MIA: {m.text}", "Memories (struggles and patterns)")
    insights = getattr(context, "insights", None)
    seen = [i for i in (insights.all_insights() if insights is not None else []) if i.source_type == "patterns"]
    for i in seen[-8:]:
        sheet.add(CALCULATION, f"{i.title}: {i.message}" + (" (no longer true)" if i.status != "open" else ""),
                  "patterns in your records")
    notes = getattr(context, "life_notes", None)
    for note in (notes.of_kind("dropped_goal") if notes is not None else []):
        from core.life_notes import describe

        sheet.add(FACT, describe(note), "what you told MIA")
    if not found and not seen:
        sheet.add(MISSING, "Nothing yet: no struggles they've told MIA about, and no pattern in the records so far.",
                  "Memories")
    _look(context, sheet, "get_journal_themes", "the journal")


def _open_loops(context, sheet, prompt, today):
    _notes(context, sheet, "commitment", open_only=True)
    _look(context, sheet, "list_tasks", "Projects")
    _look(context, sheet, "list_projects", "Projects")
    _look(context, sheet, "list_missions", "Missions")


_AMOUNT = re.compile(r"\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)|\b([0-9][0-9,]*(?:\.[0-9]+)?)\s?(?:dollars|bucks)\b", re.IGNORECASE)


def _amount_in(prompt: str) -> Optional[float]:
    """Pure logic. The money amount a question names ("$1,000", "200 dollars")."""
    m = _AMOUNT.search(prompt or "")
    if not m:
        return None
    try:
        return float((m.group(1) or m.group(2)).replace(",", ""))
    except ValueError:
        return None


_FILLER = {"how", "much", "does", "it", "cost", "me", "to", "make", "a", "an", "the", "my", "what", "is", "actual",
           "produce", "should", "i", "charge", "for", "custom", "of", "price", "do"}


def _subject(prompt: str) -> str:
    """Pure logic. What a cost question is about ("a raised garden bed")."""
    words = [w for w in re.findall(r"[a-z]+", (prompt or "").lower()) if w not in _FILLER]
    return " ".join(words[:4])


# ---------------------------------------------------------------- the plans

PLANS: tuple[Plan, ...] = (
    Plan("today", "What matters today",
         ("What are my priorities today?", "What deadlines are approaching?", "Is there anything important I've forgotten?",
          "What tasks should I prioritize based on their importance and urgency?",
          "What could I accomplish today that would make the biggest difference in my long-term goals?",
          "What would be a worthwhile mission today?", "What should I focus on right now?",
          "What's on my plate today?", "What do I need to do today?", "What's most important today?"),
         r"\b(today|right now|priorit|focus on|deadlines?)\b", _today),
    Plan("week review", "How the week went",
         ("What did I accomplish this week?", "What has changed in my life since last week?",
          "What accomplishments have I earned recently?", "How did my week go?", "What did I get done this week?"),
         r"\b(this week|last week|my week|accomplish)", _week_review),
    Plan("money month", "Money this month",
         ("How much money came in and went out this month?", "Where is most of my money going?",
          "How much am I spending on unnecessary things?", "How much money am I saving each month?",
          "What are my largest recurring expenses?", "What did I spend this month?", "How much have I spent so far?",
          "What's my spending look like this month?"),
         r"\b(spend|spent|spending|came in|went out|expenses?|money going|saving)\b", _money_month),
    Plan("debts", "Debts and paying them off",
         ("Which debt should I prioritize?", "What happens if I put an extra $200 toward that debt every month?",
          "How much interest am I paying across all my debts?",
          "When will each of my debts be paid off at my current payment rate?",
          "What would happen if I increased my monthly debt payments?", "When will I be debt free?",
          "Which card should I pay off first?"),
         r"\b(debts?|loans?|pay (it )?off|payoff|interest|credit cards?|debt.free)\b", _debts),
    Plan("freedom", "Leaving the job",
         ("How much more income do I need to replace my job?", "How close am I to financial independence?",
          "What would my financial situation look like in one, three, and five years?",
          "What financial decisions would bring me closer to leaving my current job?",
          "How much revenue would I need to replace my factory income?", "How can I get out of my current job faster?",
          "How do my current financial decisions affect my long-term goals?",
          "What is preventing me from reaching financial independence?", "When can I quit my job?"),
         r"\b(quit|leave|leaving|replace) (my |the )?(job|work)|financial(ly)? (independen|free)|freedom fund", _freedom),
    Plan("next dollar", "Where the next dollar goes",
         ("What is the most effective use of my next $1,000?", "How much emergency savings should I maintain?",
          "I got a bonus, what should I do with it?", "Where should extra money go?"),
         r"\b(next \$|extra money|bonus|emergency (fund|savings))\b", _next_dollar),
    Plan("rentals", "The rentals",
         ("How much passive income are my properties generating?", "Is my rental business actually profitable?",
          "Are my rentals making money?", "How are my rental properties doing?"),
         r"\b(rentals?|propert(y|ies)|tenants?|passive income)\b", _rentals),
    Plan("products", "What sells and what it makes",
         ("Which of my products makes the most profit?", "Which products have the best profit margins?",
          "What is my current inventory worth?", "How many products do I need to sell to cover my monthly expenses?",
          "Which products take the least time to produce relative to their profit?", "What sells best?"),
         r"\b(products?|margins?|sells? best|inventory worth)\b", _products),
    Plan("product cost", "What one thing costs to make",
         ("What is my actual cost to produce a raised garden bed?", "How much should I charge for a custom engraved planter?",
          "How much does it cost me to make a bench?", "What should I price this at?"),
         r"\b(cost (me )?to (make|produce)|should i charge|price (it|this) at)\b", _product_cost),
    Plan("business month", "The business this month",
         ("How much money did the business make this month?", "Which business expenses could potentially qualify as tax deductions?",
          "How much should I pay myself from the business?", "How much money can I safely reinvest into my business?",
          "Is my business actually growing?", "How's the business doing?"),
         r"\b(the business|my business|business (make|made|doing|growing)|deduct)", _business_month),
    Plan("market prep", "Getting ready for market",
         ("What materials should I purchase before the next market?", "What do I need for the market?",
          "Am I ready for market day?"),
         r"\bmarket\b", _market_prep),
    Plan("progress", "Goals and progress",
         ("What am I currently working toward?", "What skills have I been developing?", "What have I improved at over the past month?",
          "What is the next milestone in my current questline?", "Am I making progress toward the person I want to become?",
          "What should I work on next?", "Which of my skills would be most beneficial to develop next?",
          "What do you know about my current priorities?", "How am I doing on my goals?"),
         r"\b(working toward|my goals?|questline|milestone|skills?|progress)\b", _progress),
    Plan("coming up", "What's coming up",
         ("What upcoming responsibilities should I prepare for?", "What risks should I be preparing for over the next six months?",
          "What's coming up in the next few weeks?", "What's coming up this month?", "What should I get ready for?"),
         r"\b(coming up|upcoming|next (few )?(weeks|month)|prepare for)\b", _coming_up),
    Plan("tonight", "Before bed",
         ("What should I take care of before going to bed?", "Anything I need to do tonight?", "What's tomorrow look like?"),
         r"\b(tonight|before bed|tomorrow)\b", _tonight),
    Plan("noticed", "What MIA has noticed",
         ("What have you noticed about me lately?", "Is there anything I should know?", "Anything I'm missing?",
          "What have I been neglecting?", "What have I let slide?",
          "What patterns have you noticed?", "Anything I should be worried about?", "What stands out to you?"),
         r"\b(noticed|should i know|anything i'm missing|stands? out|worried about)\b", _noticed),
    # Cross-domain plans (build plan step 8): several apps on one sheet, the arithmetic by code
    Plan("afford", "Whether you can afford it",
         ("Can I afford a $3,000 truck and still hit my freedom date?", "Can I afford this?",
          "If I buy a $1,200 trailer, how much does it push back my freedom date?",
          "Can I afford $150 a month for a gym?", "Will buying this set me back?"),
         r"\b(afford|push(es)? (back|out)|set me back)\b", _afford),
    Plan("slipped", "What slipped this week",
         ("What slipped this week and why?", "What fell behind this week?", "What did I let slip?",
          "Why didn't I get everything done this week?", "What am I behind on?"),
         r"\b(slip(ped)?|fell behind|fall(ing)? behind|behind on)\b", _slipped),
    Plan("seasons", "How this stretch of your life compares",
         ("What changed this month?", "What's different this year?", "How was my year?", "How did last month go?",
          "How does this month compare to last month?", "What changed in my life this year?",
          "Was this a better month than last?"),
         r"\b(chang\w*|different|compar\w*|how (was|did)|better|worse)\b.*\b(month|year)\b|\bmy year\b", _seasons),
    Plan("operating", "How you're operating",
         ("Am I living how I said I want to?", "How am I doing against my operating journal?",
          "Am I keeping my rules?", "How does my week compare to how I want to operate?",
          "Am I operating the way I want to?", "What's my operating journal say?"),
         r"\boperating\b|\bmy rules\b|\bhow i (said i )?want to (live|operate)\b", _operating),
    Plan("projects", "Your projects",
         ("Which of my current projects deserves the most attention?", "Which of my projects could support another "
          "project financially?", "How are my projects going?", "What should I build next?",
          "Which project should I work on?"),
         r"\bprojects?\b", _projects),
    Plan("habits", "Your habits",
         ("What habits are helping me progress?", "What habits are interfering with my goals?", "What are my habits?",
          "What routines am I keeping?", "Which habits should I change?"),
         r"\bhabits?\b|\broutines?\b", _habits),
    Plan("priorities", "Where your time and money go",
         ("How should I distribute my available time and money between my competing priorities?",
          "What should I stop doing so I can make more progress?",
          "If you were helping me plan the next year of my life, what would you recommend?",
          "What should I prioritize this year?", "Where should my time and money go?"),
         r"\b(time and money|competing priorities|stop doing|next year|this year'?s plan)\b", _priorities),
    Plan("resources", "What you have to work with",
         ("How can I use my available resources to generate more income?",
          "What opportunities exist that connect my current skills, equipment, land, and business goals?",
          "What business opportunities am I overlooking?", "How can I make more money with what I have?"),
         r"\b(resources|opportunit\w+|make more money|more income)\b", _resources),
    Plan("recall", "What you said you'd do, decided, want to try and set aside",
         ("What did I promise someone?", "What commitments have I made?", "What did I say I'd do?",
          "What decisions have I made about this project?", "What did we decide?", "What did I decide about the roof?",
          "What ideas have I mentioned but never pursued?", "What ideas haven't I tried?",
          "What goals have I abandoned, and why?", "What goals have I set aside?", "What have I given up on?",
          "What were the reasons behind my last major decision?", "Why did I decide that?"),
         r"\b(promis\w*|commitments?|decid\w*|decisions?|ideas?|abandon\w*|gave up|given up|set aside)\b", _recall),
    Plan("person", "What you've told MIA about someone",
         ("What important information have I told you about this person?", "What do you know about my sister?",
          "What have I told you about my dad?", "Tell me what you remember about my friend.",
          "What do I know about my neighbor?"),
         r"\b(told you about|know about|remember about)\b", _person),
    Plan("patterns", "What you keep running into",
         ("What have I repeatedly struggled with?", "What patterns have you noticed in my behavior?",
          "What do I keep running into?", "What do I keep struggling with?", "What patterns do you see in me?"),
         r"\b(struggl\w*|patterns?|keep running into)\b", _patterns),
    Plan("open loops", "What's unfinished",
         ("What commitments have I made that I haven't completed?", "What projects have I started but not completed?",
          "What have I left unfinished?", "What's still open?"),
         r"\b(unfinished|not (yet )?(completed|finished|done)|still open|started but)\b", _open_loops),
)
# Questions no plan answers (DEC-0052): the benchmark's memory, research,
# findings and open-ended ones, and small talk. When one of these is the
# nearest example, no plan runs and the normal turn does.
NOT_A_PLAN = (
    'What am I spending too much time on?',
    'Which of my assets are generating the best returns?',
    'What permits or registrations do I need to verify?',
    'Which investment would generate the fastest return?',
    'What should I build next to increase revenue?',
    'How much does it cost to operate my workshop?',
    'Which materials should I buy in bulk?',
    'What equipment investment would improve production efficiency the most?',
    'Is it more profitable to make products to order or maintain inventory?',
    'What business opportunities am I overlooking?',
    'What is holding me back?',
    'How can I turn this frustrating situation into a challenge?',
    'What habits are helping me progress?',
    'What habits are interfering with my goals?',
    'How can I break this large objective into smaller missions?',
    'What would an ideal week of progression look like?',
    'What did we discuss about this project last time?',
    'Why did I originally decide to pursue this?',
    'Have I mentioned this problem before?',
    'What changed between my original plan and where I am now?',
    'What lessons have I learned from previous experiences?',
    'How does this piece of equipment work?',
    "What's the best way to repair this?",
    'What materials would I need for this project?',
    'Can you compare these three products?',
    'Is this information still accurate?',
    'What are the legal requirements for this business activity in my state?',
    'Can you find a more efficient way to accomplish this?',
    'Can you teach me how to do this?',
    'Can you help me troubleshoot this problem step by step?',
    'What are the advantages and disadvantages of these approaches?',
    'What tools would make this project easier?',
    'What am I overlooking in this plan?',
    'What is the most cost-effective way to accomplish this?',
    'Can you develop a complete project plan and bill of materials?',
    'What could go wrong, and how can I prevent it?',
    'Can you figure out the best way to accomplish this?',
    'Which of my current projects deserves the most attention?',
    'How can I use my available resources to generate more income?',
    'What should I stop doing so I can make more progress?',
    'Which of my projects could support another project financially?',
    'How should I distribute my available time and money between my competing priorities?',
    'What opportunities exist that connect my current skills, equipment, land, and business goals?',
    'If you were helping me plan the next year of my life, what would you recommend?',
    "How are you?", "Thanks!", "Tell me a joke.", "Good morning", "What do you think about that?",
    "What's the weather tomorrow?", "Who won the game last night?", "What's your name?", "I'm tired today.",
    "I had a rough day at work.", "That's cool.", "Okay, sounds good.",
)
# A message starting like this asks MIA to change something: never a plan.
CHANGE_VERBS = frozenset((
    "add", "set", "delete", "remove", "log", "mark", "record", "remind", "create", "start", "make", "put", "schedule",
    "cancel", "change", "update", "move", "open", "play", "turn", "undo", "send", "draft", "rename", "clear", "stop",
    "finish", "complete", "save", "track", "note", "write", "buy", "sell", "file", "tag", "link", "unlink",
))
PLAN_BY_NAME = {p.name: p for p in PLANS}
CROSS_DOMAIN = ("afford", "slipped", "projects", "habits", "priorities", "resources")  # build plan step 8: plans over several apps


# ---------------------------------------------------------------- choosing a plan


def match(context, prompt: str) -> Optional[Plan]:
    found = match_scored(context, prompt)
    return found[0] if found else None


def match_scored(context, prompt: str) -> Optional[tuple[Plan, Optional[float]]]:
    """The plan a question asks for, or None (then the normal turn runs).
    Never a how-to or teach-me question (those go to the help docs), never
    a request to change something. Spoken questions have no "?", so by
    meaning anything that isn't a change can match (small talk's nearest
    example is in NOT_A_PLAN); by words only (no embedding model) it must
    look like a question."""
    from core.assistant_actions import looks_like_question
    from core.assistant_chat import looks_like_how_to_question, looks_like_teaching_request

    said = (prompt or "").strip()
    first = re.sub(r"^(please|hey mia|mia|ok|okay)[, ]+", "", said.lower()).split(" ", 1)[0].strip(",.!?")
    if not said or first in CHANGE_VERBS:
        return None
    how_to = looks_like_how_to_question(said) or looks_like_teaching_request(said)
    from core.meaning import nearest

    found = nearest(context, said, [(p.name, e) for p in PLANS for e in p.examples] + [("-", e) for e in NOT_A_PLAN])
    if found is not None:
        name, score = found
        if how_to and score < EXAMPLE_AT:  # "how do I add a bill?" is the help docs'; "how can I quit faster?" is a plan's
            return None
        return (PLAN_BY_NAME[name], score) if name in PLAN_BY_NAME and score >= MATCH_AT else None
    if how_to:
        return None
    # No embedding model here (the phone): the plan's own words, when exactly one plan's match.
    if not looks_like_question(said):
        return None
    lowered = said.lower()
    hits = [p for p in PLANS if re.search(p.words, lowered)]
    across = [p for p in hits if p.name in CROSS_DOMAIN]  # the more specific: it gathers the others' facts too
    if len(across) == 1:
        return across[0], None
    return (hits[0], None) if len(hits) == 1 else None


_JOINED = re.compile(r"\b(and|still|while|if|but|also|plus)\b")
COMPOSE_MAX = 2  # other plans one question can bring onto the sheet


def composed_with(plan: Plan, prompt: str) -> list[Plan]:
    """Pure logic. A question that joins domains ("can I pay down the card and still save for the truck?"):
    the other plans whose own words it uses, to gather onto the same sheet (build plan step 8)."""
    lowered = (prompt or "").lower()
    if not _JOINED.search(lowered):
        return []
    return [p for p in PLANS if p is not plan and re.search(p.words, lowered)][:COMPOSE_MAX]


def gather(context, plan: Plan, prompt: str, today: Optional[date] = None, also: tuple = ()) -> Sheet:
    sheet = Sheet(plan.name, plan.title)
    for each in (plan, *also):
        try:
            each.gather(context, sheet, prompt, today or date.today())
        except Exception:
            log.exception("Question plan %s failed while gathering", each.name)
    if also:
        sheet.title = " and ".join([plan.title, *(p.title for p in also)])
        sheet.composed = [p.name for p in also]
    return sheet


SURE, LIKELY, UNSURE = "sure", "likely", "unsure"


def sureness(sheet: Sheet) -> tuple[str, str]:
    """Pure logic. How sure an answer from this sheet can be, and why: from what the sheet holds, never a guess."""
    known = [f for f in sheet.facts if f.kind in (FACT, CALCULATION)]
    estimates = [f for f in sheet.facts if f.kind == ESTIMATE]
    missing = [f for f in sheet.facts if f.kind == MISSING]
    if not known or len(missing) >= max(1, len(known)):
        return UNSURE, f"{len(missing)} thing{'s' if len(missing) != 1 else ''} it needs {'are' if len(missing) != 1 else 'is'} not recorded"
    if missing or estimates:
        parts = ([f"{len(estimates)} estimate{'s' if len(estimates) != 1 else ''}"] if estimates else []) + \
                ([f"{len(missing)} missing"] if missing else [])
        return LIKELY, " and ".join(parts)
    return SURE, "everything on it is recorded or worked out from records"


# ---------------------------------------------------------------- the answer

ANSWER_PROTOCOL = (
    "Answer the person's question from the fact sheet below, as yourself, in a few short sentences or a short list. "
    "Answer the actual question first. Use only what the sheet says: never add a number, date or name it doesn't "
    "have, and do any comparing from the sheet's own numbers. Say which things are estimates or calculations when it "
    "matters. If something needed is marked missing, say what's missing and how they could add it. Point out the one "
    "thing that matters most rather than listing everything. End with one next step only if it follows from the "
    "sheet; never suggest an app, feature or task the sheet doesn't mention. Each line names the app it came from: "
    "the Dungeon is their paid job, not a game or a workout. "
    "Talk like a person, not a report, in plain text: no headings, bold or symbols. Never give legal or tax "
    "rulings; say to check with a professional. The sheet ends with how sure you can be: when it's likely or "
    "unsure, say so in a few plain words (\"if the pace holds\", \"I don't have your X recorded\"); when it's "
    "sure, just answer."
)
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[str]:
    """Pure logic. Every number in `text`, without commas or trailing zeros ("1,200.00" -> "1200")."""
    out = set()
    for raw in _NUMBER.findall(text or ""):
        n = raw.replace(",", "")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        out.add(n)
    return out


def invented_numbers(answer: str, sheet_text: str, prompt: str) -> set[str]:
    """Pure logic. Numbers in the answer that are in neither the sheet
    nor the question. Small counts (up to 12) are allowed: the model may
    count the sheet's own lines ("3 bills")."""
    allowed = numbers_in(sheet_text) | numbers_in(prompt)
    return {n for n in numbers_in(answer) if n not in allowed and not (n.isdigit() and int(n) <= 12)}


def _personal(conversation) -> bool:
    from core.conversation_modes import PERSONAL_MODES

    return getattr(conversation, "mode", None) in PERSONAL_MODES or bool(getattr(conversation, "journal", False))


def request(context, conversation, prompt: str, today: Optional[date] = None) -> Optional[tuple[list, Sheet]]:
    """The model request for a question a plan answers: (messages, the
    sheet), or None (then the normal turn runs). Never in a personal
    mode or the journal: those stay a conversation."""
    if conversation is not None and _personal(conversation):
        return None
    from core import conversation_state

    # A short follow-up to the last plan ("why?", "what if I paid $300?", "what about last month?"):
    # the same plan, gathered with both questions (DEC-0052 step 4, core/conversation_state.py).
    # Unless it names another plan in that plan's own words ("and what about tonight?"): meaning
    # alone can't tell (measured: "tonight" 0.741 to its plan, "last month" 0.748 to the wrong one).
    before = conversation_state.follow_up(conversation, prompt)
    found = match_scored(context, prompt)
    switch = found is not None and bool(re.search(found[0].words, prompt.lower()))
    if before is not None and before.plan in PLAN_BY_NAME and not (switch and found[0].name != before.plan):
        plan, asked = PLAN_BY_NAME[before.plan], f"{before.question} {prompt}"
    else:
        if found is None:
            return None
        plan, asked = found[0], prompt
        conversation_state.remember_plan(conversation, plan.name, prompt)
    sheet = gather(context, plan, asked, today, tuple(composed_with(plan, prompt)))
    if not sheet.facts:
        return None
    sure, why = sureness(sheet)
    from core.assistant_chat import trim_history
    from core.personality import CHARACTER, IDENTITY

    system = (f"{IDENTITY}{CHARACTER}\n\n{ANSWER_PROTOCOL}\n\nFact sheet ({sheet.title}, today "
              f"{(today or date.today()).isoformat()}):\n{sheet.as_text()}\n\nHow sure you can be: {sure} ({why}).")
    messages = [{"role": "system", "content": system}]
    history = trim_history(conversation.messages) if conversation is not None else []
    # The question was just added to the conversation by the caller; the history before it.
    if history and history[-1].role == "user" and history[-1].content == prompt:
        history = history[:-1]
    shown = history[-4:]
    if conversation is not None:  # what's older than the messages shown (core/conversation_state.py)
        before = list(conversation.messages)
        if before and before[-1].role == "user" and before[-1].content == prompt:
            before = before[:-1]
        earlier = conversation_state.earlier_topics(before, len(shown))
        if earlier:
            messages[0]["content"] += "\n\n" + earlier
    messages.extend({"role": m.role, "content": m.content} for m in shown)
    messages.append({"role": "user", "content": prompt})
    log.info("Question plan %s: %d facts from %s", plan.name, len(sheet.facts), ", ".join(sheet.looked_up))
    return messages, sheet


def finish(content: str, sheet: Sheet, prompt: str, context=None) -> str:
    """The model's answer when it keeps to the sheet's numbers; else the
    sheet in plain words (never a number MIA didn't look up), noted for the
    answers.numbers loop."""
    from core.plain_words import strip_markdown

    said = strip_markdown(content or "")
    if not said:
        return sheet.plain()
    wrong = invented_numbers(said, sheet.as_text(), prompt)
    if wrong:
        log.warning("Question plan %s: the answer had numbers not on the sheet (%s); using the sheet.",
                    sheet.plan, ", ".join(sorted(wrong)))
        failures = getattr(context, "failures", None)
        if failures is not None:
            try:
                failures.record("invented_number", tool=f"plan:{sheet.plan}")
            except Exception:  # the note never breaks the answer
                log.exception("Couldn't note the invented number.")
        said = sheet.plain()
    from core import calibration

    calibration.note(context, sheet.plan, sureness(sheet)[0], said)
    return said


def answer(context, conversation, prompt: str, today: Optional[date] = None) -> Optional[tuple[str, Sheet]]:
    """A whole plan turn, for callers that can wait on the model (the web,
    the phone, voice): (the answer, the sheet), or None when no plan fits."""
    built = request(context, conversation, prompt, today)
    if built is None:
        return None
    messages, sheet = built
    llm = getattr(context, "llm", None)
    if llm is None:
        return sheet.plain(), sheet
    reply = llm.chat_with_tools(messages, [])
    return finish(reply.content if reply is not None else "", sheet, prompt, context), sheet
