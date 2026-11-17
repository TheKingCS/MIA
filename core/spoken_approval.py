"""
core.spoken_approval
======================

Approving a waiting card by voice, "approve it from now on" included (DEC-0215; Zac, 2026-11-17: "MIA should offer an
approve for now or Approve going forward option"; the card's two buttons, said). A quick command (core/quick_commands.py):
his own words, matched in code, never the model's, so nothing she reads or writes can approve anything.

**What it hears** (the whole thing he said, `parse`):
- "what's waiting for me?", "anything to approve?": the cards waiting, numbered;
- "approve it", "approve that", "approve 2": Approve Once;
- "approve it from now on", "yes, approve it going forward", "approve 2 from now on": Approve From Now On, refused
  in the card's own words for a kind that always asks (money, messages, publishing, deletion outside undo, system
  changes: core/kind_grants.py). Always with the word "approve" (or "accept"): a bare "yes, from now on" or "always
  do that" answers too many other questions (the review of 2026-11-18);
- "reject it", "decline that", "reject 2": declined, nothing runs.

A bare "yes" or "do it" isn't taken: those answer her other questions. With several cards waiting and no number, she
lists them and asks which. Never in a personal mode or the journal (the turn skips quick commands there).
"""

from __future__ import annotations

import re
from typing import Optional

_LIST = re.compile(r"^(what'?s|what is|anything|is there anything) (waiting|to approve|waiting for me|needing my "
                   r"approval|that needs my approval)( for me)?\??$|^what needs my approval\??$")
_ALWAYS = r"(,? ?(and )?(from now on|going forward|always))"
_APPROVE = re.compile(r"^(yes,? ?)?(approve|accept) (it|that|this|(number )?(?P<n>\d+))" + _ALWAYS + r"?[.!]?$")
_REJECT = re.compile(r"^(no,? ?)?(reject|decline) (it|that|this|(number )?(?P<n>\d+))[.!]?$")


def parse(text: str) -> Optional[tuple[str, Optional[int], bool]]:
    """Pure logic. (what, which, from_now_on) for words that are for this, else None: what is "list", "approve" or
    "reject"; which is the card's number when he said one. Approving always needs the word "approve" or "accept"."""
    said = " ".join((text or "").lower().replace("’", "'").split()).strip()
    if _LIST.match(said):
        return "list", None, False
    m = _APPROVE.match(said)
    if m:
        return "approve", int(m.group("n")) if m.group("n") else None, bool(re.search(r"from now on|going forward|always",
                                                                                    said))
    m = _REJECT.match(said)
    if m:
        return "reject", int(m.group("n")) if m.group("n") else None, False
    return None


def _waiting(context) -> list:
    """This person's waiting cards, oldest first."""
    from core.actions import _who

    actions = getattr(context, "actions", None)
    if actions is None:
        return []
    return sorted(actions.pending(_who(context)), key=lambda p: p.created_at or "")


def listed(cards: list) -> str:
    """Pure logic. The waiting cards, numbered, in words."""
    if not cards:
        return "Nothing's waiting for you."
    if len(cards) == 1:
        return f"One thing is waiting: {cards[0].summary}. Say \"approve it\", \"approve it from now on\" or \"reject it\"."
    lines = "; ".join(f"{i}. {c.summary}" for i, c in enumerate(cards, 1))
    return (f"{len(cards)} things are waiting: {lines}. Say \"approve\" or \"reject\" and its number; add \"from now "
            f"on\" to stop being asked for that kind.")


def reply(context, text: str) -> Optional[str]:
    """Does what he said to a waiting card and says what happened; None when the words aren't for this."""
    from core.actions import ActionError

    found = parse(text)
    if found is None:
        return None
    what, which, always = found
    cards = _waiting(context)
    if what == "list":
        return listed(cards)
    if not cards:
        return "Nothing's waiting for you to approve."
    if which is None and len(cards) > 1:
        return listed(cards)
    if which is not None and not 1 <= which <= len(cards):
        return f"There {'is' if len(cards) == 1 else 'are'} only {len(cards)}. " + listed(cards)
    card = cards[(which or 1) - 1]
    try:
        if what == "reject":
            context.actions.reject(context, card.proposal_id)
            return f"Rejected: {card.summary}. Nothing was changed."
        done = context.actions.approve(context, card.proposal_id, from_now_on=always)
    except (ActionError, KeyError) as problem:
        return str(problem).strip("'") or "That one can't be approved now."
    said = done.result or f"Done: {card.summary}."
    if always:
        said += (" From now on I'll just do that kind of change, with an Undo each time; you can take that back in "
                 "your grants.")
    return said
