"""
core.assistant_humor_actions
==============================

"Be funnier", "tone down the jokes", "no jokes for now" (Zac, 2026-11-07):
the person sets how funny MIA is with them, in chat. One tool, set_humor,
moving their own level (core/personality.py HUMOR_LEVELS: off, rare,
sometimes, often, lots) up or down a step or to a level by name. Only the
speaker's own setting changes.
"""

from __future__ import annotations

from core import person_settings
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.personality import HUMOR_LEVELS, humor_level

_ORDER = list(HUMOR_LEVELS)  # least to most
_WORDS = {"off": "no jokes", "rare": "the odd joke", "sometimes": "funny sometimes", "often": "funny often",
          "lots": "as funny as I can be"}
_UP = ("more", "up", "funnier", "higher", "increase")
_DOWN = ("less", "down", "fewer", "lower", "decrease", "serious", "tone down")
_NAMES = {"none": "off", "no": "off", "zero": "off", "never": "off", "stop": "off", "little": "rare",
          "a little": "rare", "occasionally": "rare", "normal": "sometimes", "default": "sometimes",
          "usual": "sometimes", "on": "sometimes", "back": "sometimes", "again": "sometimes", "a lot": "lots",
          "max": "lots", "maximum": "lots", "always": "lots"}


def level_for(wanted: str, current: str) -> str:
    """Pure logic. The level asked for: a step up or down from the current one, or a level by name; "" when it
    isn't clear."""
    wanted = " ".join((wanted or "").lower().split())
    if wanted in HUMOR_LEVELS:
        return wanted
    if wanted in _NAMES:
        return _NAMES[wanted]
    index = _ORDER.index(current)
    if any(word in wanted for word in _DOWN):
        return _ORDER[max(0, index - 1)]
    if any(word in wanted for word in _UP):
        return _ORDER[min(len(_ORDER) - 1, index + 1)]
    return ""


def _action_set_humor(context, arguments: dict) -> str:
    """Tool set_humor: this person's humor level a step up or down, or to a level by name; says where it is now."""
    current = humor_level(context)
    level = level_for(str(arguments.get("level") or ""), current)
    if not level:
        return f"I'm at {_WORDS[current]} now. More or less? Levels: " + ", ".join(_ORDER) + "."
    if level == current:
        edge = " (that's as far as it goes)" if level in (_ORDER[0], _ORDER[-1]) else ""
        return f"I'm already at {_WORDS[level]}{edge}."
    person_settings.put(context, "assistant.humor_level", level)
    if level == "off":
        return "Got it, no jokes. Say \"you can be funny again\" whenever you want them back."
    return f"Done: {_WORDS[level]} from now on." + (" Brace yourself." if level == "lots" else "")


def register_humor_actions(registry: AssistantActionRegistry) -> None:
    """Registers set_humor (domain humor)."""
    registry.register_domain_keywords("humor", ("humor", "humour", "jokes", "joking", "funny", "funnier"))
    registry.register(AssistantAction(
        name="set_humor", domain="humor",
        description="Change how funny MIA is with the user: 'more' or 'less', or a level: off, rare, sometimes, "
                    "often, lots.",
        parameters={"type": "object", "properties": {
            "level": {"type": "string", "description": "'more', 'less', or off / rare / sometimes / often / lots."},
        }, "required": ["level"]},
        handler=_action_set_humor,
        trigger_phrases=("be funnier", "be more funny", "more jokes", "joke more", "less jokes", "fewer jokes",
                         "stop joking", "no jokes", "no more jokes", "tone down the jokes", "tone down the humor",
                         "tone down the humour", "be more serious", "less funny", "funny again", "humor level",
                         "humour level", "sense of humor", "sense of humour", "stop being funny"),
    ))
