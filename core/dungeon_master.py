"""
core.dungeon_master
=====================

Living Worlds Phase 2 (DEC-0134): a playable turn. The player says what they do; the **model proposes** narrative and
the state changes it implies; **authoritative code validates and commits** them; MIA narrates the committed result.
This is the spec's hardest rule (§9.1) made real — the language model is never the authority over campaign state, the
same propose→validate→commit split the rest of MIA runs on (`core/actions.py`).

A turn (`take_turn`):
1. Gather the campaign, the character version, its open quests and the last few turns (`core/living_worlds.py`).
2. **Propose** (`propose`): from the state and the player's action, a proposal of narration + typed `Intent`s — a
   quest done, an item gained or lost, a skill learned, or just narration. The model fills this in live; a test passes
   a stub, so the whole loop is deterministic and model-free under test.
3. **Validate** each intent (`validate`): an intent with a difficulty `check` has to beat a d20-style roll plus the
   version's edge; one without just goes through. The model can *suggest* the hero picks the lock; the dice decide.
4. **Commit** the ones that passed (`commit`) to the living_worlds store, keep the turn in the campaign's story
   (`record_turn`: the last RECENT_TURNS go back to the DM next turn, for continuity, and a play screen can show it),
   and record a *fictional* life event (DEC-0137) — never a real one, never real XP.
5. Return what happened: the narration, what changed, and what was attempted but failed.

Everything here is fictional: `require_real` would reject any of it reaching real state, and the events are tagged
fictional, so a campaign can never leak into the person's real life.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from core import life_events
from core.environment import FICTIONAL

INTENT_KINDS = ("complete_quest", "gain_item", "lose_item", "learn_skill", "narrate")
RECENT_TURNS = 5  # how many of the last turns the DM sees, for continuity


@dataclass
class Intent:
    """One state change the model proposes for a turn. `check` (1–20) is the difficulty of a contested action; None
    means it just happens (no roll)."""

    kind: str
    params: dict = field(default_factory=dict)
    check: Optional[int] = None

    @staticmethod
    def from_dict(d: dict) -> "Intent":
        """From the model's JSON, keeping only a known kind and a sane check."""
        kind = d.get("kind") if d.get("kind") in INTENT_KINDS else "narrate"
        check = d.get("check")
        check = int(check) if isinstance(check, (int, float)) and 1 <= check <= 20 else None
        return Intent(kind=kind, params=dict(d.get("params") or {}), check=check)


@dataclass
class TurnResult:
    """What a turn did: the narration shown to the player, what actually changed, and what was tried but failed its
    check."""

    narration: str
    committed: list = field(default_factory=list)
    failed: list = field(default_factory=list)


def _edge(version, intent: Intent) -> int:
    """The version's bonus on a check: the named attribute's value plus 1 if it has the named skill."""
    attr = intent.params.get("attribute", "")
    bonus = 0
    if attr:
        try:
            bonus += int(version.attributes.get(attr, 0))
        except (TypeError, ValueError):
            bonus += 0
    if intent.params.get("skill") and intent.params["skill"] in getattr(version, "skills", []):
        bonus += 1
    return bonus


def validate(intent: Intent, version, roll: float) -> bool:
    """Pure logic. Whether a proposed intent succeeds: an uncontested one always does; a contested one needs a d20
    (from `roll`, 0–1) plus the version's edge to reach its difficulty."""
    if intent.check is None:
        return True
    d20 = int(roll * 20) + 1
    return d20 + _edge(version, intent) >= intent.check


def commit(book, version, intent: Intent) -> Optional[str]:
    """Apply a validated intent to the living_worlds store (the model never calls this). Returns a one-line
    description of what changed, or None when the intent changed nothing (e.g. plain narration, or an unknown item to
    lose)."""
    if intent.kind == "complete_quest":
        quest = book.get_quest(intent.params.get("quest_id", ""))
        if quest is None or quest.status == "done":
            return None
        book.complete_quest(quest.quest_id)
        return f"Quest complete: {quest.name}"
    if intent.kind == "gain_item":
        item = str(intent.params.get("item", "")).strip()
        if not item:
            return None
        book.update_version(version.version_id, inventory=list(version.inventory) + [item])
        return f"Gained: {item}"
    if intent.kind == "lose_item":
        item = str(intent.params.get("item", "")).strip()
        if item not in version.inventory:
            return None
        remaining = list(version.inventory)
        remaining.remove(item)
        book.update_version(version.version_id, inventory=remaining)
        return f"Lost: {item}"
    if intent.kind == "learn_skill":
        skill = str(intent.params.get("skill", "")).strip()
        if not skill or skill in version.skills:
            return None
        book.update_version(version.version_id, skills=list(version.skills) + [skill])
        return f"Learned: {skill}"
    return None  # narrate — nothing to commit


def take_turn(book, campaign_id: str, version_id: str, action: str, propose: Callable,
              roll: Callable[[], float] = random.random) -> TurnResult:
    """Play one turn. `propose(state, action) -> {"narration": str, "intents": [dicts]}` is the model (a stub in
    tests); it sees the last RECENT_TURNS of the story, and this turn joins the story when it's done. ValueError when
    the campaign or version isn't this person's."""
    campaign = book.get_campaign(campaign_id)
    version = book.get_version(version_id)
    if campaign is None or version is None:
        raise ValueError("No such campaign or character version.")

    state = {
        "universe": (book.get_universe(campaign.universe_id).to_dict() if book.get_universe(campaign.universe_id) else {}),
        "campaign": campaign.to_dict(),
        "version": version.to_dict(),
        "open_quests": [q.to_dict() for q in book.quests_in(campaign_id) if q.status == "open"],
        # The story so far, for continuity: the last few turns (what was done, what happened).
        "recent_turns": [{"action": t["action"], "narration": t["narration"]}
                         for t in (book.turns_in(campaign_id, RECENT_TURNS) if hasattr(book, "turns_in") else [])],
    }
    proposal = propose(state, action) or {}
    intents = [Intent.from_dict(d) for d in (proposal.get("intents") or [])]

    committed, failed = [], []
    for intent in intents:
        if intent.kind == "narrate":
            continue
        version = book.get_version(version_id)  # re-read: an earlier intent may have changed it
        if not validate(intent, version, roll()):
            failed.append(intent.kind + (f" ({intent.params})" if intent.params else ""))
            continue
        done = commit(book, version, intent)
        if done:
            committed.append(done)

    narration = str(proposal.get("narration") or "").strip()
    if hasattr(book, "record_turn"):
        book.record_turn(campaign_id, version_id, action, narration, committed, failed)  # the story so far
    life_events.record(book, "campaign_turn", (narration[:80] or f"A turn in {campaign.name}"),
                       [f"campaign:{campaign_id}", f"version:{version_id}"], environment=FICTIONAL)
    return TurnResult(narration=narration, committed=committed, failed=failed)


import json as _json
import re as _re

_DM_PROMPT = """You are the Dungeon Master of a living world. Keep it vivid but grounded in the state, and continue the story
so far (recent_turns: what the player did and what happened).

World state (JSON): {state}

The player's action: {action}

Reply with ONLY a JSON object:
{{"narration": "what happens, 1-3 sentences, second person",
  "intents": [{{"kind": one of complete_quest|gain_item|lose_item|learn_skill|narrate,
    "params": {{"quest_id"|"item"|"skill": "...", "attribute": "optional, for a check", "skill": "optional"}},
    "check": optional 1-20 difficulty for a contested action, else omit}}]}}
Propose only what the action and state justify. You never decide outcomes of a contested action — give it a check and
the dice decide. You never change state yourself; these intents are proposals the game validates."""


def _parse(reply: str) -> dict:
    """Pull the proposal JSON out of a model reply; narration-only on anything unparseable."""
    m = _re.search(r"\{.*\}", reply or "", _re.S)
    if not m:
        return {"narration": (reply or "").strip()[:400], "intents": []}
    try:
        data = _json.loads(m.group(0))
    except ValueError:
        return {"narration": (reply or "").strip()[:400], "intents": []}
    return {"narration": str(data.get("narration") or "").strip(),
            "intents": data.get("intents") if isinstance(data.get("intents"), list) else []}


def model_proposer(context) -> Callable:
    """A `propose` backed by the person's local model (it suggests narration + intents; code still validates and
    commits). Falls back to narration-only when no model is available, so a turn never fails for lack of one."""
    def propose(state: dict, action: str) -> dict:
        llm = getattr(context, "llm", None)
        if llm is None or not hasattr(llm, "generate"):
            return {"narration": "", "intents": []}
        try:
            reply = llm.generate(_DM_PROMPT.format(state=_json.dumps(state)[:6000], action=str(action)[:500]))
        except Exception:  # noqa: BLE001 - a model hiccup must not break the turn
            return {"narration": "", "intents": []}
        return _parse(reply)

    return propose
