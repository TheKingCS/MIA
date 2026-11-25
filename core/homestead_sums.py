"""
core.homestead_sums
=====================

Three everyday homestead sums worked out in code, never from the model's memory (live sweep, 2026-11-25: each was
answered from memory, "around 2 chickens" for a dozen eggs a week among them):

- **Water to store** (`water_to_store`): one gallon a person a day, for drinking and washing (FEMA's Ready.gov and the
  Red Cross), for the days his words say ("two weeks", "3 days", "a month"; else his preparedness target,
  `prepared.target_days`, 14 unless set) and the people they say ("for 4 people", "a family of 5"; else
  `prepared.people`, 1 unless set), with what needs more.
- **Generator runtime** (`generator_runtime`): the fuel his words give ("5 gallons", "20 lb of propane": about 4.24 lb a
  gallon, core/power_ready.py) over his generator's burn rate (`prepared.generator_gph`, from its manual at the load he
  runs it), in hours and in days at his hours a day (`prepared.generator_hours`, 8 unless set). With no burn rate kept,
  where to find it and how to tell MIA, never a typical figure passed off as his.
- **Hens for eggs** (`hens_for_eggs`): the eggs a week his words want ("a dozen eggs a week", "2 eggs a day") over a
  hen's lay: a production layer in her first year or two lays about 5 eggs a week, a Leghorn or a sex-link nearer 6,
  a heritage breed nearer 4 (land-grant extension backyard-poultry guides), then one or two more for winter's short
  days and the molt, when they lay less or stop (core/hen_laying.py).

Each is a read-only tool that takes his own words (`prompt_arg`, core/tool_loop.his_words) and is said as it is
(core/tool_loop.SAID_AS_IS). Nothing is kept.
"""

from __future__ import annotations

import math
import re
from typing import Optional

GALLON_A_PERSON_A_DAY = 1.0  # FEMA (Ready.gov) and the Red Cross
EGGS_A_WEEK = {"production": 5.0, "high": 6.0, "heritage": 4.0}  # a hen in her first year or two
_NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                 "eight": 8, "nine": 9, "ten": 10, "a couple": 2, "a couple of": 2, "half a": 0.5, "a half": 0.5}
_NUM = r"(\d+(?:\.\d+)?|a couple(?: of)?|half a|an?|one|two|three|four|five|six|seven|eight|nine|ten)"


def _number(word: str) -> float:
    """Pure logic. A number said in figures or words."""
    word = word.strip().lower()
    return float(word) if re.match(r"^\d", word) else float(_NUMBER_WORDS.get(word, 1))


def _setting(context, key: str, default: float) -> float:
    """One of his number settings, or the default."""
    try:
        from core import person_settings

        value = person_settings.get(context, key, default)
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError, AttributeError):
        return default


def days_in(words: str) -> Optional[float]:
    """Pure logic. The days his words give: "two weeks", "3 days", "72 hours", "a month" (30), "a year"; None for
    none."""
    said = str(words or "").lower()
    hours = re.search(rf"\b{_NUM}\s+hours?\b", said)
    if hours:  # "72 hours": 3 days (the sixth review)
        return _number(hours.group(1)) / 24
    found = re.search(rf"\b{_NUM}\s+(day|week|month|year)s?\b", said)
    if not found:
        found = re.search(r"\b(?:a|one)?\s*(fortnight)\b", said)
        return 14.0 if found else None
    per = {"day": 1, "week": 7, "month": 30, "year": 365}[found.group(2)]
    return _number(found.group(1)) * per


def people_in(words: str) -> Optional[int]:
    """Pure logic. The people his words give: "for 4 people", "for 1 person", "a family of 5", "the two of us", and
    every group said added up ("2 adults and 2 kids" is 4: the sixth review); None for none."""
    said = str(words or "").lower()
    groups = re.findall(rf"\b{_NUM}\s+(?:people|persons?|adults?|kids?|children|child|teens?|of us)\b", said)
    if groups:
        return max(1, int(sum(_number(g) for g in groups)))
    found = re.search(rf"\bfamily of\s+{_NUM}\b", said) or re.search(rf"\bthe\s+{_NUM}\s+of us\b", said)
    return max(1, int(_number(found.group(1)))) if found else None


def water_to_store(context, words: str) -> str:
    """The water to store for the days and people his words give (or his settings), at a gallon a person a day."""
    days = days_in(words)
    target = days is None
    days = days if days is not None else _setting(context, "prepared.target_days", 14)
    said_people = people_in(words)
    people = said_people or int(_setting(context, "prepared.people", 1))
    gallons = GALLON_A_PERSON_A_DAY * people * days
    who = f"{people} {'person' if people == 1 else 'people'}"
    whose = "" if said_people else " (if there are more of you, say how many)"
    span = f"{days:g} days" + (" (your preparedness target)" if target else "")
    return (f"Store {gallons:g} gallons: a gallon a person a day, for {who}{whose}, for {span}. That's FEMA's and the "
            "Red Cross's figure, for drinking and washing. Store more in hot weather, for anyone nursing or sick, and "
            "for pets. Keep it in food-grade containers, sealed, in a cool dark place; replace stored tap water every "
            "6 months.")


_FUEL = re.compile(rf"\b{_NUM}\s*(gallons?|gal|lbs?|pounds?|liters?|litres?)\b(?:\s+of\s+(propane|lp|gas|gasoline|"
                   r"diesel))?", re.I)


def fuel_in(words: str) -> Optional[tuple]:
    """Pure logic. (gallons, what was said) for the fuel his words give: gallons or liters, cans of a size ("two
    5-gallon cans"), or pounds of propane (about 4.24 lb a gallon); None for none."""
    from core.power_ready import PROPANE_LB_A_GALLON

    cans = re.search(rf"\b{_NUM}\s*(?:x\s*)?(\d+(?:\.\d+)?)[\s-]*(?:gallon|gal)\b", str(words or ""), re.I)
    if cans and re.match(r"\s*\d", cans.group(2)):  # "two 5-gallon cans", "2 x 5 gallon" (the sixth review)
        count, size = _number(cans.group(1)), float(cans.group(2))
        return count * size, f"{count:g} {size:g}-gallon cans ({count * size:g} gallons)"
    found = _FUEL.search(str(words or ""))
    if not found:
        return None
    amount, unit = _number(found.group(1)), found.group(2).lower()
    if unit.startswith(("lb", "pound")):
        return amount / PROPANE_LB_A_GALLON, f"{amount:g} lb of propane"
    if unit.startswith("lit"):
        return amount / 3.785, f"{amount:g} liters"
    return amount, f"{amount:g} gallons"


def generator_runtime(context, words: str) -> str:
    """How long his generator runs on the fuel his words give, at his burn rate (or how to tell MIA his rate)."""
    fuel = fuel_in(words)
    if fuel is None:
        return "How much fuel? Say it in gallons, or pounds of propane, like \"5 gallons\"."
    gallons, said = fuel
    gph = _setting(context, "prepared.generator_gph", 0) or None
    if gph is None:
        return (f"I need your generator's burn rate to work out {said}: its manual gives gallons an hour at a load "
                "(often at 25% and 50%). Tell me, like \"my generator burns half a gallon an hour\", and I'll keep it.")
    hours = gallons / gph
    a_day = _setting(context, "prepared.generator_hours", 8) or 8
    return (f"About {hours:.1f} hours on {said}, at the {gph:g} gallons an hour you told me: "
            f"{hours / a_day:.1f} days running it {a_day:g} hours a day. A bigger load burns faster; check the manual's "
            "rate for the load you'll run. Run it outside, 20 feet from the house, exhaust away from windows.")


def eggs_wanted(words: str) -> Optional[float]:
    """Pure logic. The eggs a week his words want: "a dozen eggs a week", "2 eggs a day", "18 eggs weekly", "a dozen
    eggs every week", and a dozen with no time said is a week's (the sixth review: its own trigger had asked back)."""
    said = str(words or "").lower()
    period = r"(?:\s+(?:a|per|each|every)\s+(day|week)\b|\s+(daily|weekly)\b)?"  # none said: a week
    found = re.search(rf"\b(?:(\d+(?:\.\d+)?|a|one|two|three|half a)\s+)?dozen(?:\s+eggs?)?{period}", said)
    if found:
        many = 12 * (_number(found.group(1)) if found.group(1) else 1)
        return many * (7 if (found.group(2) or found.group(3) or "") in ("day", "daily") else 1)
    found = re.search(rf"\b{_NUM}\s+eggs?{period}", said)
    if found and (found.group(2) or found.group(3)):
        return _number(found.group(1)) * (7 if (found.group(2) or found.group(3)) in ("day", "daily") else 1)
    return None


def hens_for_eggs(context, words: str) -> str:
    """The hens it takes for the eggs a week his words want, at a hen's lay in her prime, with the winter allowance."""
    eggs = eggs_wanted(words)
    if eggs is None:
        return "How many eggs a week (or a day) do you want? Like \"a dozen a week\"."
    typical = math.ceil(eggs / EGGS_A_WEEK["production"])
    high, low = math.ceil(eggs / EGGS_A_WEEK["high"]), math.ceil(eggs / EGGS_A_WEEK["heritage"])
    return (f"For {eggs:g} eggs a week, about {typical} hens: a laying hen in her first year or two lays about 5 a week "
            f"({high} would do it with Leghorns or sex-links, near 6 a week; heritage breeds, near 4, take {low}). Keep "
            "one or two more for winter's short days and the molt, when they lay less or stop, and expect each hen to "
            "lay a bit less every year after her second. Your own egg log shows what yours actually lay.")


def _water_tool(context, arguments: dict) -> str:
    """Tool water_to_store."""
    return water_to_store(context, str(arguments.get("question") or ""))


def _generator_tool(context, arguments: dict) -> str:
    """Tool generator_runtime."""
    return generator_runtime(context, str(arguments.get("question") or ""))


def _hens_tool(context, arguments: dict) -> str:
    """Tool hens_for_eggs."""
    return hens_for_eggs(context, str(arguments.get("question") or ""))


def register_homestead_sum_actions(registry) -> None:
    """Registers water_to_store, generator_runtime and hens_for_eggs: read only, his own words (`prompt_arg`)."""
    from core.assistant_actions import AssistantAction

    words = {"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
             "required": ["question"]}
    registry.register(AssistantAction(
        name="water_to_store", domain="today",
        description="How much drinking water to store for a number of days and people (a gallon a person a day). "
                    "How many days of water he has now is the preparedness answer.",
        parameters=words, handler=_water_tool, prompt_arg="question",
        trigger_phrases=("water should i store", "water to store", "water do i need to store", "how much water for",
                         "gallons of water for", "water should we store", "water storage for")))
    registry.register(AssistantAction(
        name="generator_runtime", domain="power",
        description="How long his generator runs on an amount of fuel (gallons, or pounds of propane), at the burn "
                    "rate he's told MIA.",
        parameters=words, handler=_generator_tool, prompt_arg="question",
        trigger_phrases=("generator run on", "generator last on", "generator go on", "run the generator on",
                         "hours on a tank", "gallons last the generator")))
    registry.register(AssistantAction(
        name="hens_for_eggs", domain="flock",
        description="How many hens it takes for a number of eggs a week or a day.",
        parameters=words, handler=_hens_tool, prompt_arg="question",
        trigger_phrases=("chickens do i need for", "hens do i need for", "how many hens for", "how many chickens for",
                         "hens for a dozen", "chickens for a dozen", "hens to get", "chickens to get")))
