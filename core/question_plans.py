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
answer that states a number the sheet doesn't hold (`invented_numbers`; for a reference, strictly, a number it
spells out counting as said: `spelled_numbers`) is replaced by the
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

A question that joins domains gathers several plans onto one sheet
(`composed_with`). A purchase asked against the debts ("can I buy a $900
welder and still pay off the loan?", `buying`) is worked out as what the
same money would do on the debt instead (`instead`, brainstorm 1.4),
never as that much more a month. A project he's planning ("I'm planning to
build a greenhouse") gathers everything it touches (the plan "project
picture", core/project_ripple.py), using the month's money (`money_now`)
and the freedom date with a cost (`freedom_with`), both shared with the
money and afford plans. "What should I do this weekend?" gathers each
weekend day's forecast with what's due, the garden, learning and projects
(the plan "weekend", `weekend_days`; a wet day named for indoor work, `is_wet`); "am I ready for winter?" gathers
the first frost, firewood, preparedness, the kit, the flock, the garden and
the canning shelf (the plan "winter"); "how's the homestead?" gathers the
greenhouse, flock, garden, orchard, water, power and tonight's weather (the
plan "homestead"). A tool's quoted example holding a
number ("I burn 4 cords a winter") is left off a sheet (`without_examples`):
the model read examples as his records.
A thank-you is never a plan's (THANKS), and a source label the model starts an answer with comes off
(`without_source_label`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Optional

from core.logger import get_logger
from core.project_ripple import PROJECT_WORDS

log = get_logger(__name__)

# A project named as the thing itself: only articles, a few sizes and adjectives before it ("a big garden", "a 10 by
# 12 shed"), never "seeds in the garden" or "more hens to my flock"
_PROJECT_THING = (r"(?:\s+(?:a|an|the|some|my|our|new|big|small|another|second|\d+\s*(?:by|x)\s*\d+(?:\s*ft)?))*"
                  rf"\s+(?:{PROJECT_WORDS})(?![a-z])")

FACT, CALCULATION, ESTIMATE, MISSING = "fact", "calculation", "estimate", "missing"
MATCH_AT = 0.66  # cosine similarity to the nearest example (measured: small talk stayed below)
EXAMPLE_AT = 0.92  # this close to a plan's own example, a "how can I...?" question is that plan's, not a how-to


@dataclass
class Fact:
    """One line on a sheet: its kind (fact from the records, calculation, estimate, or missing), the text, and where it
    came from.
    """
    kind: str  # FACT | CALCULATION | ESTIMATE | MISSING
    text: str
    source: str = ""  # the app or lookup it came from


@dataclass
class Sheet:
    """What a plan gathered for one question: its lines (each once, even with two plans on one sheet), the tools it ran,
    and the other plans composed onto it. The model writes its answer from this; without a model it's said plainly.
    """
    plan: str
    title: str
    facts: list = field(default_factory=list)
    looked_up: list = field(default_factory=list)  # tool names run
    composed: list = field(default_factory=list)  # other plans gathered onto it (step 8)

    def add(self, kind: str, text: str, source: str = "") -> None:
        """Adds a line (whitespace tidied) unless the sheet already has the same text."""
        text = " ".join(str(text or "").split())
        if text and not any(f.text == text for f in self.facts):  # two plans on one sheet: each fact once
            self.facts.append(Fact(kind, text, source))

    def as_text(self) -> str:
        """The sheet for the model: one line each, marked."""
        return "\n".join(f"- [{f.kind}{', ' + f.source if f.source else ''}] {f.text}" for f in self.facts)

    def plain(self) -> str:
        """The sheet in plain words, for when there's no model (or its
        answer failed the number check, or the sheet holds only what's
        missing: then the missing lines, so they know what to add)."""
        found = [f.text for f in self.facts if f.kind != MISSING]
        missing = [f.text for f in self.facts if f.kind == MISSING]
        if not found:  # only what's missing: say it, so they know what to add
            return ("I don't have what that needs recorded yet. " + " ".join(missing)) if missing else \
                "I don't have anything recorded for that yet."
        out = " ".join(found)
        if missing:
            out += " Not recorded yet: " + " ".join(missing)
        return out


@dataclass
class Plan:
    """One question plan: its name and title, the example questions it answers (matched by meaning), its own words (a
    regex, used when there's no embedding model) and the gatherer that fills a sheet.
    """
    name: str
    title: str
    examples: tuple  # questions it answers (Zac's benchmark, plus phrasings)
    words: str  # a regex: the plan's own words, used when there's no embedding model
    gather: Callable  # (context, sheet, prompt, today) -> None


# ---------------------------------------------------------------- lookups

_NOTHING = re.compile(r"^(you don't have|you have no|no |nothing|there (are|is) no|i don't have|none)", re.IGNORECASE)


# A quoted example of what to say or log that holds a number ('tell me yours ("I burn 4 cords a winter")'): on a
# sheet the model read it as his record, so it's left off the sheet (the tool's own reply keeps it).
_QUOTED = re.compile(r'"[^"]*"')  # quotes in pairs, in order
_LEAD_IN = re.compile(r"\s*(?:\(\s*)?(?:like|e\.g\.,?|say|such as)?\s*\(?\s*$")


def without_examples(text: str) -> str:
    """Pure logic. A tool's reply without its quoted examples that hold a number, only those led into by "like",
    "e.g.", "say", "such as" or a bracket, so a model never reports an example ("I burn 4 cords a winter") as the
    person's record; a quoted name or price ("Sign 2", "$45") stays, and no comma is left before a bracket or stop."""
    out, last = [], 0
    for quoted in _QUOTED.finditer(text or ""):
        if not re.search(r"\d", quoted.group()):
            continue
        before = text[last:quoted.start()]
        if not re.search(r"(?:\(|\b(?:like|e\.g\.,?|say|such as))\s*$", before):
            continue  # a name or a price in quotes ("Sign 2", "$45"): kept
        opened = before.rstrip().endswith("(") or bool(re.search(r"\(\s*(?:like|e\.g\.,?|say|such as)?\s*$", before))
        out.append(_LEAD_IN.sub("", before))
        last = quoted.end()
        if opened and text[last:last + 1] == ")":
            last += 1
    out.append((text or "")[last:])
    said = "".join(out)
    said = re.sub(r",\s*([.;:)])", r"\1", said)
    return re.sub(r"\s+([,.;:])", r"\1", said).strip()


def _look(context, sheet: Sheet, tool: str, source: str, said_as: str = "", **arguments) -> str:
    """Run one of MIA's own lookups and put what it says on the sheet (a fact after `said_as`, when given: whose
    it is), its quoted examples with numbers left off (`without_examples`); a lookup that failed (its apology: it's
    logged) puts nothing on the sheet. Returns the tool's whole reply."""
    registry = getattr(context, "assistant_actions", None)
    if registry is None or tool not in getattr(registry, "_actions", {}):
        return ""
    try:
        text = registry.execute(context, tool, arguments)
    except Exception:
        log.exception("Question plan lookup %s failed", tool)
        return ""
    sheet.looked_up.append(tool)
    if text.strip().startswith("Something on my side broke"):  # the tool failed (it's logged): not a fact
        return ""
    found = not _NOTHING.match(text.strip())
    kept = without_examples(text)
    sheet.add(FACT if found else MISSING, said_as + kept if found else kept, source)
    return text


def _money(context, amount: float) -> str:
    """An amount in the person's currency."""
    from core.region import money

    return money(amount)


def _month_bounds(day: date) -> tuple[date, date]:
    """The first and last day of a date's month."""
    first = day.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return first, last


# ---------------------------------------------------------------- the plans' gathering


def _today(context, sheet, prompt, today):
    """Plan gatherer (what matters today): today's picture, compliance deadlines, the calendar and their goals."""
    _look(context, sheet, "get_today", "Today")
    _look(context, sheet, "get_deadlines", "Compliance")
    _look(context, sheet, "list_calendar_events", "Calendar")
    _look(context, sheet, "show_my_why", "your goals")


def _play(context, sheet):
    """Adds the recreation lines (play this week against before, core/recreation.py) as calculations."""
    from core import recreation

    for line in recreation.lines(context):
        sheet.add(CALCULATION, line, "Recreation")


def _week_review(context, sheet, prompt, today):
    """Plan gatherer (how the week went): the weekly check-in, play, the week's history, workouts and the job's
    loot.
    """
    _look(context, sheet, "get_weekly_checkin", "the weekly check-in")
    _play(context, sheet)
    _look(context, sheet, "get_life_events", "your history", period="week")
    _look(context, sheet, "get_workout_summary", "Workout")
    _look(context, sheet, "get_dungeon_loot", "the Dungeon (their job)")


def _time(context, sheet, prompt, today):
    """A11: where their recorded time goes: work hours, workouts, games and sports, a week of the calendar, and how
    they said they mean to spend it."""
    from core.calendar_view import calendar_items

    _look(context, sheet, "get_dungeon_loot", "the Dungeon (their job)")
    _look(context, sheet, "get_workout_summary", "Workout")
    _play(context, sheet)
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    try:
        items = calendar_items(context, monday, monday + timedelta(days=6), today)
    except Exception:
        items = []
    if items:
        kinds = {}
        for i in items:
            kinds[i.get("kind", "event")] = kinds.get(i.get("kind", "event"), 0) + 1
        sheet.add(CALCULATION, f"This week's calendar has {len(items)} things: "
                  + ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))
                  + ".", "Calendar")
    _operating(context, sheet, prompt, today)
    sheet.add(ESTIMATE, "Only recorded time is here: screens, sleep, chores and driving aren't tracked, so \"too much\" "
                        "is against what they said they want, not a measure of everything.", "how this was worked out")


def money_now(context, sheet, today: Optional[date] = None) -> bool:
    """This month so far and last month, in, out and net, on the sheet; False (said as missing) with no budget."""
    budget = getattr(context, "budget", None)
    if budget is None:
        sheet.add(MISSING, "No budget is set up.", "Money")
        return False
    today = today or date.today()
    first, _last = _month_bounds(today)
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
    return True


def _money_month(context, sheet, prompt, today):
    """Plan gatherer (money this month): in, out and net so far this month and last month (`money_now`), the five biggest
    spending categories, how much came from the bank sync against by hand, the bills, and untagged charges.
    """
    budget = getattr(context, "budget", None)
    if not money_now(context, sheet, today):
        return
    first, _last = _month_bounds(today)
    went_out = budget.total_expenses(first.isoformat(), today.isoformat())
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
    """Plan gatherer (debts and paying them off): the debts and payoff order, then a simulation at the minimums (each payoff
    date, debt-free date, interest; the date is recorded to be checked when it comes) and with extra a month (the amount
    asked, else 200) to the first debt. Missing minimums are said. A purchase asked about ("can I buy a $900 welder and still pay off the loan?", `buying`) is never taken as extra a
    month: it's worked out as the same money put on the first debt instead (`instead`). Extra on a debt he names ("an
    extra $100 a month on the truck") goes to that debt first, and its payoff date is said both ways.
    A debt counts as named only where the extra goes ("on the truck"), never a word of its name said elsewhere; an
    extra of $0 adds nothing.
    """
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
    if buying(prompt) and _amount_in(prompt):  # "can I buy a $900 welder and still pay off the loan?" (1.4)
        for kind, line in instead(ranked, _amount_in(prompt), _monthly(prompt), now, today, lambda a: _money(context, a)):
            sheet.add(kind, line, "a payoff calculation")
        return
    asked = _amount_in(prompt)
    if asked is not None and asked <= 0:
        return  # "an extra $0": nothing more to work out
    extra = asked or 200.0
    # a debt named where the extra goes ("on the truck", "toward my Visa"), never a word of its name said elsewhere
    # ("the best way", "which one": the Fable review)
    where = " ".join(m.group(1) for m in re.finditer(r"\b(?:on|to|toward|towards|into|at)\s+(?:the|my|our)\s+"
                                                     r"([a-z][\w ]{1,30}?)(?=[,.?!]|\s+(?:first|instead|every|each|a "
                                                     r"month|per)|$)", str(prompt or "").lower()))
    said = set(re.findall(r"[a-z]{3,}", where)) - {"loan", "card", "debt", "debts", "balance", "bill"}
    named = [d for d in ranked if said & (set(re.findall(r"[a-z]{3,}", d.name.lower())) - {"loan", "card"})]
    if len(named) == 1 and named[0] is not ranked[0]:
        # "an extra $100 a month on the truck": that debt first, and when it's paid off now and with it (the live sweep)
        target = named[0]
        mine = simulate([target] + [d for d in ranked if d is not target], extra, today)
        before = next((r for r in now.debts if r.name == target.name), None)
        after = next((r for r in mine.debts if r.name == target.name), None)
        if after is not None and after.paid_off:
            sheet.add(CALCULATION, f"With {_money(context, extra)} more a month to {target.name}: it's paid off "
                                   f"{after.paid_off}" + (f" instead of {before.paid_off}" if before and before.paid_off
                                                          else "") + ".", "a payoff calculation")
            return
    more = simulate(ranked, extra, today)
    if more.months is not None and (now.months is None or more.months < now.months):
        saved = now.interest - more.interest
        sheet.add(CALCULATION, f"With {_money(context, extra)} more a month to {ranked[0].name} first: debt-free "
                               f"{more.debt_free}" + (f", {now.months - more.months} months sooner" if now.months else "")
                               + f", about {_money(context, saved)} less interest.", "a payoff calculation")


def _freedom(context, sheet, prompt, today):
    """Plan gatherer (leaving the job): Freedom's progress, the job's pay rate and recent weekly pace, the business
    ledger and the financial check-in.
    """
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
    """Plan gatherer (where the next dollar goes): the amount asked about, the debt picture, Freedom and the
    check-in, plus a rule of thumb clearly marked as an estimate, not advice.
    """
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
    """Plan gatherer (the rentals): the properties and each one's summary (the first five)."""
    estate = getattr(context, "real_estate", None)
    _look(context, sheet, "list_properties", "Real Estate")
    for p in (estate.all_properties() if estate is not None and hasattr(estate, "all_properties") else [])[:5]:
        _look(context, sheet, "get_property_summary", "Real Estate", property_name=p.name)


def _products(context, sheet, prompt, today):
    """Plan gatherer (what sells and what it makes): products, goods on hand and the business ledger."""
    _look(context, sheet, "list_products", "Workshop")
    _look(context, sheet, "list_goods_on_hand", "Workshop")
    _look(context, sheet, "get_ledger_summary", "the business")


def _returns(context, sheet, prompt, today):
    """B19: what their assets earn: each rental's income and cap rate, each product's margin, the business."""
    _rentals(context, sheet, prompt, today)
    _products(context, sheet, prompt, today)
    sheet.add(ESTIMATE, "Returns here are from what's recorded: a property's value, a product's materials and what "
                        "sold. Investments outside MIA (stocks, retirement accounts) aren't on the sheet.",
              "how this was worked out")


def _product_cost(context, sheet, prompt, today):
    """Plan gatherer (what one thing costs to make): the product, its build costs and materials, and that labour and
    overhead aren't recorded (an estimate line). The workshop's materials only for a product of his: "how do I price
    my firewood?" is never answered with the plywood on hand (the live sweep, 2026-11-25); for one he hasn't
    recorded, the way to price it (the business course's pricing lesson) is on the sheet instead.
    His product is found by its name's words, plurals in "es" too ("benches" is the Bench)."""
    subject = _subject(prompt)
    _look(context, sheet, "list_products", "Workshop", query=subject)
    _look(context, sheet, "get_build_costs", "Workshop", build=subject)
    book = getattr(context, "products", None)

    def stems(text):
        """Its words of three letters or more, a plural as its one ("benches" is bench, "boxes" box), "the" left out."""
        out = set()
        for w in re.findall(r"[a-z]{3,}", str(text).lower()):
            if w == "the":
                continue
            out.add(w[:-2] if re.search(r"(?:ch|sh|x|ss)es$", w) else w[:-1] if w.endswith("s") and len(w) > 3 else w)
        return out

    said = stems(prompt)  # the whole question: a product of his is one whose name's words are all in it
    his = [pr for pr in (book.all_products() if book is not None and hasattr(book, "all_products") else [])
           if stems(getattr(pr, "name", "")) and stems(getattr(pr, "name", "")) <= said]
    if his:
        _look(context, sheet, "list_materials", "Workshop")
    else:
        sheet.add(ESTIMATE, "How to price one: what it costs you in materials, plus your hours on it at the rate you "
                            "want, plus a share of your running costs (tools, fuel, a vehicle); then check what the same "
                            "thing sells for near you, and don't price below your costs.", "the business course")
    sheet.add(ESTIMATE, "Labour and overhead aren't recorded per product: a price needs your time per piece and "
                        "what you want an hour for it.", "Workshop")


def _business_month(context, sheet, prompt, today):
    """Plan gatherer (the business this month): the ledger, business use, and the jobs."""
    _look(context, sheet, "get_ledger_summary", "the business")
    _look(context, sheet, "get_business_use", "the business")
    _look(context, sheet, "list_jobs", "Workshop")


def _running_costs(context, sheet, prompt, today):
    """C12: what the workshop costs to run: the business's expenses and its business-use share of household bills,
    what builds use in materials, and the equipment that needs upkeep."""
    _look(context, sheet, "get_ledger_summary", "the business")
    _look(context, sheet, "get_business_use", "the business")
    _look(context, sheet, "get_build_costs", "the Workshop")
    _look(context, sheet, "list_maintenance_assets", "Maintenance (equipment)")
    sheet.add(ESTIMATE, "Running costs here are what's recorded: power, rent or tools bought outside the business's "
                        "books aren't on the sheet unless they were tagged to it.", "how this was worked out")


def _market_prep(context, sheet, prompt, today):
    """Plan gatherer (getting ready for market): goods on hand, materials and the calendar."""
    _look(context, sheet, "list_goods_on_hand", "Workshop")
    _look(context, sheet, "list_materials", "Workshop")
    _look(context, sheet, "list_calendar_events", "Calendar")


def _progress(context, sheet, prompt, today):
    """Plan gatherer (goals and progress): their goals, missions, learning and the month's history."""
    _look(context, sheet, "show_my_why", "your goals")
    _look(context, sheet, "list_missions", "Missions")
    _look(context, sheet, "get_learning_progress", "Skills")
    _look(context, sheet, "get_life_events", "your history", period="month")


def _coming_up(context, sheet, prompt, today):
    """Plan gatherer (what's coming up): deadlines, the calendar, birthdays in 30 days, upkeep and bills."""
    _look(context, sheet, "get_deadlines", "Compliance")
    _look(context, sheet, "list_calendar_events", "Calendar")
    _look(context, sheet, "list_upcoming_birthdays", "People", within_days=30)
    _look(context, sheet, "list_maintenance_tasks", "upkeep")
    _look(context, sheet, "list_bills", "Money")


def _tonight(context, sheet, prompt, today):
    """Plan gatherer (before bed): today's picture, alarms, the calendar and the Loop."""
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
    by core/freedom.plan() twice, as things stand and with the purchase (`freedom_with`), with what his confirmed
    builds still need from the store (`_planned_builds`)."""
    amount = _amount_in(prompt)
    monthly = bool(re.search(r"\b(a|per|each|every) month\b|\bmonthly\b", prompt.lower()))
    if amount:
        sheet.add(FACT, f"The amount asked about: {_money(context, amount)}{' a month' if monthly else ', once'}.",
                  "your question")
    else:
        sheet.add(MISSING, "The question doesn't say how much it costs.", "your question")
    _money_month(context, sheet, prompt, today)
    _planned_builds(context, sheet)
    freedom_with(context, sheet, amount, monthly, today)


def _planned_builds(context, sheet) -> None:
    """What his confirmed builds still need from the store (core/project_ripple.add_still_to_buy); a failure is
    logged and the sheet goes on without it."""
    try:
        from core.project_ripple import add_still_to_buy

        add_still_to_buy(context, sheet)
    except Exception:  # noqa: BLE001
        log.exception("Couldn't read what the confirmed builds still need")


def freedom_with(context, sheet, amount: Optional[float], monthly: bool, today: date, check: bool = True) -> None:
    """The freedom date as things stand and with a cost (`amount` once, or a month when `monthly`), both worked out
    by core/freedom.plan(); used by the afford plan and the project picture (core/project_ripple.py). With `check`,
    the date is filed to be checked when it comes (core/calibration.py); the project picture doesn't file one."""
    from dataclasses import replace

    from core import freedom

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

    if check:
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


_BUYING = re.compile(r"\b(?:afford|buy|buying|bought|purchase|spend|spending)\b|\bget (?:an?|the) ", re.I)
# Money that goes on a debt, not a thing bought: "an extra $200 toward the card", "throw $1,000 at the loan",
# "pay $300 more a month", "afford to pay $300 a month on my loans", "spending $400 a month on interest".
_TOWARD = re.compile(
    r"\b(?:toward|towards|extra)\b"
    r"|\b(?:pay|put|throw)\s+(?:an?\s+)?(?:\$?[\d,.]+\s+)?more\b"
    r"|\b(?:put|throw|putting|throwing)\b[^?]*\b(?:on|at|into)\b[^?]*\b(?:debts?|loans?|cards?)\b"
    r"|\b(?:afford|spend|spending)\b(?:\s+to)?\s+(?:pay(?:ing)?|put(?:ting)?|throw(?:ing)?)\b"
    r"|\b(?:spend|spending|use|using)\b[^?]{0,40}?\b(?:paying|to pay)\s+(?:down|off)\b"
    r"|\b(?:spend|spending)\b[^?]*\bon (?:my |the )?(?:interest|debts?|loans?|cards?)\b", re.I)


def buying(prompt: str) -> bool:
    """Pure logic. Whether a question's amount is something he'd buy ("can I afford a $900 welder?", "should I get
    the $900 welder?"), not money he'd put on a debt ("an extra $200 toward the card", "can I afford to throw $1,000
    at the card?", "I'm spending $400 a month on interest")."""
    said = prompt or ""
    return bool(_BUYING.search(said)) and not _TOWARD.search(said)


def _monthly(prompt: str) -> bool:
    """Pure logic. Whether an amount asked about is a month's ("$150 a month", "monthly")."""
    return bool(re.search(r"\b(a|per|each|every) month\b|\bmonthly\b", (prompt or "").lower()))


def instead(ranked: list, amount: float, monthly: bool, now, today, money) -> list[tuple[str, str]]:
    """Pure logic. What a purchase costs him in debt terms (brainstorm 1.4): the same money put on the debts in the
    payoff order instead, worked out by the payoff simulation, against `now` (the plan as things stand). Once, it's
    walked down the payoff order (a debt it clears keeps its minimum rolling on to the next, as in `now`; what's
    left over after every debt is said); a month's, it's extra each month. A purchase never changes the minimums, so
    that's said first. Returns (kind, line) pairs for the sheet."""
    from types import SimpleNamespace

    from core.debt_math import simulate

    first = ranked[0]
    covers_all = False
    if monthly:
        other = simulate(ranked, amount, today)
        what = f"{money(amount)} a month"
    else:
        copies = [SimpleNamespace(name=d.name, balance=float(d.balance or 0), interest_rate=d.interest_rate,
                                  minimum_payment=d.minimum_payment, promo_apr=getattr(d, "promo_apr", None),
                                  promo_expires_date=getattr(d, "promo_expires_date", None)) for d in ranked]
        left, freed = float(amount), 0.0
        for c in copies:
            if left <= 0.005 or c.balance <= 0.005:
                continue
            take = min(c.balance, left)
            c.balance -= take
            left -= take
            if c.balance <= 0.005:
                freed += float(c.minimum_payment or 0)  # its minimum rolls on, as it would have in `now`
        covers_all = left > 0.005 or all(c.balance <= 0.005 for c in copies)
        other = simulate(copies, freed, today)
        what = f"{money(amount)} once"
    if now.months is None:
        lines = [("calculation", "Buying it doesn't change the minimums, and at the minimums some debt is never paid "
                                 "off, so there's no payoff date to hold.")]
    else:
        lines = [("calculation", "Buying it doesn't change the minimums, so the payoff dates above hold either way, as "
                                 "long as the minimums are still paid.")]
    if covers_all:
        lines.append(("calculation", f"Put on the debts instead, {what} would pay them all off now. That's what buying "
                                     f"it costs in debt terms."))
    elif other.debt_free and (now.months is None or (other.months or 0) < now.months):
        sooner = f", {now.months - other.months} months sooner" if now.months else ""
        saved = f", with about {money(now.interest - other.interest)} less interest" if now.months else ""
        lines.append(("calculation", f"Put toward {first.name} instead, {what} would make you debt-free "
                                     f"{other.debt_free}{sooner}{saved}. That's what buying it costs in debt terms."))
    elif now.months is not None and now.interest - other.interest >= 1:
        lines.append(("calculation", f"Put toward {first.name} instead, {what} wouldn't move the debt-free date, but "
                                     f"would save about {money(now.interest - other.interest)} in interest."))
    else:
        lines.append(("calculation", f"Put toward {first.name} instead, {what} wouldn't move the debt-free date."))
    return lines


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
    """Cross-domain (step 8; G7, G11): the projects, their open tasks, what builds cost and what confirmed builds
    still need from the store, what the business makes."""
    _look(context, sheet, "list_projects", "Projects")
    _look(context, sheet, "list_tasks", "Projects")
    _look(context, sheet, "get_build_costs", "the Workshop")
    _planned_builds(context, sheet)
    _look(context, sheet, "get_ledger_summary", "the business")
    _look(context, sheet, "show_my_why", "your goals")


def _habits(context, sheet, prompt, today):
    """Cross-domain (step 8; D12, D13): how they mean to operate against the records, and the rhythms the Loop
    has learned."""
    _operating(context, sheet, prompt, today)
    _look(context, sheet, "get_workout_summary", "Workout")
    _look(context, sheet, "get_life_events", "your history", period="month")


def _priorities(context, sheet, prompt, today):
    """Cross-domain (step 8; G10, G12, G15): money, freedom, projects (and what confirmed builds still need from the
    store), how they mean to operate, and the year."""
    from core import seasons

    _money_month(context, sheet, prompt, today)
    _look(context, sheet, "get_freedom_progress", "Freedom")
    _look(context, sheet, "list_projects", "Projects")
    _planned_builds(context, sheet)
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


def _project_picture(context, sheet, prompt, today):
    """Cross-domain (Zac, 2026-11-24): a project he's planning and everything it touches, money, materials, growing,
    water, power, time and goals (core/project_ripple.py)."""
    from core import project_ripple

    project_ripple.gather(context, sheet, prompt, today)


WET_CHANCE = 60  # percent chance of rain that makes a day a wet one
_WET_WORDS = re.compile(r"\b(rain|showers?|drizzle|storms?|thunder\w*|snow|sleet)\b", re.I)


def is_wet(day: dict) -> bool:
    """Pure logic. Whether a forecast day is a wet one: its chance of rain at WET_CHANCE or more; without a chance,
    its words say rain, snow or storms."""
    if day.get("rain") is not None:  # the chance decides when there is one ("slight chance of rain" at 10%: dry)
        return day["rain"] >= WET_CHANCE
    return bool(_WET_WORDS.search(day.get("words") or ""))


def weekend_days(today: date, prompt: str = "") -> list[date]:
    """Pure logic. The days a weekend question means: this Saturday and Sunday (on a Saturday, today and tomorrow; on
    a Sunday, today); "next weekend" the one after this week's (on a Sunday, the coming one); one day named alone
    ("how should I spend Saturday?"), its next one, today if it's today."""
    said = (prompt or "").lower()
    names = [d for d, word in ((5, "saturday"), (6, "sunday")) if re.search(rf"\b{word}", said)]
    if len(names) == 1 and "weekend" not in said:
        return [today + timedelta(days=(names[0] - today.weekday()) % 7)]
    if re.search(r"\bnext weekend\b", said):  # the weekend after the one this week
        saturday = today + timedelta(days=(5 - today.weekday()) % 7 + (7 if today.weekday() <= 5 else 0))
        return [saturday, saturday + timedelta(days=1)]
    if today.weekday() == 6:
        return [today]
    saturday = today + timedelta(days=(5 - today.weekday()) % 7)
    return [saturday, saturday + timedelta(days=1)]


def _weekend(context, sheet, prompt, today):
    """Cross-domain (Jarvis brainstorm round 7): the weekend: each day's forecast (core/weather.py), what's due this
    week, the garden's week, his learning paths and his projects, with a line of guidance on fitting outdoor work to
    the better day when two days have a forecast; a wet day (`is_wet`) is named, with guidance for indoor work. The model suggests; nothing is scheduled."""
    from core import weather

    days = weekend_days(today, prompt)
    try:
        card = weather.card(context)
    except Exception:  # noqa: BLE001 - the forecast is one part of the sheet
        log.exception("The weekend plan couldn't read the weather")
        card = {}
    forecast = {d["date"]: d for d in (card.get("days") or [])}
    unit = card.get("unit", "")
    known, wet = 0, []
    for day in days:
        f = forecast.get(day.isoformat())
        if f:
            known += 1
            if is_wet(f):
                wet.append(day)
            sheet.add(FACT, f"{day:%A}: " + (f"{f['words']}, " if f["words"] else "") + f"high {f['high']}{unit}, low {f['low']}{unit}"
                      + (f", {f['rain']}% chance of rain" if f.get("rain") is not None else "") + ".", "the forecast")
        else:
            sheet.add(MISSING, f"No forecast for {day:%A} yet" + ("" if card.get("place") else
                                                                 " (no town set for the weather)") + ".",
                      "the forecast")
    _look(context, sheet, "get_week", "this week", look_ahead="false")  # the garden's its own line below
    _look(context, sheet, "garden_this_week", "the garden")
    _look(context, sheet, "learning_progress", "learning paths")
    _look(context, sheet, "list_projects", "Projects")
    if wet:  # a wet day: indoor work leads it (Jarvis brainstorm round 8)
        sheet.add(CALCULATION, " and ".join(f"{d:%A}" for d in wet) + (" looks" if len(wet) == 1 else " look")
                  + " wet: a day for indoor work.", "the forecast")
        sheet.add(ESTIMATE, "A wet day suits the next practice on a learning path, shop work on a build's cut list, "
                            "or planning and paperwork that's been waiting.", "general guidance")
    if known >= 2:  # a comparison only when there are two days to compare
        sheet.add(ESTIMATE, "Outdoor work (a build, the garden) suits the drier, milder day; practice and indoor jobs "
                            "fit the wetter one. Rest counts too.", "general guidance")


def _winter(context, sheet, prompt, today):
    """Cross-domain (Jarvis brainstorm round 8): ready for winter: how far off his first fall frost is
    (`garden.first_frost`, core/planting_now.py), firewood against his winter figure, fuel and the generator, the
    72-hour kit, the flock (water freezes), what the garden still has due, and the canning shelf; each through the
    tool that already answers it, with what a winter asks of the flock and the house as guidance."""
    from core.planting_now import _first_frost

    try:
        frost = _first_frost(context, today)
    except Exception:  # noqa: BLE001 - the frost date is one line of the sheet
        log.exception("The winter plan couldn't read the first frost")
        frost = None
    if frost is None:
        sheet.add(MISSING, "His first fall frost date isn't set (\"my first frost is October 15\").", "the garden")
    elif frost >= today:
        sheet.add(CALCULATION, f"His first fall frost is about {frost:%B} {frost.day}, {(frost - today).days} days "
                               "from today.", "the garden")
    else:
        sheet.add(FACT, f"His usual first fall frost ({frost:%B} {frost.day}) has passed: winter's here.", "the garden")
    _look(context, sheet, "firewood_check", "firewood")
    _look(context, sheet, "how_prepared", "preparedness (water, food, fuel, power)")
    _look(context, sheet, "emergency_kit", "the 72-hour kit")
    if getattr(context, "flock", None) is not None and getattr(context.flock, "flocks", None):
        _look(context, sheet, "get_eggs", "the flock")
        sheet.add(ESTIMATE, "Hens need water that doesn't freeze (a heated waterer or changing it twice a day), a "
                            "draft-free coop with ventilation up high, and lay less in the short days.",
                  "general guidance")
    _look(context, sheet, "garden_this_week", "the garden")
    _look(context, sheet, "canning_shelf", "the canning shelf")
    sheet.add(ESTIMATE, "Before a hard freeze: drain and store hoses, cover or drain outdoor taps and lines, and have "
                        "the heat source and fuel checked.", "general guidance")


def _quit_by(context, sheet, prompt, today):
    """Cross-domain (Jarvis brainstorm round 8): "what if I quit at the end of next year?": the freedom plan run to
    the day he names (core/freedom.quit_by): saved by then at his pace, the goal, the shortfall and what more a month
    makes it, how long the savings carry the gap after; beside it the business's real hourly, who owes him and his
    debts. Read-only; the date he named is said back."""
    from core import freedom

    when = freedom.quit_date(prompt, today)
    if when is None:
        sheet.add(MISSING, "The question doesn't say when (\"by the end of next year\", \"in 18 months\").",
                  "your question")
        _look(context, sheet, "get_freedom_progress", "Freedom")
        return
    try:
        inputs, _history = freedom.gather(context, today)
    except Exception:  # noqa: BLE001 - the fund is the heart of it: said as missing if it can't be read
        log.exception("The quit-by plan couldn't read the freedom fund")
        sheet.add(MISSING, "The freedom fund couldn't be read.", "Freedom")
        return
    if inputs.needs <= 0:
        sheet.add(MISSING, "What a month of living takes isn't known (set it on Freedom, or let the bank sync show "
                           "it).", "Freedom")
        return
    r = freedom.quit_by(inputs, when, today)
    sheet.add(FACT, f"The day asked about: {when:%B} {when.day}, {when.year}, about {r['months']:g} months away.",
              "your question")
    sheet.add(CALCULATION, f"A month of living takes {_money(context, inputs.needs)}; the homestead covers "
                           f"{_money(context, inputs.homestead)} of it, leaving a gap of {_money(context, r['gap'])} "
                           "a month.", "Freedom")
    sheet.add(CALCULATION, f"Saved by then at the last three months' pace ({_money(context, inputs.pace)} a month): "
                           f"about {_money(context, r['by_then'])}, against a goal of {_money(context, r['goal'])} "
                           f"({inputs.cushion_months} months of the gap, plus builds still to pay for).", "Freedom")
    if r["short"]:
        sheet.add(CALCULATION, f"Short by about {_money(context, r['short'])}: saving about "
                               f"{_money(context, r['more_a_month'] or 0)} more a month from now would close it.",
                  "a freedom calculation")
    else:
        sheet.add(CALCULATION, f"On track: about {_money(context, r['over'])} over the goal by then.",
                  "a freedom calculation")
    if r["lasts_months"] is not None:
        sheet.add(CALCULATION, f"After quitting, what's saved by then covers the gap for about {r['lasts_months']:g} "
                               "months, while the homestead grows.", "a freedom calculation")
    _look(context, sheet, "earnings_per_hour", "the business (its real hourly)")
    _look(context, sheet, "who_owes_me", "the business (owed to him)")
    _look(context, sheet, "list_debts", "Money (debts)")
    sheet.add(ESTIMATE, "Every figure assumes the last three months' pace holds; health insurance and taxes after "
                        "leaving a job aren't in it.", "how this was worked out")


def _homestead(context, sheet, prompt, today):
    """Cross-domain (docs/future/SMART_AG_PLAN.md phase A4): the homestead's morning sheet: the greenhouse as its node
    last reported (core/greenhouse_link.py; never fetched in the middle of an answer), the flock, the garden's week,
    the orchard's month, the property's water and power, tonight's weather against what's growing, and anything
    unusual; each through what already answers it."""
    link = getattr(context, "greenhouse_link", None)
    if link is not None and getattr(link, "taken_over", False):
        try:
            from core.greenhouse_link import status_line

            sheet.add(FACT, "The greenhouse, as its node last reported: " + status_line(link.state), "the greenhouse")
        except Exception:  # noqa: BLE001 - the greenhouse is one line
            log.exception("The homestead sheet couldn't read the greenhouse")
    else:
        sheet.add(MISSING, "MIA isn't watching the greenhouse yet (the node isn't running, or not taken over).",
                  "the greenhouse")
    if getattr(context, "flock", None) is not None and getattr(context.flock, "flocks", None):
        _look(context, sheet, "get_eggs", "the flock")
    _look(context, sheet, "garden_this_week", "the garden")
    _look(context, sheet, "orchard_this_month", "the orchard")
    _look(context, sheet, "water_budget", "water")
    _look(context, sheet, "power_picture", "power")
    _look(context, sheet, "weather_for_my_plans", "tonight's weather against what's growing")
    _look(context, sheet, "anything_unusual", "anything unusual")


def _owned(context, tool: str) -> bool:
    """Whether the household inventory holds a tool by its name (the part before any "and" or parenthesis)."""
    inventory = getattr(context, "inventory", None)
    name = re.split(r"\s+(?:and|or)\s+|\s*\(", tool.lower())[0].strip()
    if inventory is None or len(name) < 3:
        return False
    try:
        return bool(inventory.search(name))
    except Exception:
        return False


def _the_job(context, sheet, prompt, today):
    """Trade Master (DEC-0149; F2, F8, F9, F11, F12): the job or repair in progress (or the one the words name): what
    it is, the step or check in focus, the tools it takes against the household inventory, its stop rules and permit,
    and the holds left. With neither, it says how to start one when the words ask about "this job", and otherwise
    leaves the sheet empty so the plan steps aside. The benchmark's open "this" questions (F2, F8, F9, F11) stay in
    NOT_A_PLAN: the normal turn answers them, with the live job in its context (core/trade_session.context_block)."""
    from core import trade_session, trades

    store = getattr(context, "trade_session", None)
    live = store.live() if store is not None else None
    item = trade_session.item_of(live) if live is not None else trades.find(prompt)
    if item is None:
        if not re.search(r"\b(this|the) job\b", (prompt or "").lower()):
            return
        sheet.add(MISSING, "No job or repair is in progress and the question doesn't name one. Say \"walk me through "
                           "...\" with the job, or \"help me figure out ...\" with the problem, and I'll take it step "
                           "by step.", "Trade Master")
        return
    sheet.looked_up.append("trade_master")
    sheet.add(FACT, trades.outline(item), "Trade Master")
    if live is not None:
        sheet.add(FACT, "Where you are: " + trade_session.say(live), "Trade Master")
    if isinstance(item, trades.Diagnosis):
        return
    have = [t for t in item.tools if _owned(context, t)]
    need = [t for t in item.tools if t not in have]
    if have:
        sheet.add(ESTIMATE, "Tools you seem to have already (matched by name in your inventory): " + ", ".join(have)
                  + ".", "Inventory")
    if need:
        sheet.add(FACT, "Tools the job takes that aren't in your inventory: " + ", ".join(need) + ".", "Trade Master")
    rules = [trades.STOP_RULES[r].when for r in item.stop_if if r in trades.STOP_RULES]
    if rules:
        sheet.add(FACT, "Stop and get help if " + "; or if ".join(rules) + ".", "Trade Master")
    if live is not None:
        holds = [(i, st) for i, (_p, _j, st) in enumerate(item.steps()) if st.hold and i >= live.at]
        if holds:
            sheet.add(FACT, f"{len(holds)} hold point(s) still ahead, the next: {holds[0][1].hold}", "Trade Master")


_RECALL_KINDS = (
    ("commitment", re.compile(r"\b(promis\w*|commit\w*|said i'?d|owe)\b", re.IGNORECASE)),
    ("dropped_goal", re.compile(r"\b(abandon\w*|gave up|given up|giving up|set aside|dropp\w*)\b", re.IGNORECASE)),
    ("decision", re.compile(r"\b(decid\w*|decisions?|chose|chosen|went with)\b", re.IGNORECASE)),
    ("idea", re.compile(r"\b(ideas?|never (pursued|tried)|haven'?t tried|want(ed)? to try)\b", re.IGNORECASE)),
)
_WE_DECIDED = re.compile(r"\b(?:we|you and i)\b[^.?!]*\b(?:decid\w*|decisions?|agree\w*|settle\w*)\b", re.IGNORECASE)
_RECALL_NONE = {"commitment": "No promises kept yet.", "decision": "No decisions kept yet.", "idea": "No ideas kept yet.",
                "dropped_goal": "No goals set aside kept yet."}


def _notes(context, sheet, kind, open_only=False):
    """Adds the life notes of one kind (core/life_notes.py; open ones only when asked), the last twelve, as facts
    "from what you told MIA".
    """
    from core.life_notes import describe

    store = getattr(context, "life_notes", None)
    found = store.of_kind(kind, open_only=open_only) if store is not None else []
    for note in found[-12:]:
        done = " (done)" if note.get("status") == "done" else ""
        sheet.add(FACT, f"{describe(note)}{done}, noted {note.get('at', '')[:10]}.".replace(".,", ","),
                  "what you told MIA")
    return found


def _recall(context, sheet, prompt, today):
    """DEC-0054 (E3, E6, E10, E15): what they promised, decided, want to try and set aside, as kept on their yes.
    "What did *we* decide" with nothing kept also looks in MIA's own decision record, said as hers, not theirs."""
    kinds = [k for k, words in _RECALL_KINDS if words.search(prompt or "")] or [k for k, _ in _RECALL_KINDS]
    for kind in kinds:
        if not _notes(context, sheet, kind):
            sheet.add(MISSING, _RECALL_NONE[kind], "what you told MIA")
            if kind == "decision" and _WE_DECIDED.search(prompt or ""):
                # "What did we decide about eggs?" may mean a decision about MIA herself: those are in her own
                # documents (docs/DECISIONS.md), not in what the person asked her to keep.
                _look(context, sheet, "get_mia_docs", "MIA's own decisions", question=prompt,
                      said_as="Not something the person asked you to keep, but a decision made about you, MIA, in "
                              "your own decision record. Say it that way (\"my records have a decision that…\"): ")
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


_ASKING = frozenset((
    "what", "did", "do", "does", "we", "i", "you", "us", "our", "my", "me", "your", "discuss", "discussed", "discussing",
    "talk", "talked", "talking", "say", "said", "about", "last", "time", "have", "has", "had", "ever", "before",
    "mention", "mentioned", "told", "tell", "the", "a", "an", "of", "on", "for", "to", "in", "is", "are", "was", "were",
    "when", "where", "how", "why", "who", "which", "been", "be", "it", "this", "that", "these", "those", "any",
    "anything", "already", "again", "earlier", "previously", "remember", "with", "and", "or", "go", "over", "went",
))
_GENERIC = frozenset(("project", "problem", "thing", "issue", "idea", "plan", "stuff", "situation", "one"))


def _discussed(context, sheet, prompt, today):
    """E1, E5: what they said about something in earlier conversations (their own words, never a private journal or
    an off-the-record one, which aren't kept), and the memories and kept notes that name it."""
    from core.life_notes import describe

    words = [w for w in re.findall(r"[a-z']+", (prompt or "").lower()) if w not in _ASKING and len(w) > 2]
    if not words or set(words) <= _GENERIC:
        sheet.add(MISSING, "About what? Name it (\"what did we discuss about the roof?\") and I'll look back through "
                           "our conversations.", "your conversations")
        return
    stems = [w.rstrip("s")[:6] for w in words if w not in _GENERIC] or [w.rstrip("s")[:6] for w in words]
    has = lambda text: all(s in text.lower() for s in stems)  # noqa: E731
    store = getattr(context, "conversations", None)
    found = []
    for c in (store.all_conversations() if store is not None else []):
        if c.journal or c.off_record:
            continue
        said = [m for m in c.messages if m.role == "user" and m.content.strip() != (prompt or "").strip()
                and has(m.content)]
        if said:
            found.append((said[-1].timestamp or c.updated_at or "", c, said[-1]))
    for at, c, m in sorted(found, key=lambda f: f[0], reverse=True)[:5]:
        text = " ".join(m.content.split())
        sheet.add(FACT, f"On {at[:10] or 'an earlier day'}, in “{c.title}”, they said: “{text[:160]}"
                        f"{'…' if len(text) > 160 else ''}”", "your conversations")
    memories = getattr(context, "user_memories", None)
    for mem in [m for m in (memories.all_memories() if memories is not None else []) if has(m.text)][-5:]:
        sheet.add(FACT, f"You told MIA: {mem.text}", "Memories")
    notes = getattr(context, "life_notes", None)
    for note in [n for n in (notes.notes if notes is not None else []) if has(f"{n.get('what', '')} {n.get('why', '')}")]:
        sheet.add(FACT, describe(note), "what you told MIA")
    if not sheet.facts:
        sheet.add(MISSING, f"Nothing about {' '.join(words)} in our earlier conversations, memories or notes.",
                  "your conversations")


def _held_back(context, sheet, prompt, today):
    """D4, cross-domain: what they keep running into, what slipped this week, what's unfinished, and the goals they
    set aside, on one sheet: the model names the thread through them, the records are the evidence."""
    _patterns(context, sheet, prompt, today)
    _slipped(context, sheet, prompt, today)  # what's unfinished too


def _open_loops(context, sheet, prompt, today):
    """Plan gatherer (what's unfinished; also gathered by another plan): open promises, tasks, projects and missions."""
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
         r"\b(spend|spent|spending|came in|went out|expenses?|money (going|go|goes|went)|saving)\b", _money_month),
    Plan("debts", "Debts and paying them off",
         ("Which debt should I prioritize?", "What happens if I put an extra $200 toward that debt every month?",
          "How much interest am I paying across all my debts?",
          "When will each of my debts be paid off at my current payment rate?",
          "What would happen if I increased my monthly debt payments?", "When will I be debt free?",
          "Which card should I pay off first?"),
         r"\b(debts?|loans?|pay (it |them |the \w+ )?(off|down)|payoff|interest|credit cards?|debt.free)\b"
         r"|\b(toward|towards) (the|my) cards?\b|\b(pay|paid|paying) (off|down) (the|my) cards?\b"
         r"|\b(which|what) card should i pay (off|down|first)\b"
         r"|\b(the|my) cards?\b[^?.,;!]{0,30}\b(paid off|balance|interest)\b", _debts),
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
         r"\b(next \$|extra money|bonus|emergency (fund|savings)|tax refund|refund go|windfall)\b", _next_dollar),
    Plan("rentals", "The rentals",
         ("How much passive income are my properties generating?", "Is my rental business actually profitable?",
          "Are my rentals making money?", "How are my rental properties doing?"),
         r"\b(rentals?|propert(y|ies)|tenants?|passive income)\b", _rentals),
    Plan("products", "What sells and what it makes",
         ("Which of my products makes the most profit?", "Which products have the best profit margins?",
          "What is my current inventory worth?", "How many products do I need to sell to cover my monthly expenses?",
          "Which products take the least time to produce relative to their profit?", "What sells best?",
          "What should I build next to increase revenue?", "What should I make more of?"),
         r"\b(products?|margins?|sells? best|inventory worth)\b", _products),
    Plan("time", "Where your time goes",
         ("What am I spending too much time on?", "Where does my time go?", "How do I spend my week?",
          "Am I working too much?", "What takes up most of my time?"),
         r"\b(my time|too much time|spend my (week|time|days)|working too much)\b", _time),
    Plan("returns", "What your assets earn",
         ("Which of my assets are generating the best returns?", "What earns me the most money?",
          "Which property makes the most?", "Where am I getting the best return?", "What are my returns?",
          "Which investment would generate the fastest return?"),
         r"\b(returns?|earns? (me )?the most|best return)\b", _returns),
    Plan("product cost", "What one thing costs to make",
         ("What is my actual cost to produce a raised garden bed?", "How much should I charge for a custom engraved planter?",
          "How much does it cost me to make a bench?", "What should I price this at?"),
         r"\b(cost (me )?to (make|produce)|should i charge|price (it|this) at)\b", _product_cost),
    Plan("business month", "The business this month",
         ("How much money did the business make this month?", "Which business expenses could potentially qualify as tax deductions?",
          "How much should I pay myself from the business?", "How much money can I safely reinvest into my business?",
          "Is my business actually growing?", "How's the business doing?"),
         r"\b(the business|my business|business (make|made|doing|growing)|deduct)", _business_month),
    Plan("running costs", "What the workshop costs to run",
         ("How much does it cost to operate my workshop?", "What does my workshop cost to run?",
          "What are my business's running costs?", "How much does the shop cost me a month?"),
         r"\b(cost to (operate|run)|running costs?|operating costs?)\b", _running_costs),
    Plan("market prep", "Getting ready for market",
         ("What materials should I purchase before the next market?", "What do I need for the market?",
          "Am I ready for market day?"),
         r"\bmarket\b", _market_prep),
    Plan("progress", "Goals and progress",
         ("What am I currently working toward?", "What skills have I been developing?", "What have I improved at over the past month?",
          "What is the next milestone in my current questline?", "Am I making progress toward the person I want to become?",
          "What should I work on next?", "Which of my skills would be most beneficial to develop next?",
          "What do you know about my current priorities?", "How am I doing on my goals?",
          "How can I break this large objective into smaller missions?",
          "What would an ideal week of progression look like?"),
         r"\b(working toward|my goals?|questline|milestone|skills?|progress|smaller missions|ideal week)\b", _progress),
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
         r"\b(afford|push(es)? (back|out)|set me back|(if|should|can) i buy an? )", _afford),
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
          "Am I operating the way I want to?", "What's my operating journal say?",
          "What would an ideal week of progression look like?", "What does my ideal week look like?"),
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
          "What business opportunities am I overlooking?", "How can I make more money with what I have?",
          "What equipment investment would improve production efficiency the most?"),
         r"\b(resources|opportunit\w+|make more money|more income)\b", _resources),
    Plan("recall", "What you said you'd do, decided, want to try and set aside",
         ("What did I promise someone?", "What commitments have I made?", "What did I say I'd do?",
          "What decisions have I made about this project?", "What did we decide?", "What did I decide about the roof?",
          "What ideas have I mentioned but never pursued?", "What ideas haven't I tried?",
          "What goals have I abandoned, and why?", "What goals have I set aside?", "What have I given up on?",
          "What were the reasons behind my last major decision?", "Why did I decide that?",
          "Why did I originally decide to pursue this?"),
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
    Plan("discussed", "What you said about it before",
         ("What did we discuss about this project last time?", "Have I mentioned this problem before?",
          "What did we talk about with the roof?", "Have I told you about the leak before?",
          "When did we last talk about the truck?", "What did I say about the garden last time?"),
         r"\b(discuss\w*|talk(ed)? about|mentioned|last time)\b", _discussed),
    Plan("held back", "What might be holding you back",
         ("What is holding me back?", "What's getting in my way?", "Why am I stuck?", "What's slowing me down?",
          "Why can't I make progress?"),
         r"\b(holding me back|in my way|stuck|slowing me down|make progress)\b", _held_back),
    Plan("the job", "The job or repair you're working on",
         ("What tools do I need for this job?", "What step am I on?", "What do I need for this job?",
          "What's left on this job?", "How do I do this step?", "What am I overlooking on this job?",
          "What tools does the job take?"),
         r"\b(this job|the job|what step|this step)\b",
         _the_job),
    Plan("weekend", "The weekend",
         ("What should I do this weekend?", "Plan my weekend.", "What's on for the weekend?",
          "What should I get done on Saturday?", "How should I spend Sunday?", "Is the weekend good for building?"),
         r"\b(this weekend|the weekend|my weekend|next weekend|weekend plans?)\b"
         r"|\b(do|spend|get done|plans?|build|work on|going on)\b[^?]{0,20}\b(saturday|sunday)\b", _weekend),
    Plan("homestead", "The homestead this morning",
         ("How's the homestead?", "What needs doing on the homestead today?", "Give me the homestead rundown.",
          "How are things on the homestead?", "Homestead check.", "What's going on around the place?"),
         r"\b(how'?s the homestead|how is the homestead|homestead (check|rundown|report|today|this morning)|"
         r"things on the homestead|on the homestead today|going on around the place)\b", _homestead),
    Plan("quit by", "Quitting by a date",
         ("What if I quit at the end of next year?", "Could I leave my job in 18 months?",
          "What would it take to quit by next June?", "Can I afford to quit at the end of this year?"),
         r"\b(quit (my|the|this) job|quit work(ing)?|quit the factory|what if i quit|could i quit|can i quit|"
         r"leave (my|the|this) job|leaving (my|the) job|go full[- ]time)\b[^?]{0,40}\b(end of (this|next|the) year|"
         r"next year|in \d+ (months?|years?)|by|next|before)\b", _quit_by),
    Plan("winter", "Ready for winter",
         ("Am I ready for winter?", "What do I need to do before winter?", "Are we set for the cold?",
          "Will I get through the winter?", "What's left to winterize?", "Is the homestead ready for winter?"),
         r"\b(ready for (the )?winter|winter ready|before (the )?winter|winteriz\w*|through (the )?winter|"
         r"set for (the )?(winter|cold)|ready for the cold)\b", _winter),
    Plan("project picture", "What a project touches",
         ("I'm planning to build a greenhouse.", "I want to build a chicken coop this spring.",
          "I'm thinking about putting up a hoop house.", "How would building a greenhouse affect everything else?",
          "What would a new shed mean for the rest of my life?", "We're going to start a big garden next year.",
          "If I build a cold room, what does it touch?", "I'm planning to add solar panels.",
          "What would a greenhouse take?", "I want to put in rain barrels."),
         rf"\b(?:build|put up|set up|start|add|install|put in|building|putting up|starting|adding|installing)"
         rf"{_PROJECT_THING}(?!\s+(?:journal|plan|log|seeds?|notes?))"
         rf"|\b(?:what|how) (?:would|will)(?:\s+(?:building|adding|putting up|starting))?{_PROJECT_THING}"
         r"[^?]{0,15}\b(?:take|touch|change|mean for)\b"
         r"|\b(?:affect|mean for|touch)\b[^?]{0,20}\b(?:everything|the rest)\b", _project_picture),
    Plan("open loops", "What's unfinished",
         ("What commitments have I made that I haven't completed?", "What projects have I started but not completed?",
          "What have I left unfinished?", "What's still open?"),
         r"\b(unfinished|not (yet )?(completed|finished|done)|still open|started but)\b", _open_loops),
)
# Questions no plan answers (DEC-0052): the benchmark's memory, research,
# findings and open-ended ones, and small talk. When one of these is the
# nearest example, no plan runs and the normal turn does.
NOT_A_PLAN = (
    'What permits or registrations do I need to verify?',
    'Which materials should I buy in bulk?',
    'Is it more profitable to make products to order or maintain inventory?',
    'What business opportunities am I overlooking?',
    'How can I turn this frustrating situation into a challenge?',
    'What habits are helping me progress?',
    'What habits are interfering with my goals?',
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
    # Feelings, faith and big leaps are a conversation, not a data question (the Highest Self, H-0089): measured
    # 2026-11-07, "struggling with my faith" went to the patterns plan and "quit my job to stream" to freedom.
    "I've been doubting what I believe.", "I feel guilty about something.", "Is there a God?",
    "What's the meaning of it all?", "I feel like I'm not good enough.", "Am I a good person?",
    "I'm thinking of quitting to chase my dream. Thoughts?", "Nobody understands me like you do.",
)
# A message starting like this asks MIA to change something: never a plan.
CHANGE_VERBS = frozenset((
    "add", "set", "delete", "remove", "log", "mark", "record", "remind", "create", "start", "make", "put", "schedule",
    "cancel", "change", "update", "move", "open", "play", "turn", "undo", "send", "draft", "rename", "clear", "stop",
    "finish", "complete", "save", "track", "note", "write", "buy", "sell", "file", "tag", "link", "unlink",
))
PLAN_BY_NAME = {p.name: p for p in PLANS}
CROSS_DOMAIN = ("afford", "slipped", "projects", "habits", "priorities", "resources", "held back", "time", "weekend",
                "winter", "quit by", "homestead")  # build plan step 8: plans over several apps


# ---------------------------------------------------------------- choosing a plan


THANKS = re.compile(r"^(thanks|thank you|thx|ty|ok|okay|got it|great|cool|sounds good|perfect|awesome|nice|good to "
                    r"know|that's (great|good|helpful|perfect)|will do)\b", re.I)


def match(context, prompt: str) -> Optional[Plan]:
    """The plan a question wants (the best-scoring of match_scored), or None."""
    found = match_scored(context, prompt)
    return found[0] if found else None


def match_scored(context, prompt: str) -> Optional[tuple[Plan, Optional[float]]]:
    """The plan a question asks for, or None (then the normal turn runs).
    Never a how-to or teach-me question (those go to the help docs), never
    a request to change something. Spoken questions have no "?", so by
    meaning anything that isn't a change can match (small talk's nearest
    example is in NOT_A_PLAN); by words only (no embedding model) it must
    look like a question. Either way, a plan never takes a question its `NOT_FOR` words give to a tool (the
    evening's plan never answers "will it frost tonight?"). A how-to counts as one about using MIA only when her tool
    registry says so (`assistant_chat.about_mia`): "how should I pay off my debts?" can reach the debts plan.
    A thank-you or a nod that asks nothing is never a plan's (THANKS)."""
    from core.assistant_actions import looks_like_question
    from core.assistant_chat import looks_like_how_to_question, looks_like_teaching_request

    said = (prompt or "").strip()
    first = re.sub(r"^(please|hey mia|mia|ok|okay)[, ]+", "", said.lower()).split(" ", 1)[0].strip(",.!?")
    if not said or first in CHANGE_VERBS:
        return None
    if THANKS.match(said) and "?" not in said:
        return None  # a thank-you or a nod asks no plan anything ("thanks, that's good to know": live check)
    how_to = looks_like_how_to_question(said, context) or looks_like_teaching_request(said, context)
    from core.meaning import nearest

    found = nearest(context, said, [(p.name, e) for p in PLANS for e in p.examples] + [("-", e) for e in NOT_A_PLAN])
    if found is not None:
        name, score = found
        if how_to and score < EXAMPLE_AT:  # "how do I add a bill?" is the help docs'; "how can I quit faster?" is a plan's
            return None
        if name in PLAN_BY_NAME and score >= MATCH_AT and not _not_for(name, said):
            return PLAN_BY_NAME[name], score
        return None
    if how_to:
        return None
    # No embedding model here (the phone): the plan's own words, when exactly one plan's match.
    if not looks_like_question(said):
        return None
    lowered = said.lower()
    hits = [p for p in PLANS if re.search(p.words, lowered)]
    across = [p for p in hits if p.name in CROSS_DOMAIN]  # the more specific: it gathers the others' facts too
    hits = [p for p in hits if not _not_for(p.name, said)]
    across = [p for p in across if p in hits]
    if len(across) == 1:
        return across[0], None
    return (hits[0], None) if len(hits) == 1 else None


_WEATHER = r"frost|freez\w*|rain\w*|snow\w*|storms?|forecast|weather|windy|too (cold|hot)|cover the"
_GROWING = r"plant(ing)?|seeds?|sow(ing)?|transplant\w*|garden\w*|homestead"
_FLOCK = r"feed|hens?|chickens?|flock|coop"
_LEARNING = r"homework|lessons?|practi[cs]e\w*|woodworking|bushcraft|fitness plan|guitar"
# A plan's own words can catch a question it can't answer: "is it going to frost tonight?" isn't the evening's plan,
# "what should I plant this week" isn't the week's review. Such a question goes on to the tool that answers it
# (the weather against his plans, the garden's week, the flock's feed; tomorrow's first thing is the evening wrap's,
# spending past its usual is "anything unusual"'s, which compares each category with its own normal month; what's due
# this week is the bills', not the week's review; having enough for rent is money ahead's).
NOT_FOR = {
    # the week ahead is get_week's (with its look-ahead), never the ideal week he operates by (the live sweep,
    # 2026-11-25: "what does my week look like?" had been told to add a routine to the operating journal)
    "operating": re.compile(r"^(?!.*\b(?:ideal|operat\w*|rules|want to)\b).*\b(?:my|the|this) week\b", re.I),
    # a debt's balance is the debts' plan, never what he can afford (the live sweep, 2026-11-25)
    "afford": re.compile(r"^(?!.*\bafford\b).*\bhow much is (?:my|the) [\w ]*?(?:loan|card|debt|balance)\b", re.I),
    # who he owes is his debts', never what his assets return (the live sweep)
    "returns": re.compile(r"\b(?:who|what|how much) do (?:i|we) owe\b|\bwho (?:do )?i owe\b", re.I),
    # what he told her before is his past conversations' (list_past_conversations), never one person's (the live
    # sweep, 2026-11-25: "do you remember what I told you yesterday?" had asked which person)
    "person": re.compile(r"\b(?:remember|recall) what i (?:told|said)|\bwhat (?:did )?i (?:tell|told|said to) you\b|"
                         r"\bwhat we (?:talked|spoke) about\b", re.I),
    "tonight": re.compile(rf"\b({_WEATHER}|{_GROWING}|{_FLOCK}|{_LEARNING}|first (thing )?tomorrow|tomorrow first)\b",
                          re.I),
    # what she did on her own today is "catch me up"'s (her own changes), not today's list
    # what's on his grocery list is list_grocery_list's (the live sweep, 2026-11-25: the day's plan had said it didn't
    # know)
    "today": re.compile(rf"\b(on your own|you been up to|while i was (out|gone|away)|{_LEARNING}|(?:grocery|shopping) "
                        r"list)\b"
                        r"|\bwhat did i miss\b(?!.*\b(do|deadlines?|priorit\w*|supposed)\b)", re.I),
    # quitting a habit or a club isn't quitting the job
    "quit by": re.compile(r"\b(smoking|drinking|vaping|chew|caffeine|coffee|soda|sugar|gym|band|team|club|league|"
                          r"class|course|game|drugs?|alcohol)\b", re.I),
    # a weekend for winter work is the weekend's (it names its days); a winter gone is a conversation or the seasons'
    "winter": re.compile(r"\b(weekend|saturday|sunday|last|was|were|did|went|got through|firewood|cords?|wood)\b",
                         re.I),
    # quitting by a date is its own plan's ("what if I quit at the end of next year?"), not the year's priorities
    "priorities": re.compile(r"\b(quit|quitting|leave (my|the) job|leaving (my|the) job)\b", re.I),
    # a project idea for anyone ("a good beginner woodworking project") isn't his own projects (live sweep 2026-11-25)
    "projects": re.compile(r"\b(?:a|an|some)\s+(?:good|easy|simple|first|starter|beginner|beginners|weekend)\b.{0,30}"
                           r"\bprojects?\b|\bbeginners?\b.{0,20}\bprojects?\b|\bprojects? (?:ideas?|for (?:a )?"
                           r"beginners?)\b|\bproject ideas?\b|"
                           # "what should I build next for the shop?" is what_to_make_next (the live sweep)
                           r"\b(?:build|make) next\b.{0,20}\b(?:shop|sell|business)\b|"
                           r"\b(?:build|make|sell)\b.{0,20}\bfor the shop\b", re.I),  # never "my projects for the shop"
    # his net worth is get_net_worth's, not what his products are worth (live sweep 2026-11-25)
    "products": re.compile(r"\bnet worth\b|\bam i worth\b", re.I),
    "money month": re.compile(r"\b(more|less) than (normal|usual)\b|\bunusual\b|\brent(al)?\b|\bwater\b", re.I),
    # a weekend gone is a conversation or recall; a shop's hours, a meal or a meeting on a weekend day isn't the plan
    "weekend": re.compile(r"\b(was|were|did|went|go|last|spent|happened|open|close[sd]?|hours|dinner|lunch|breakfast|"
                          r"meals?|remind|meeting|appointment)\b", re.I),
    # the build's own questions are its tools' (material_list, cut_list, price_build, plan_with_me), and a plan
    # named isn't the picture's: "I want to build a 10 by 12 shed, what materials do I need?"; nor a question about
    # one he already has (what's due in it, how it's doing: by meaning "what's due in the greenhouse?" came close)
    # a survival how-to ("the best way to start a fire in the rain", live sweep 2026-11-25) is no project of his
    "project picture": re.compile(r"\b(what (?:should|can|do) (?:i|we) (?:plant|grow|sow)|when (?:should|do|can) (?:i|we) "
                                  r"(?:plant|sow|start)|"  # what_to_plant's (the live sweep)
                                  r"(?:start|make|light|build)\w* a fire|fire in the (?:rain|wet)|tinder|kindling|"
                                  r"purify|compass|(?:build|make) a (?:survival |debris )?shelter|plans for|blueprints?|"
                                  r"(?:do|does) (?:we|i) have (?:any )?plans|"
                                  r"materials?|lumber|cut list|cuts|charge|price|quote|cost|costs|help me plan|"
                                  r"how many (?:solar )?panels|panels (?:would|do) i need|kwh|size (?:a|my) solar|"
                                  r"hens?|chickens?|coop|laying|"
                                  r"let's plan|plan the|debts?|loans?|bills?|weather|frost|due|overdue|status|"
                                  r"how(?:'s| is) (?:the|my) \w+ (?:doing|going)|needs? doing|needs? done|readings?|"
                                  r"temperature|humidity)\b", re.I),
    # what's on his calendar is the calendar's listing (the live sweep, 2026-11-25)
    "week review": re.compile(rf"\b(what'?s on my calendar|{_WEATHER}|{_GROWING}|{_FLOCK}|{_LEARNING}|training|workouts?|due|bills?|dinner|lunch|breakfast|"
                              rf"supper|meals?|weekend)\b", re.I),
    "coming up": re.compile(rf"\b({_WEATHER}|{_GROWING}|{_FLOCK}|short|cash flow|enough for|enough to|prepared|"
                            r"emergency|emergencies|kit|preparedness)\b", re.I),
    # questions with a tool built for them, which these plans took by meaning (live check through
    # run_assistant_turn, 2026-11-24): spending against his usual is spending_vs_usual, what to make next is
    # what_to_make_next, taxes to set aside are tax_set_aside, who owes him is who_owes_me, the coop's light is the
    # hens' (why_hens_not_laying)
    "time": re.compile(r"\b(spend(ing)? (more|less) than|spend(ing)? money|spent \$|money|eating out|groceries|"
                       r"bills?|budgets?)\b", re.I),  # "am I over budget anywhere?" is budget_left (the live sweep)
    # a course's next lesson is the learning tools' (live check, 2026-11-25: "what's my next Arduino lesson?" was
    # answered by this plan with a lesson it made up)
    "progress": re.compile(rf"\b(make next|for the shop|sell\w*|products?|running low|in stock|{_LEARNING}|arduino|"
                           r"esp ?32|labs?|course)\b", re.I),
    "next dollar": re.compile(r"\b(aside for tax(es)?|save for tax(es)?|owe in tax(es)?|taxes on|tax bracket|irs|"
                              r"self.?employment|estimated tax|quarterly tax)\b", re.I),
    # the same for the business's month (live sweep, 2026-11-25: "how much should I set aside for taxes on my side
    # business?" was told to ask a professional, with tax_set_aside there to work it out)
    "business month": re.compile(r"\b(aside for tax(es)?|save for tax(es)?|put away for tax(es)?|owe in tax(es)?|"
                                 r"taxes on (?:my |the )?(?:side )?(?:business|profit|income|shop)|tax bracket|irs|"
                                 r"self.?employment|estimated tax|quarterly tax)\b", re.I),
    "debts": re.compile(r"\b(owes? me|owing me)\b", re.I),
    # what's due on a vehicle or machine is the maintenance list's (live check: "what's coming up on the truck?")
    "discussed": re.compile(r"\b(coming up on|due on|due for|needs doing on|service|maintenance|oil change)\b", re.I),
    # what she can help with is her own overview (what_can_you_do), not the homestead's morning sheet
    "homestead": re.compile(r"\b(can you help|could you help|help me with|can you do|you help with)\b", re.I),
    # what customers haven't paid is who_owes_me's; rent is rent_collected's
    "open loops": re.compile(r"\b(unpaid|owes? me|owed|invoices?|rent)\b", re.I),
}


def _not_for(name: str, said: str) -> bool:
    """Pure logic. Whether a question is one plan `name` mustn't take (NOT_FOR): its topic is another tool's."""
    words = NOT_FOR.get(name)
    return bool(words and words.search(said or ""))


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
    """Fills a sheet for a plan (and any plans composed onto it) by running their gatherers; a gatherer that fails is
    logged and the rest still run.
    """
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
    "sheet; never suggest an app, feature or task the sheet doesn't mention. Each line names the app it came from "
    "(where a line comes from an app called the Dungeon, that means their paid job, not a game or a workout). "
    "Talk like a person, not a report, in plain text: no headings, bold or symbols. Never give legal or tax "
    "rulings; say to check with a professional. The sheet ends with how sure you can be: when it's likely or "
    "unsure, say so in a few plain words (\"if the pace holds\", \"I don't have your X recorded\"); when it's "
    "sure, just answer."
)
# How a plan's answer is shaped, where the one-thing rule above doesn't fit: added after it for that plan only.
HOW = {
    "project picture": (
        "For this answer, instead of picking one thing: they're planning a project and want to see how it touches the "
        "rest of their life. Write six to nine short sentences, one for each area on the sheet in its order: the "
        "build (the plan named, how many materials, how many still to buy), money, materials on hand, then growing, "
        "water, power, time, goals and research as the sheet has them, saying what their records show for each or "
        "that it isn't recorded. Where one area leans on another, say so (water and power for a greenhouse, the "
        "garden's year for its starts). End with the offer to draft the plan."),
    "homestead": (
        "For this answer, instead of picking one thing: start with the most pressing thing the sheet itself shows (if "
        "it shows none, say things are steady), then one short sentence each for the greenhouse and fish, the flock, "
        "the garden, "
        "the orchard, water and power, from the sheet only, saying what isn't recorded in a few words. Five to eight "
        "sentences in all."),
    "quit by": (
        "For this answer: start with whether the date works at their pace, then in four to six short sentences: the "
        "gap a month, what's saved by then against the goal, what more a month closes any shortfall, how long the "
        "savings carry them after, and what the business and money owed add. Say it rests on the pace holding."),
    "winter": (
        "For this answer, instead of picking one thing: start straight with the answer, no heading, then write five "
        "to eight short sentences going through what winter asks, one each from the sheet: how long until the frost, "
        "firewood, water and food, fuel and power, the kit, the flock, the garden, the canning shelf, saying what "
        "their records show or that it isn't recorded. End with the two or three things to do first."),
    "weekend": (
        "Suggest how they could spend the weekend from the sheet: which day suits what, outdoor work on the better "
        "forecast, what's due or in the garden on a day, practice or rest on the other. A short plan, not every line."),
}
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


_UNITS = (r"(?:drops?|teaspoons?|tsp|tablespoons?|tbsp|cups?|quarts?|gallons?|liters?|litres?|ml|pints?|ounces?|oz|"
          r"grams?|g\b|kg|pounds?|lbs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?|inches|inch|in\b|feet|"
          r"foot|ft|yards?|meters?|metres?|cm|mm|percent|degrees?|ppm|parts|psi|volts?|amps?|watts?|times)")


_SPELLED = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
            "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fifteen": "15", "twenty": "20", "thirty": "30",
            "forty": "40", "fifty": "50", "hundred": "100", "half": "1/2", "third": "1/3", "quarter": "1/4",
            "dozen": "12"}


_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
         "ninety": 90}
_FILLER = {"a", "an", "of", "the", "per", "more", "or", "to"}


def _unit(words: list[str], i: int) -> str:
    """Pure logic. The word a number counts (the next one that isn't "a", "of", "the"...), without a plural s."""
    for w in words[i:i + 4]:
        if w not in _FILLER:
            return w[:-1] if len(w) > 3 and w.endswith("s") else w
    return ""


def spelled_numbers(text: str) -> set[tuple[str, str]]:
    """Pure logic. The numbers a text writes as words, each with what it counts: ("2", "foot") for "two feet",
    ("1/3", "post") for "a third of the post", ("25", "minute") for "twenty-five minutes"; so an answer saying that
    number in digits of that same thing isn't taken as making it up, and "one of these methods" never allows
    "1 drop"."""
    words = re.findall(r"[a-z]+|\d+", (text or "").lower().replace("-", " "))
    out = set()
    i = 0
    while i < len(words):
        w = words[i]
        value = None
        if w in _TENS:
            value, step = _TENS[w], 1
            if i + 1 < len(words) and _SPELLED.get(words[i + 1], "").isdigit() and int(_SPELLED[words[i + 1]]) < 10:
                value, step = value + int(_SPELLED[words[i + 1]]), 2
            value = str(value)
        else:
            value = _SPELLED.get(w) or _SPELLED.get(w[:-1] if w.endswith("s") else "")
            step = 1
        if value:
            unit = _unit(words, i + step)
            out.add((value, "foot" if unit == "feet" else unit))
            i += step
        else:
            i += 1
    return out


def invented_numbers(answer: str, sheet_text: str, prompt: str, strict: bool = False) -> set[str]:
    """Pure logic. Numbers in the answer that are in neither the sheet
    nor the question. Small counts (up to 12) are allowed: the model may
    count the sheet's own lines ("3 bills"). `strict` (a reference's
    figures): a small number is allowed only as a count ("2 methods"),
    never before a unit ("2 drops", `_UNITS`); a list's own step numbers
    ("1.", "**2.**", "Step 3") aren't figures, and one the text spells out of the same thing ("a third of the
    post", "two feet") may be said in digits (`spelled_numbers`)."""
    allowed = numbers_in(sheet_text) | numbers_in(prompt)
    if not strict:
        return {n for n in numbers_in(answer) if n not in allowed and not (n.isdigit() and int(n) <= 12)}
    spelled = spelled_numbers(sheet_text)  # "a third of its length" may be said "1/3 of its length"
    if spelled:
        def said(m):
            """A number in the answer, kept unless the text spelled that number of that same thing."""
            unit = _unit(re.findall(r"[a-z]+", (answer or "").lower()[m.end():m.end() + 40]), 0)
            return " " if (m.group(0), "foot" if unit == "feet" else unit) in spelled else m.group(0)
        answer = re.sub(r"(?<![\d/.])\d+(?:/\d+)?(?![\d/])", said, answer or "")
    answer = re.sub(r"(?mi)^\s*(\**\s*)?\d{1,2}[.)]\s|\bstep\s+\d{1,2}\b|\*\*\d{1,2}[.)]\*\*", " ",
                    answer or "")
    # "2 methods" is a count, taken out; "2 drops" is a figure, kept (by its place, not its value)
    answer = re.sub(r"(?<![\d.,/])\b(?:[1-9]|1[0-2])\s+(?!" + _UNITS + r")(?=[a-z])", "", answer.lower())
    return {n for n in numbers_in(answer) if n not in allowed}


def _personal(conversation) -> bool:
    """Whether a conversation is a personal one (a personal mode, or the journal): plans never answer there, it stays
    a conversation.
    """
    from core.conversation_modes import PERSONAL_MODES

    return getattr(conversation, "mode", None) in PERSONAL_MODES or bool(getattr(conversation, "journal", False))


def request(context, conversation, prompt: str, today: Optional[date] = None) -> Optional[tuple[list, Sheet]]:
    """The model request for a question a plan answers: (messages, the
    sheet), or None (then the normal turn runs). Never in a personal
    mode or the journal: those stay a conversation. A plan with its own
    shape (`HOW`: the project picture area by area, the weekend as a
    plan) has it last in the system message, after the sheet."""
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

    how = f"\n\n{HOW[plan.name]}" if plan.name in HOW else ""  # a plan's own shape, last: a small model reads it
    system = (f"{IDENTITY}{CHARACTER}\n\n{ANSWER_PROTOCOL}\n\nFact sheet ({sheet.title}, today "
              f"{(today or date.today()).isoformat()}):\n{sheet.as_text()}\n\nHow sure you can be: {sure} ({why})."
              f"{how}")
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


def without_source_label(said: str, sheet: Sheet) -> str:
    """Pure logic. The answer without a source label the model began it with ("Dungeon. I don't have...",
    "Dungeon\nYou're welcome.", "Workshop. You're missing...": the sheet labels facts by the app they came from, and
    the model sometimes says the label first; live checks 2026-11-24), a "The" before it too ("The Dungeon. A good
    beginner project...", 2026-11-25)."""
    names = {re.sub(r"\s*\(.*\)$", "", re.sub(r"^the ", "", f.source.strip(), flags=re.I)).strip()
             for f in sheet.facts if f.source}
    names = {n for n in names if n and len(n.split()) <= 3} | {"Dungeon"}  # the protocol's own word for his job
    label = re.compile(r"^\s*(?i:(?:the\s+)?(?:" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
                       + r"))(?:[ \t]*[.:,][ \t]*\n*|[ \t]*\n+)")  # the label (a "The" before it too), then a stop or a break
    trimmed = label.sub("", said, count=1)
    return trimmed if trimmed.strip() else said


def finish(content: str, sheet: Sheet, prompt: str, context=None) -> str:
    """The model's answer when it keeps to the sheet's numbers; else the
    sheet in plain words (never a number MIA didn't look up), noted for the
    answers.numbers loop; and the sheet in plain words when everything on it
    is missing (nothing to word). Either way
    without a stock opener or closer (core.response_composer.polish) and without "the fact sheet" said aloud
    (`without_sheet_words`).
    A source label the answer begins with is taken off first."""
    from core.plain_words import strip_markdown

    said = without_source_label(strip_markdown(content or ""), sheet)
    if not said:
        return sheet.plain()
    if sheet.facts and all(f.kind == MISSING for f in sheet.facts):
        # nothing known, only what's missing: the model had nothing to word and filled it in (heard 2026-11-24:
        # "about 2 months' worth" from a fund that couldn't be read), so the missing lines are the answer
        from core.response_composer import polish

        return polish(sheet.plain())
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
    from core.response_composer import polish

    said = polish(without_sheet_words(said))  # no "Sure!" first, no "let me know" last, no "the fact sheet says"
    calibration.note(context, sheet.plan, sureness(sheet)[0], said)
    return said


def without_sheet_words(said: str) -> str:
    """Pure logic. The answer without her own working said aloud ("the fact sheet says", "the sheet doesn't mention":
    the live sweep, 2026-11-26): a sheet she was given is his records to him."""
    said = re.sub(r"\b(?:the |my )?fact sheet (?:says|shows|lists|suggests) (?:to |that )?", "", said, flags=re.I)
    said = re.sub(r"\b(?:the |my )?(?:fact )?sheet (?:doesn'?t|does not) (?:mention|say|show|have|include|list)\b",
                  "I don't have", said, flags=re.I)
    said = re.sub(r"\bit only (?:talks about|mentions|shows|has)\b", "I only have", said, flags=re.I)
    said = re.sub(r"\b(?:on|in|from) the (?:fact )?sheet\b", "in your records", said, flags=re.I)
    said = re.sub(r"\bthe fact sheet\b", "your records", said, flags=re.I)
    said = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), said)
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
