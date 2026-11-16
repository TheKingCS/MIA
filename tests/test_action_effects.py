"""
tests.test_action_effects
===========================

What each action kind reaches and whether it can be undone (REQ-AUT-006, REQ-AUT-007; core/action_effects.py): every
declared effect is a real kind with a known reach and reversibility; a kind whose code deletes or moves files, uses
the network, talks to a device, runs a program or merges code is declared, never left as "records"; anything reaching
the system or outside waits for the person's yes every time; and an irreversible kind's approval sentence says so.
The sweep reads each kind's code and its own module's helpers: an outward call hidden inside another module's store
method isn't seen, so a new store that deletes files or talks to a device should be declared by whoever writes it.
"""

from __future__ import annotations

import inspect
import re
import sys

import core.actions as actions
from core.action_effects import EFFECTS, REACHES, REVERSIBILITY, effect_of, says_irreversible
from core import parity

parity.desktop_registry()  # every tool module, so every action kind the app has is registered

# The marks of reaching beyond the stores, read in each kind's own code and the helpers of its module it calls.
MARKS = re.compile(r"\.unlink\(|rmtree|shutil\.move|os\.remove|os\.rename|\.rename\(|tak\.send|home_call|"
                   r"subprocess|Popen|urlopen|requests\.|smtp|dev_lab\.approve|perform_pending|save_to_files|"
                   r"make_folder|delete_picture|save_picture|file_item|unfile|download_area|path_of\(")
# Kinds whose code shows a mark but stays inside MIA's records, with why.
INSIDE = {
    "art.delete": "keeps the picture's file aside (art/removed/), so undo brings it back",
    "wallet.delete": "keeps the card's photos until removed for good, so undo brings it back",
    "weather.place": "looks a town up online; what changes is only his own setting",
}


def _code(kind: str) -> str:
    """A kind's execute and the helpers of its own module that it calls, as text."""
    fn = actions.ACTION_TYPES[kind].execute
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        return ""
    mod = sys.modules.get(fn.__module__)
    for name in set(re.findall(r"\b(_?[a-z][a-z0-9_]*)\(", src)):
        helper = getattr(mod, name, None)
        if inspect.isfunction(helper) and helper.__module__ == fn.__module__ and helper is not fn:
            try:
                src += inspect.getsource(helper)
            except (OSError, TypeError):
                pass
    return src


def test_every_declared_effect_is_a_real_kind_with_a_known_reach_and_reversibility():
    for kind, (reach, reversible, why) in EFFECTS.items():
        assert kind in actions.ACTION_TYPES, kind
        assert reach in REACHES and reversible in REVERSIBILITY and why, kind
    assert effect_of("bill.add") == ("records", "undoable")
    assert actions.ACTION_TYPES["browser.commit"].as_dict()["reversibility"] == "irreversible"


def test_no_kind_reaches_beyond_the_stores_without_being_declared():
    missed = [k for k in sorted(actions.ACTION_TYPES) if k not in EFFECTS and k not in INSIDE and MARKS.search(_code(k))]
    assert missed == [], f"Declare these in core/action_effects.py (or in INSIDE here, with why): {missed}"


def test_anything_reaching_the_system_or_outside_asks_every_time():
    from core import grants

    loose = [k for k, (reach, _r, _w) in EFFECTS.items()
             if reach in ("system", "outside") and grants.tier_of(k) not in (grants.WITH_APPROVAL, grants.NEVER)]
    assert loose == []


def test_an_irreversible_kind_says_so_before_it_is_approved(tmp_path):
    from types import SimpleNamespace

    from core.actions import ActionCenter, ActionType

    assert says_irreversible("Delete notes.txt").endswith("This can't be undone.")
    assert says_irreversible("Delete it for good") == "Delete it for good"
    actions.ACTION_TYPES["zz.gone"] = ActionType("zz.gone", "Gone", {}, lambda c, p: "Delete the old log", lambda c, p: "")
    EFFECTS["zz.gone"] = ("device", "irreversible", "a test kind")
    try:
        proposal = ActionCenter().propose(SimpleNamespace(config=None), "zz.gone")
        assert proposal.summary == "Delete the old log. This can't be undone."
    finally:
        actions.ACTION_TYPES.pop("zz.gone")
        EFFECTS.pop("zz.gone")
