"""
core.capability_check
=====================

A capability's four descriptions read as one (DEC-0283, LS-04, docs/mia_os/MIA_UNIVERSAL_RUNTIME_CONTRACTS.md
section 2). A capability is described in four places that each work on their own:

1. the tool (`AssistantAction`: its name, whether it's destructive, its handler);
2. the action kind (`ActionType` in core/actions.py);
3. its app's manifest (`capabilities.tiers`, and `outside` for a tool that carries outside text);
4. the effects table (core/action_effects.py: what it reaches and whether it can be undone).

`describe()` assembles one record per capability from them, rewriting none, and `disagreements()` lists where they
contradict each other:

- a tool that runs an action kind is tiered looser than that kind, so the tool would get round the kind's tier
  (found by reading the handler's own code for `propose`, `_run` or `run_as_tool` with the kind's name written
  out; a kind reached through a variable or another function isn't seen, so this is a floor, not a proof);
- an irreversible kind is tiered below `act_with_approval`, so MIA could do something that can't be put back within a
  grant (REQ-AUT-007 already holds this for kinds reaching the system or outside);
- a destructive tool is tiered only to observe or suggest, though it changes things;
- a capability has no tier, or a tier no one knows.

`tests/test_capability_check.py` fails on any disagreement. Pure reads: nothing here writes.
"""

from __future__ import annotations

import inspect
import re
from typing import Optional

# How a tool's handler reaches an action kind by name: `propose(context, "kind"`, the tool modules' own
# `_run(context, "kind"` helpers, and `run_as_tool(context, "kind"` (core/actions.py).
_PROPOSES = re.compile(r"(?:propose|_run|run_as_tool)\(\s*context,\s*\"([a-z_]+\.[a-z_.]+)\"")


def _rank(tier: Optional[str]) -> int:
    """Pure logic. A tier's strictness (observe 0 to never 4); an unknown tier is the strictest, as grants treat it."""
    from core import grants

    return grants.TIERS.index(tier) if tier in grants.TIERS else len(grants.TIERS)


def proposed_kinds(handler) -> list[str]:
    """The action kinds a tool's handler runs by name (`propose`, `_run` or `run_as_tool` with the kind written
    out), read from its code."""
    try:
        source = inspect.getsource(handler)
    except (OSError, TypeError):
        return []
    return sorted(set(_PROPOSES.findall(source)))


def describe(tools: dict, kinds: dict, tiers: dict, outside: set) -> dict[str, dict]:
    """One description per capability, {name: {sort, tier, reach, reversibility, destructive, outside, proposes}},
    from the tools ({name: AssistantAction}), the kinds ({kind: ActionType}), the manifests' tiers and outside tags,
    and the effects table."""
    from core.action_effects import effect_of

    out: dict[str, dict] = {}
    for name, tool in tools.items():
        out[name] = {"sort": "tool", "tier": tiers.get(name), "reach": "", "reversibility": "",
                     "destructive": bool(getattr(tool, "destructive", False)), "outside": name in outside,
                     "proposes": proposed_kinds(getattr(tool, "handler", None))}
    for kind in kinds:
        reach, reversibility = effect_of(kind)
        out[kind] = {"sort": "kind", "tier": tiers.get(kind), "reach": reach, "reversibility": reversibility,
                     "destructive": False, "outside": reach == "outside", "proposes": []}
    return out


def disagreements(described: dict[str, dict]) -> list[str]:
    """Pure logic. Where a capability's descriptions contradict each other, one plain line each; [] when they agree."""
    from core import grants

    problems = []
    for name, d in sorted(described.items()):
        if d["tier"] not in grants.TIERS:
            problems.append(f"{name} has no tier in its app's manifest")
            continue
        for kind in d["proposes"]:
            other = described.get(kind)
            if other is None:
                problems.append(f"{name} proposes {kind}, which isn't an action kind")
            elif _rank(d["tier"]) < _rank(other["tier"]):
                problems.append(f"{name} is {d['tier']} but proposes {kind}, which is {other['tier']}")
        if d["sort"] == "kind" and d["reversibility"] == "irreversible" and _rank(d["tier"]) < _rank(grants.WITH_APPROVAL):
            problems.append(f"{name} can't be undone but is {d['tier']}")
        if d["destructive"] and _rank(d["tier"]) < _rank(grants.WITHIN_GRANT):
            problems.append(f"{name} is destructive but only {d['tier']}")
    return problems


def check() -> list[str]:
    """The disagreements across MIA's own capabilities as the repository has them (the desktop's tools, every kind,
    every manifest)."""
    from core import app_registry, parity
    from core.actions import ACTION_TYPES

    registry = app_registry.load()
    tiers, outside = {}, set()
    for manifest in registry.manifests.values():
        tiers.update(manifest["capabilities"]["tiers"])
        outside.update(manifest["capabilities"].get("outside", []))
    return disagreements(describe(dict(parity.desktop_registry()._actions), dict(ACTION_TYPES), tiers, outside))
