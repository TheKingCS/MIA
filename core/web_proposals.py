"""
core.web_proposals
====================

The Toolbox's two "MIA proposes, you confirm" tools on the web and by voice
(DEC-0125: Discovery and Field Captures were in the Qt Toolbox only).

- Discovery (core/discovery_manager.py): `mission_idea(context)` is the
  person's pending mission idea for the Missions page; `suggest(context)`
  asks the model for one (the manager builds the prompt from real facts and
  throws out any idea naming a skill that doesn't exist, so the model only
  ever proposes). `mission_idea.accept` makes it a real mission, assigned by
  MIA; `mission_idea.reject` sets it aside (kept as history).
- Field Captures (core/lite_capture_manager.py): `field_captures(context)`
  lists recordings from MIA Lite waiting for review, transcribed, for the
  Journal page; `capture.keep` puts one in the journal (tagged
  field-capture), `capture.discard` leaves it out. `check_captures(context)`
  looks in the capture folder for new ones (transcribing needs the PC's
  voice).

Suggesting isn't an action: nothing changes until the person accepts, and a
pending idea can always be set aside. The four decisions are actions, so
undo takes them back. Unlike the desktop, keeping a capture from the web
doesn't also pull memories from it (that runs on the PC's model in the
background); the words are in the journal either way.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _pid(context) -> str:
    """The signed-in person's id."""
    from core.person_settings import person_id

    return person_id(context) or ""


def idea_card(proposal, skills=None) -> dict:
    """Pure logic. A mission idea for the page: its name, summary, difficulty, why MIA thinks it's useful, XP and credits, and the skills it trains
    (named when the skill store is given)."""
    def skill_name(skill_id: str) -> str:
        """A skill's icon and name, or its id when it can't be found."""
        skill = skills.get_skill(skill_id) if skills is not None else None
        return f"{skill.icon} {skill.name}" if skill is not None else skill_id

    return {"id": proposal.proposal_id, "name": proposal.name, "summary": proposal.summary,
            "difficulty": proposal.difficulty, "why": proposal.rationale, "xp": proposal.reward_xp, "credits": proposal.reward_credits,
            "skills": [skill_name(w.skill_id) for w in proposal.skill_rewards]}


def mission_idea(context) -> dict:
    """The Missions page's idea section: {"available", "idea": the pending one or None}."""
    discovery = getattr(context, "discovery", None)
    if discovery is None:
        return {"available": False, "idea": None}
    pending = discovery.pending_proposal_for(_pid(context))
    return {"available": True, "idea": idea_card(pending, getattr(context, "skills", None)) if pending else None}


def suggest(context) -> dict:
    """Asks the model for one mission idea from the person's skills, projects, intents and recent missions;
    {"idea"} once it's recorded, or {"error": why not} (one already waiting, no model, or nothing usable came back)."""
    discovery = getattr(context, "discovery", None)
    llm = getattr(context, "llm", None)
    pid = _pid(context)
    if discovery is None:
        return {"error": "Mission ideas aren't on this MIA."}
    if discovery.pending_proposal_for(pid) is not None:
        return {"error": "There's already an idea waiting. Accept it or set it aside first."}
    if llm is None:
        return {"error": "The model isn't running, so MIA can't think one up right now."}
    raw = llm.generate(discovery.build_discovery_prompt(pid))
    proposal = discovery.parse_and_validate_proposal(pid, raw)
    if proposal is None or discovery.record_pending_proposal(proposal) is None:
        return {"error": "MIA couldn't come up with a usable idea just now. Try again in a bit."}
    return {"idea": idea_card(proposal, getattr(context, "skills", None))}


def _idea(context, params):
    """The pending idea the params name, the person's own; ActionError otherwise."""
    proposal = _need(context, "discovery").get_proposal(str(params.get("proposal_id") or ""))
    if proposal is None or proposal.profile_id != _pid(context) or proposal.status != "pending":
        raise ActionError("That idea isn't waiting anymore.")
    return proposal


def _accept_idea(context, params) -> str:
    """Does mission_idea.accept: the idea becomes a real mission, assigned by MIA."""
    proposal = _idea(context, params)
    if context.discovery.accept_proposal(proposal.profile_id, proposal.proposal_id) is None:
        raise ActionError("Missions aren't on this MIA.")
    return f"{proposal.name} is one of your missions now."


def _reject_idea(context, params) -> str:
    """Does mission_idea.reject: the idea is set aside (kept as history)."""
    proposal = _idea(context, params)
    context.discovery.reject_proposal(proposal.profile_id, proposal.proposal_id)
    return f"Set {proposal.name} aside."


def capture_row(proposal) -> dict:
    """Pure logic. A field capture for the page: its id, when it was recorded, the journal title it would get and the
    words."""
    return {"id": proposal.proposal_id, "when": (proposal.captured_at or "")[:16].replace("T", " "),
            "title": proposal.journal_title, "words": proposal.transcript}


def field_captures(context) -> dict:
    """The Journal page's field captures: {"available", "captures": the pending ones for this person (or for no one in
    particular), oldest first}."""
    captures = getattr(context, "lite_captures", None)
    if captures is None:
        return {"available": False, "captures": []}
    pid = _pid(context)
    pending = sorted((p for p in captures.pending_proposals() if not p.profile_id or p.profile_id == pid),
                     key=lambda p: p.captured_at or "")
    return {"available": True, "captures": [capture_row(p) for p in pending]}


def check_captures(context) -> dict:
    """Looks in the capture folder for new recordings and transcribes them; {"found": how many} or {"error"}."""
    captures = getattr(context, "lite_captures", None)
    if captures is None:
        return {"error": "Field captures aren't on this MIA."}
    if getattr(context, "voice", None) is None:
        return {"error": "Recordings are transcribed with the PC's voice, which isn't running."}
    return {"found": len(captures.scan_for_new_captures())}


def _capture(context, params):
    """The pending capture the params name; ActionError otherwise."""
    proposal = _need(context, "lite_captures").get_proposal(str(params.get("capture_id") or ""))
    if proposal is None or proposal.status != "pending":
        raise ActionError("That recording isn't waiting anymore.")
    return proposal


def _keep(context, params) -> str:
    """Does capture.keep: the recording's words go in the journal."""
    proposal = _capture(context, params)
    _need(context, "journal")
    context.lite_captures.accept_proposal(proposal.proposal_id)
    return f"Put {proposal.journal_title} in your journal."


def _discard(context, params) -> str:
    """Does capture.discard: the recording stays out of the journal."""
    proposal = _capture(context, params)
    context.lite_captures.reject_proposal(proposal.proposal_id)
    return "Left that recording out."


PROPOSAL_ACTIONS = {a.kind: a for a in (
    ActionType("mission_idea.accept", "Accept", {"proposal_id": "the idea"},
               lambda c, p: f"Make {_idea(c, p).name} one of your missions", _accept_idea, child_ok=True),
    ActionType("mission_idea.reject", "Set Aside", {"proposal_id": "the idea"},
               lambda c, p: f"Set the idea {_idea(c, p).name} aside", _reject_idea, child_ok=True),
    ActionType("capture.keep", "Keep It", {"capture_id": "the recording"},
               lambda c, p: f"Put {_capture(c, p).journal_title} in your journal", _keep),
    ActionType("capture.discard", "Leave It Out", {"capture_id": "the recording"},
               lambda c, p: f"Leave {_capture(c, p).journal_title} out of your journal", _discard),
)}
ACTION_TYPES.update(PROPOSAL_ACTIONS)
