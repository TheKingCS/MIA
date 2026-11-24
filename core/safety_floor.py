"""
core.safety_floor
===================

The safety floor from docs/COGNITIVE_EXTENSION_PROPOSAL.md (slice A):
a deterministic check on every message, before any mode and before the
model sees it. On clear signs that the user may be in danger (thoughts
of suicide, self-harm, someone threatening them) MIA answers with
fixed, human-written text instead of a generated reply.

**Why not let the model handle it.** MIA runs a 3B model that is
sometimes offline, sometimes slow, and not reliable at noticing or
responding to a crisis. This path needs no model, works with Ollama
down, and says the same careful thing every time. After it fires, the
conversation continues in Listen mode (core/conversation_modes.py) so
MIA keeps talking with the person rather than ending the exchange.

**Scope, honestly stated.** This is a floor, not a clinician. It
catches clear phrasing and misses indirect phrasing; its own corpus in
tests/test_safety_floor.py lists both what must trigger and what must
not ("this traffic is killing me"). False positives cost a caring
message; false negatives are why the wording errs broad. Besides the
direct words it knows the commonly recognised indirect signs, each said
of the person themselves ("nobody would miss me", "what's the point of
living", "I wish I'd never been born"), never of a thing, a place or a
time ("nobody would miss this old truck", "what's the point of living in
the city", "better off gone by noon"). A denial cancels only the phrase it
denies. A false positive costs more than the caring message: the
conversation turns to Listen mode (core/talk_it_out.py) until the person
says "back to normal", and a child's guardians are alerted
(core/safety_escalation.py), so the ordinary uses are kept out.

Contacts follow the person's country (core/region.py, 2026-10-01): 988
and 911 in the US, Samaritans and 999 in the UK, and so on; elsewhere,
general advice and findahelpline.com rather than a number that might be
wrong. Each person can add a trusted person (`assistant.safety.trusted_contact`,
free text like "my brother, 555-0142"), named in the reply when set.
"""

from __future__ import annotations

import re
from typing import Optional

from core.region import DEFAULT, Region, region

_DANGER = re.compile(
    r"\b(?:"
    r"kill(?:ing)? myself|end(?:ing)? my (?:own )?life|take my (?:own )?life|end it all|"
    r"(?:want|wanna|going|plan(?:ning)?) (?:to )?die\b|i wish i (?:was|were) dead|better off dead|"
    r"(?:everyone|they|you) (?:would be|'?d be) better off without me|"
    r"suicid(?:e|al)|"
    r"(?:hurt|harm|cut)(?:ing)? myself|self[- ]harm|"
    r"no reason (?:to|for me to) (?:live|keep going)|"
    r"don'?t want to (?:live|be alive|wake up)|"
    r"overdos(?:e|ing)|"
    r"(?:going|want|gonna) to (?:hurt|kill) (?:someone|somebody|him|her|them)|"
    r"(?:he|she|they)(?:'?s| is| are| was)? (?:going to|gonna) (?:hurt|kill) me|"
    r"i'?m not safe|i am not safe|i'?m in danger|i am in danger|"
    # Indirect, but the commonly recognised signs (2026-11-24): about the person themselves, never a thing, a place or
    # a time ("nobody would miss me at the meeting", "better off gone by noon" stay ordinary talk)
    r"(?:nobody|no ?one|no-one)(?: would|'d| will)(?: even| really)? (?:miss me(?!\s+(?:at|for|from|during)\b)|"
    r"(?:notice|care) if i(?:'?m| am| was| were)? (?:gone|dead|died|disappeared|wasn'?t here|weren'?t here)"
    r"(?!\s+(?:at|for|from|during)\b)|care if i died)|"
    r"would(?:n'?t)? (?:anyone|anybody) (?:even |really )?(?:miss me|notice if i|care if i)|"
    r"(?:i'?d|i would|i'?m|i am) (?:be )?better off (?:gone(?!\s+(?:by|before|from|for|early|until|when)\b)|"
    r"not (?:being )?(?:here|around)|dead)|"
    r"better off if i (?:was|were|'?m|am) (?:gone|dead|not here|not around)|"
    r"what(?:'?s| is) (?:even )?the point (?:of|in) (?:living(?!\s+(?:in|on|at|near|by|off|out|so|close)\b)|"
    r"being alive|going on(?=\s*(?:$|[.,!?]|anymore|any more|like this))|me being here)|"
    r"(?:life|my life)(?:'?s not| isn'?t| is not| ain'?t) worth living|"
    r"can(?:'?t|not| not) go on living|(?:don'?t|do not) want to exist(?!\s+on\b)|"
    r"wish i(?:'d| had| was| were)? never (?:been )?(?:born|existed)|"
    r"want (?:it all to (?:end|stop)|everything to (?:end|stop) for good)"
    r")"
)

# Phrases that contain a trigger but plainly aren't one. A denial cancels only the danger phrase inside it ("I'm not
# suicidal" cancels "suicidal"), never another one in the same message: "I'm not suicidal, but what's the point of
# living" is the classic way passive thoughts are said, and still fires.
_NOT_DANGER = re.compile(
    r"\b(?:"
    r"suicide (?:squad|doors?|lane)|"
    r"(?:not|never|wouldn'?t|won'?t|would never) (?:be )?(?:suicidal|hurt myself|harm myself|kill myself)|"
    r"i'?m not suicidal|i am not suicidal|"
    r"overdose on (?:coffee|caffeine|sugar|pizza|tacos|chocolate|netflix)"
    r")"
)


def detect_danger(prompt: str) -> bool:
    """Pure logic. True when `prompt` clearly signals the user (or someone) may be in danger: any danger phrase that
    isn't inside a denial of itself (`_NOT_DANGER`, matched by span). Curly and back quotes are read as '."""
    text = prompt.lower().replace("’", "'").replace("‘", "'").replace("`", "'")
    safe = [m.span() for m in _NOT_DANGER.finditer(text)]
    return any(not any(s <= d.start() and d.end() <= e for s, e in safe) for d in _DANGER.finditer(text))


def safety_reply(trusted_contact: Optional[str] = None, where: Optional[Region] = None, child: bool = False) -> str:
    """The fixed reply. Kept plain and short enough to be spoken aloud.
    `where` is the person's region (core/region.py); the US if not given.
    For a child (core/child_accounts.py) it also asks them to tell an adult,
    and says plainly that a parent who looks after their account will be
    told (core/safety_escalation.py, Q-0002)."""
    where = where or region(DEFAULT)
    contact = (trusted_contact or "").strip()
    contact_line = f" You could also reach out to {contact}." if contact else ""
    if child:
        from core.safety_escalation import CHILD_NOTICE

        contact_line += " Please tell a parent or another grown-up you trust right now, too. " + CHILD_NOTICE
    return (
        "I'm really glad you told me, and I'm taking it seriously. You don't have to carry this alone. "
        f"Please talk to someone who can be with you right now: {where.crisis}. If you or anyone else is in "
        f"immediate danger, call {where.emergency}.{contact_line} I'm right here and I'll keep talking with "
        "you. Do you want to tell me what's going on?"
    )


def trusted_contact_from(context) -> Optional[str]:
    """The person's own trusted contact for a crisis (their setting assistant.safety.trusted_contact), or None when they haven't set one."""
    from core import person_settings  # each person's own contact (accounts, 2026-10-01)

    return person_settings.get(context, "assistant.safety.trusted_contact", None) or None
