"""
core.meat_cure
================

"How much curing salt for 5 pounds of pork belly?" (Jarvis brainstorm, round 12; his homestead): the meat cure worked
out in code (core/eng_calcs.py `meat_cure`), never from the model's memory: curing salt #1 by the meat's weight for
the ingoing nitrite (156 ppm for most cured meat, 120 for bacon, `PPM`), and plain salt to the salt percentage
(2.5% unless he says another). The weight is read from his words (`weight_in`: lb, oz, kg, g), the product from them
too (bacon, sausage, ham, jerky). Always said with: weigh it on a scale, keep it in the fridge at 34 to 40 F, the
time from a tested recipe, and curing salt #2 only for long dry-cured meats he won't cook (salami, prosciutto).

**Checked** 2026-11-24: curing salt #1 is 6.25% sodium nitrite, 93.75% salt, and a level teaspoon cures 5 lb (the
National Center for Home Food Preservation); FSIS caps ingoing nitrite at 120 ppm in pumped or immersion-cured bacon
(with 550 ppm ascorbate or erythorbate) and 200 ppm in dry-cured bacon (9 CFR 424.21-22), and its quick reference
gives 156 ppm for comminuted products. So 120 for any bacon here errs low, and the 100 to 200 ppm range refuses a
long dry cure's 625, which belongs to a tested recipe with curing salt #2.
"""

from __future__ import annotations

import re
from typing import Optional

PPM = {"bacon": 120}  # the USDA's limit for pumped or immersion-cured bacon; everything else 156
DEFAULT_PPM = 156
_WEIGHT = r"(\d+(?:\.\d+)?)\s*-?\s*(pounds?|lbs?|ounces?|oz|kilograms?|kilos?|kg|grams?|g)\b"
_SALT = r"(\d+(?:\.\d+)?)\s*%\s*salt|salt\s*(?:at|of)?\s*(\d+(?:\.\d+)?)\s*%"


def weight_in(words: str) -> Optional[str]:
    """Pure logic. The meat's weight as a quantity ("5 lb", "2 kg"), or None."""
    found = re.search(_WEIGHT, str(words or ""), re.I)
    if not found:
        return None
    unit = found.group(2).lower()
    unit = ("lb" if unit.startswith(("pound", "lb")) else "oz" if unit.startswith(("ounce", "oz"))
            else "kg" if unit.startswith(("kilo", "kg")) else "g")
    return f"{found.group(1)} {unit}"


def say(words: str) -> str:
    """The answer for what he said (see the module's opening)."""
    from core import eng_calcs

    weight = weight_in(words)
    if weight is None:
        return "How much meat, by weight (pounds or kilograms)? I work the cure out from that."
    product = next((p for p in ("bacon", "ham", "sausage", "jerky", "corned beef", "pastrami", "brisket")
                    if p in str(words).lower()), "")
    ppm = PPM.get(product, DEFAULT_PPM)
    salt = re.search(_SALT, str(words), re.I)
    inputs = {"meat": weight, "nitrite": str(ppm)}
    if salt:
        inputs["salt"] = f"{salt.group(1) or salt.group(2)} %"
    try:
        result = eng_calcs.calculate("meat_cure", inputs)
    except eng_calcs.CalcError as problem:
        return str(problem)
    why = ("120 ppm, the USDA's limit for bacon" if ppm == 120 else "156 ppm, the USDA's level for most cured meat")
    return (f"{result['said']} That's {why}. Mix it evenly over the meat, keep it in the fridge at 34 to 40 F, and "
            "go by a tested recipe for how long. Use curing salt #1 (pink) for anything you'll cook or smoke; #2 is "
            "only for long dry-cured meats you won't cook. Check it against a tested recipe (the USDA's or your "
            "extension service's) before you cure.")


def _tool(context, arguments: dict) -> str:
    """Tool meat_cure: `say` on his words."""
    return say(" ".join(str(arguments.get(k) or "") for k in ("question", "meat")))


def register_meat_cure_actions(registry) -> None:
    """Registers meat_cure."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="meat_cure", domain="kitchen",
        description="How much curing salt #1 (pink salt) and salt to cure meat (bacon, ham, sausage, jerky, corned "
                    "beef) by its weight, worked out in code with the USDA's nitrite levels. Fermenting vegetables "
                    "is a brine, not this.",
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "Their words, with the meat's weight and what it is."}},
            "required": ["question"]},
        handler=_tool, trigger_phrases=("curing salt", "cure #1", "cure no. 1", "prague powder", "pink salt",
                                        "pink curing", "cure my bacon", "cure bacon", "cure a ham", "cure the ham",
                                        "cure the bacon", "cure some bacon", "cure pork", "cure the pork",
                                        "dry cure", "equilibrium cure", "make bacon", "making bacon",
                                        "cure venison", "cure jerky", "cure for jerky", "cure for sausage"),
    ))
