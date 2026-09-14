"""
tests.test_user_memory_manager
=================================

Unit tests for core.user_memory_manager. is_duplicate_memory() is
tested directly (pure, deterministic). UserMemoryManager is tested
against a tmp_path scratch area, same monkeypatch pattern as
test_mission_manager.py's isolated_paths.
"""

from __future__ import annotations

import pytest

import core.user_memory_manager as user_memory_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.user_memory_manager import (
    MEMORY_CATEGORIES,
    UserMemory,
    UserMemoryManager,
    is_duplicate_memory,
    memory_relationship_trees,
    related_memories,
)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(user_memory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(user_memory_manager_module, "_USER_MEMORIES_FILE", data_dir / "user_memories.json")


def _make_manager() -> UserMemoryManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return UserMemoryManager(context)


# ----------------------------------------------------------------------
# is_duplicate_memory (pure)
# ----------------------------------------------------------------------

def test_is_duplicate_memory_exact_match():
    assert is_duplicate_memory("Loves hiking", ["Loves hiking"]) is True


def test_is_duplicate_memory_case_and_whitespace_insensitive():
    assert is_duplicate_memory("  loves HIKING  ", ["Loves hiking"]) is True


def test_is_duplicate_memory_not_a_match():
    assert is_duplicate_memory("Loves kayaking", ["Loves hiking"]) is False


def test_is_duplicate_memory_empty_existing_list():
    assert is_duplicate_memory("Loves hiking", []) is False


# ----------------------------------------------------------------------
# related_memories (pure, 2026-09-10 "Memory Palace" cross-linking)
# ----------------------------------------------------------------------

def _memory(memory_id: str, text: str, category: str = "Other") -> UserMemory:
    return UserMemory(memory_id=memory_id, text=text, category=category)


def test_related_memories_finds_a_shared_proper_noun():
    sister = _memory("m1", "The user's sister is named Jamie.", category="Family")
    party = _memory("m2", "The user is planning a birthday party for Jamie next month.", category="Family")
    unrelated = _memory("m3", "The user enjoys fly fishing on weekends.", category="Fishing")

    results = related_memories(sister, [sister, party, unrelated])
    assert results == [party]


def test_related_memories_a_single_shared_generic_word_is_not_enough():
    """Both facts happen to use the word "named" — one weak, generic
    shared word alone must not count as a real relation (the whole
    reason for the minimum-score threshold)."""
    dog = _memory("m1", "The user has a dog named Rex.", category="Pets")
    sister = _memory("m2", "The user's sister is named Jamie.", category="Family")

    assert related_memories(dog, [dog, sister]) == []


def test_related_memories_excludes_the_target_itself():
    only = _memory("m1", "The user has a dog named Rex.", category="Pets")
    assert related_memories(only, [only]) == []


def test_related_memories_the_word_user_never_counts_toward_a_relation():
    """core.assistant_chat's extraction prompt always says "the user"
    instead of he/she — a universal overlap across this whole corpus,
    not a real signal."""
    a = _memory("m1", "The user likes coffee.", category="Other")
    b = _memory("m2", "The user likes tea.", category="Other")
    assert related_memories(a, [a, b]) == []


def test_related_memories_respects_limit():
    target = _memory("m1", "The user's sister is named Jamie.", category="Family")
    others = [
        _memory("m2", "The user is planning a party for Jamie.", category="Family"),
        _memory("m3", "The user is buying a gift for Jamie.", category="Family"),
        _memory("m4", "The user is calling Jamie this weekend.", category="Family"),
    ]
    results = related_memories(target, [target] + others, limit=2)
    assert len(results) == 2


def test_related_memories_sorted_highest_score_first():
    target = _memory("m1", "The user's sister Jamie lives in Denver.", category="Family")
    weak = _memory("m2", "The user is planning a trip to Denver.", category="Travel")  # shares "Denver" only
    strong = _memory("m3", "The user is calling Jamie about the Denver trip.", category="Family")  # shares both

    results = related_memories(target, [target, weak, strong])
    assert results[0] == strong


def test_related_memories_empty_when_nothing_qualifies():
    target = _memory("m1", "The user enjoys fly fishing on weekends.", category="Fishing")
    other = _memory("m2", "The user works as a backend engineer.", category="Work")
    assert related_memories(target, [target, other]) == []


# ----------------------------------------------------------------------
# memory_relationship_trees (pure, 2026-09-14 "graph/tree visualization")
# ----------------------------------------------------------------------

def test_memory_relationship_trees_empty_with_no_memories():
    assert memory_relationship_trees([]) == []


def test_memory_relationship_trees_excludes_fully_isolated_memories():
    a = _memory("m1", "The user enjoys fly fishing on weekends.", category="Fishing")
    b = _memory("m2", "The user works as a backend engineer.", category="Work")
    assert memory_relationship_trees([a, b]) == []


def test_memory_relationship_trees_pairs_a_related_pair_as_root_and_child():
    sister = _memory("m1", "The user's sister is named Jamie.", category="Family")
    party = _memory("m2", "The user is planning a birthday party for Jamie next month.", category="Family")

    trees = memory_relationship_trees([sister, party])

    assert len(trees) == 1
    root = trees[0]
    assert len(root.children) == 1
    assert {root.memory.memory_id, root.children[0].memory.memory_id} == {"m1", "m2"}


def test_memory_relationship_trees_chain_forms_one_cluster_rooted_at_the_hub():
    """A relates to B (shared name "Jamie"), B relates to C (shared
    name "Denver"), but A and C share neither name with each other —
    still one connected tree (transitively linked via B), rooted at B
    since it's the only one with degree 2."""
    a = _memory("m1", "The user's sister is named Jamie.", category="Family")
    b = _memory("m2", "The user is calling Jamie about the upcoming Denver trip.", category="Family")
    c = _memory("m3", "The user is planning a trip to Denver.", category="Travel")

    assert related_memories(a, [a, b, c]) == [b]  # sanity check: a and c really don't relate directly
    assert related_memories(c, [a, b, c]) == [b]

    trees = memory_relationship_trees([a, b, c])

    assert len(trees) == 1
    root = trees[0]
    assert root.memory.memory_id == "m2"
    child_ids = {child.memory.memory_id for child in root.children}
    assert child_ids == {"m1", "m3"}


def test_memory_relationship_trees_two_separate_clusters_largest_first():
    jamie_a = _memory("m1", "The user's sister is named Jamie.", category="Family")
    jamie_b = _memory("m2", "The user is planning a birthday party for Jamie.", category="Family")
    jamie_c = _memory("m3", "The user is buying a gift for Jamie.", category="Family")
    rex_a = _memory("m4", "The user has a dog named Rex.", category="Pets")
    rex_b = _memory("m5", "The user is taking Rex to the vet.", category="Pets")

    trees = memory_relationship_trees([jamie_a, jamie_b, jamie_c, rex_a, rex_b])

    assert len(trees) == 2
    assert len(trees[0].children) + 1 == 3  # the 3-member Jamie cluster is listed first
    assert len(trees[1].children) + 1 == 2  # the 2-member Rex cluster is listed second


def test_memory_relationship_trees_root_tie_broken_by_original_order():
    """Two memories with equal degree (1 each) — the earlier one in
    the original list wins the root spot, deterministically."""
    a = _memory("m1", "The user's sister is named Jamie.", category="Family")
    b = _memory("m2", "The user is planning a birthday party for Jamie.", category="Family")

    trees = memory_relationship_trees([a, b])
    assert trees[0].memory.memory_id == "m1"

    trees_reversed = memory_relationship_trees([b, a])
    assert trees_reversed[0].memory.memory_id == "m2"


# ----------------------------------------------------------------------
# UserMemoryManager CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_memories() == []


def test_add_memory(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("The user's name is Alex.")
    assert memory is not None
    assert memory.text == "The user's name is Alex."
    assert manager.all_memories() == [memory]


def test_add_memory_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_memory("Loves hiking in the Cascades.")

    reloaded = _make_manager()
    assert len(reloaded.all_memories()) == 1
    assert reloaded.all_memories()[0].text == "Loves hiking in the Cascades."


def test_add_memory_rejects_duplicate(isolated_paths):
    manager = _make_manager()
    manager.add_memory("Loves hiking.")
    duplicate = manager.add_memory("loves hiking.")
    assert duplicate is None
    assert len(manager.all_memories()) == 1


def test_add_memory_rejects_blank_text(isolated_paths):
    manager = _make_manager()
    assert manager.add_memory("   ") is None
    assert manager.all_memories() == []


def test_add_memory_records_source_conversation(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("Has a dog named Rex.", source_conversation_id="conv123")
    assert memory.source_conversation_id == "conv123"


def test_add_memory_defaults_to_other_category(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("Has a dog named Rex.")
    assert memory.category == "Other"


def test_add_memory_stores_a_real_category(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("Has a dog named Rex.", category="Pets")
    assert memory.category == "Pets"


def test_add_memory_falls_back_to_other_for_unknown_category(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("Plays tennis.", category="Sports")
    assert memory.category == "Other"


def test_add_memory_category_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_memory("Has a dog named Rex.", category="Pets")

    reloaded = _make_manager()
    assert reloaded.all_memories()[0].category == "Pets"


def test_user_memory_from_dict_backward_compatible_without_category_field():
    # Pre-Memory-Palace records on disk never had a "category" key at all.
    memory = UserMemory.from_dict({"memory_id": "m1", "text": "Loves hiking."})
    assert memory.category == "Other"


def test_add_memory_accepts_every_real_category(isolated_paths):
    manager = _make_manager()
    for category in MEMORY_CATEGORIES:
        memory = manager.add_memory(f"A fact filed under {category}.", category=category)
        assert memory.category == category


def test_delete_memory(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("Loves hiking.")
    manager.delete_memory(memory.memory_id)
    assert manager.all_memories() == []


def test_delete_memory_is_idempotent(isolated_paths):
    manager = _make_manager()
    manager.delete_memory("does-not-exist")  # must not raise


def test_clear_all(isolated_paths):
    manager = _make_manager()
    manager.add_memory("Fact one.")
    manager.add_memory("Fact two.")
    manager.clear_all()
    assert manager.all_memories() == []


def test_all_memories_sorted_newest_first(isolated_paths):
    # created_at has only second-level precision (timespec="seconds"),
    # so two real add_memory() calls in the same test could collide on
    # the same wall-clock second — set distinguishable timestamps
    # directly rather than relying on real-time granularity.
    manager = _make_manager()
    first = manager.add_memory("Fact one.")
    second = manager.add_memory("Fact two.")
    first.created_at = "2026-07-14T10:00:00"
    second.created_at = "2026-07-14T11:00:00"

    ordered = manager.all_memories()
    assert ordered[0].memory_id == second.memory_id
    assert ordered[1].memory_id == first.memory_id


def test_load_handles_corrupt_json_gracefully(isolated_paths, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "user_memories.json").write_text("{not valid json", encoding="utf-8")
    manager = _make_manager()
    assert manager.all_memories() == []
