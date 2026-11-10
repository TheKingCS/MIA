"""
core.saga_actions
===================

The moments kept for the Chronicles (core/saga.py, DEC-0084), seen and
decided without voice (2026-11-09, DEC-0125). "Remember this for the
Chronicles" keeps a moment private until the person marks it; this
gives the Chronicle page the list (`kept_moments`) and one action,
`saga.mark`, that marks one moment for the series, private, or never,
the same as saying "keep that private". Only a moment marked for the
series counts as approved for the comic. A child account has no
moments, as by voice.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger
from core.saga import PRIVACY

log = get_logger(__name__)

WORDS = {"series": "for the series", "private": "private", "never": "never in the Chronicles"}


def _moments(context):
    """The person's moments store, or ActionError (none here, or a child's account)."""
    moments = getattr(context, "saga_moments", None)
    if moments is None or _is_child(context):
        raise ActionError("Moments for the Chronicles aren't kept on this account.")
    return moments


def _is_child(context) -> bool:
    """Whether the signed-in person is a child (no moments for them, as by voice); False when it can't be told."""
    try:
        from core.child_accounts import is_child
        from core.person_settings import person_id

        return bool(is_child(context, person_id(context)))
    except Exception:
        log.exception("Couldn't check whether the Chronicles' reader is a child")
        return False


def _target(context, params) -> tuple[dict, str]:
    """(the moment, the privacy asked for), or ActionError."""
    privacy = str(params.get("privacy") or "")
    if privacy not in PRIVACY:
        raise ActionError(f"Privacy is one of {', '.join(PRIVACY)}.")
    found = next((m for m in _moments(context).moments if m["id"] == str(params.get("moment_id") or "")), None)
    if found is None:
        raise ActionError("That moment isn't kept anymore.")
    return found, privacy


def _describe(context, params) -> str:
    """The approval sentence for saga.mark."""
    moment, privacy = _target(context, params)
    return f"Mark {moment['id']} {WORDS[privacy]}"


def _mark(context, params) -> str:
    """Does saga.mark."""
    moment, privacy = _target(context, params)
    _moments(context).mark(moment["id"], privacy)
    return f"{moment['id']} is {WORDS[privacy]}."


ACTION_TYPES["saga.mark"] = ActionType("saga.mark", "Mark",
                                       {"moment_id": "the moment", "privacy": "series, private or never"},
                                       _describe, _mark)


def kept_moments(context, count: int = 30) -> list[dict]:
    """The person's latest kept moments, newest first: id, when, the summary, its privacy in words, and the actions
    to mark it each other way; [] without the store or for a child."""
    moments = getattr(context, "saga_moments", None)
    if moments is None or _is_child(context):
        return []
    return [{"id": m["id"], "at": m.get("at", ""), "summary": m.get("summary", ""), "privacy": m.get("privacy", ""),
             "privacy_text": WORDS.get(m.get("privacy", ""), m.get("privacy", "")),
             "actions": [{"label": WORDS[p].capitalize(), "action": {"kind": "saga.mark",
                                                                     "params": {"moment_id": m["id"], "privacy": p}}}
                         for p in PRIVACY if p != m.get("privacy")]}
            for m in reversed(moments.recent(count))]
