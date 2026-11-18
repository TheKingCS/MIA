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


NUMBERS_LAST = 120  # seconds the numbers he was read stay his to use
_read_out: dict = {}  # person -> (when, [proposal ids in the order read])
_NEEDS_PRESS = frozenset({"lab.approve", "browser.commit"})


def needs_press(kind: str) -> bool:
    """Pure logic. Whether a card can only be approved on screen: one that reaches outside MIA, can't be undone, or
    puts code or a purchase through. A voice in the room isn't enough for those."""
    from core.action_effects import effect_of

    reach, undo = effect_of(kind)
    return kind in _NEEDS_PRESS or reach == "outside" or undo == "irreversible"


def _remember(context, cards: list) -> None:
    """Keeps the order the cards were just read in, so "approve 2" means the second one he heard."""
    import time

    from core.actions import _who

    _read_out[_who(context)] = (time.monotonic(), [c.proposal_id for c in cards])


def _as_read(context, cards: list) -> Optional[list]:
    """The waiting cards in the order last read to him, or None when nothing was read recently or the list has
    changed since (then the numbers are read again rather than guessed)."""
    import time

    from core.actions import _who

    when, ids = _read_out.get(_who(context), (0.0, []))
    by_id = {c.proposal_id: c for c in cards}
    if time.monotonic() - when > NUMBERS_LAST or set(ids) != set(by_id):
        return None
    return [by_id[i] for i in ids]


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


def _kept(context, kind: str, done) -> bool:
    """Whether his standing yes was really kept: the change ran and the grant is there."""
    from core import kind_grants
    from core.actions import EXECUTED

    return getattr(done, "status", "") == EXECUTED and kind_grants.has(context, kind)


def reply(context, text: str) -> Optional[str]:
    """Does what he said to a waiting card and says what happened; None when the words aren't for this. A number
    means the card read to him under that number in the last two minutes; a card that reaches outside or can't be
    undone needs his press; "from now on" is only confirmed when the yes was really kept."""
    from core.actions import ActionError

    found = parse(text)
    if found is None:
        return None
    what, which, always = found
    cards = _waiting(context)
    if what == "list":
        _remember(context, cards)
        return listed(cards)
    if not cards:
        return "Nothing's waiting for you to approve."
    if which is None and len(cards) > 1:
        _remember(context, cards)
        return listed(cards)
    if which is not None:
        heard = _as_read(context, cards)
        if heard is None:  # no numbers read lately, or the list changed since: read them, don't guess
            _remember(context, cards)
            return "The list has changed since I read it. " + listed(cards)
        cards = heard
    if which is not None and not 1 <= which <= len(cards):
        return f"There {'is' if len(cards) == 1 else 'are'} only {len(cards)}. " + listed(cards)
    card = cards[(which or 1) - 1]
    if what == "approve" and needs_press(card.kind):
        return f"That one needs your press on the screen, not just a voice: {card.summary}."
    try:
        if what == "reject":
            context.actions.reject(context, card.proposal_id)
            return f"Rejected: {card.summary}. Nothing was changed."
        done = context.actions.approve(context, card.proposal_id, from_now_on=always)
    except (ActionError, KeyError) as problem:
        return str(problem).strip("'") or "That one can't be approved now."
    said = done.result or f"Done: {card.summary}."
    if always and _kept(context, card.kind, done):
        said += (" From now on I'll just do that kind of change, with an Undo each time; you can take that back in "
                 "your grants.")
    return said
