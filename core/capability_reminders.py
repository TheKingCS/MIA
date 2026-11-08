"""
core.capability_reminders
===========================

Now and then, MIA reminds the person of what they're already capable of doing right now — "did you know you could go
do X?" (Zac, 2026-11-08). It isn't a new task and it isn't a value to live up to: it's a subtle redirect that meets
him where he is — the gentle reminder that the ability is already in his hands, which is often all it takes to get
moving.

Facts in code, the model only phrases — the same rule the rest of MIA follows. The app (`core/application.py`)
gathers the real abilities on his table: a learning path he's a step from advancing (`core/paths.py`), a project he
started and parked (`core/project_manager.py`). This module wraps one in a warm, low-pressure frame. Empty in, empty
out — a reminder never fires without a true thing behind it — and the communication gate paces it, so it stays a
gentle redirect and never a push.
"""

from __future__ import annotations

from typing import Sequence, Tuple

# Warm, low-pressure openings. {x} is a short verb phrase the caller has grounded in real state ("pick the guitar back
# up", "get back to your bookshelf project"); an optional reason follows as its own sentence. The tone is agency, not
# obligation — the point is to remind him the thing is already within reach, never to make him feel behind.
_FRAMES: Tuple[str, ...] = (
    "Did you know you could {x} right now?",
    "Quiet reminder — you've already got everything you need to {x}.",
    "No pressure, but right now you could {x}.",
    "Whenever you want an easy win today: you could {x}.",
    "You're more ready than it feels — you could {x} today.",
    "Something's within reach: you could {x}.",
)


def a_reminder(abilities: Sequence[Tuple[str, str]], roll: float) -> str:
    """Wrap one real, right-now ability in a warm, low-pressure frame — or "" when there's nothing concrete to point
    to.

    `abilities` are `(phrase, reason)` pairs the caller has already grounded in real state: `phrase` is a short verb
    phrase ("pick the guitar back up"), `reason` the honest why ("you're a clean run from the next stage") or "".
    `roll` (0–1) picks the ability and the frame deterministically, so the reminder is testable.
    """
    items = [(p.strip(), (r or "").strip()) for p, r in (abilities or []) if p and p.strip()]
    if not items:
        return ""
    phrase, reason = items[min(int(roll * len(items)), len(items) - 1)]
    frame = _FRAMES[min(int(((roll * 9) % 1.0) * len(_FRAMES)), len(_FRAMES) - 1)]
    line = frame.format(x=phrase)
    return f"{line} {reason}" if reason else line
