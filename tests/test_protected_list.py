"""What MIA can never change about herself, in words, kept true to the lab's own list (core/protected_list.py,
DEC-0225, R-56)."""

from core import protected_list
from core.dev_lab import PROTECTED, touches_protected


def test_every_protected_path_is_named_in_a_group():
    assert protected_list.unnamed() == []


def test_every_named_safeguard_is_on_the_lab_list():
    assert [s for s in protected_list.SAFEGUARDS if s not in PROTECTED] == []


def test_zacs_additions_are_protected_from_any_lab_change():
    added = ["core/grants.py", "core/kind_grants.py", "core/stop.py", "core/browser_safety.py",
             "core/action_effects.py", "core/model_inspection.py", "core/self_merges.py", "core/self_repair.py"]
    assert touches_protected(added) == added


def test_a_group_names_only_paths_that_exist_on_the_list():
    named = [p for _n, _w, paths in protected_list.GROUPS for p in paths]
    assert [p for p in named if p not in PROTECTED] == [] and len(named) == len(set(named))


def test_the_list_said_aloud_names_the_groups_plainly():
    said = protected_list.said()
    assert "your stop" in said and "my safety rules" in said and "refused before" in said
