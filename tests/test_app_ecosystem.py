"""
tests.test_app_ecosystem
==========================

MIA's understanding of her own apps (migration phase M2, DEC-0178; core/app_ecosystem.py,
core/assistant_app_registry_actions.py): the inventory, one app's parts, which app does something, and the check
(health, overlaps, gaps) are answered from the manifests and the runtime; a failing job is pinned on the app whose
manifest claims it; overlaps are said as suggestions; the four tools are registered on the PC and the phone's
runtime and claimed by the Apps app; and the Apps page carries the same section.
"""

from types import SimpleNamespace

import pytest

from core import app_ecosystem, app_registry, parity


@pytest.fixture(scope="module")
def tools():
    """Her tools as the PC registers them."""
    return parity.desktop_registry()


@pytest.fixture(scope="module")
def reg():
    """The registry from the repository's manifests."""
    return app_ecosystem.registry()


def _context(tools, scheduler=None, tmp=None):
    """A context with her tools, an optional scheduler and an optional data folder."""
    return SimpleNamespace(assistant_actions=tools, scheduler=scheduler, data_dir=tmp)


def test_the_inventory_counts_every_live_app_and_names_the_retired_ones(reg):
    inv = app_ecosystem.inventory(reg)
    assert inv["apps"] == len(reg.apps())
    assert sum(len(n) for n in inv["areas"].values()) == inv["apps"]
    assert inv["retired"] == sorted(m["name"] for m in reg.apps(True) if m["retired"])
    said = app_ecosystem.inventory_sentence(reg)
    assert said.startswith(f"I have {inv['apps']} apps.") and "Greenhouse" in said


def test_one_app_is_described_from_its_manifest_by_name_or_inside_a_sentence(reg):
    said = app_ecosystem.details_sentence(reg, "what can the greenhouse app do")
    m = reg.get("greenhouse")
    assert said.startswith("Greenhouse (")
    assert f"{len(m['capabilities']['actions'])} action" in said
    assert ".." not in said
    assert "don't have an app called" in app_ecosystem.details_sentence(reg, "Zeppelin")


def test_which_app_names_the_owner_of_an_exact_capability_and_ranks_by_words_otherwise(reg, tools):
    ctx = _context(tools)
    assert app_ecosystem.which_sentence(reg, ctx, "record_price") == "record_price belongs to World."
    found = app_ecosystem.which(reg, ctx, "log an energy reading")
    assert found and found[0]["app"]["id"] == "power"
    assert app_ecosystem.which(reg, ctx, "the a of") == []


def test_a_failing_job_is_pinned_on_the_app_whose_manifest_claims_it(reg, tools):
    job = next(j for j in reg.get("world_intel")["runtime"]["background"])
    scheduler = SimpleNamespace(status=lambda: [
        {"name": job, "failures_in_a_row": 3, "last_error": "timed out"},
        {"name": "quiet", "failures_in_a_row": 0, "last_error": ""}])
    found = app_ecosystem.health(reg, _context(tools, scheduler))
    assert list(found) == ["world_intel"]
    assert "failed 3 times in a row (timed out)" in found["world_intel"][0]
    assert "Wrong now: World" in app_ecosystem.check_sentence(reg, _context(tools, scheduler))


def test_a_registry_problem_is_pinned_on_the_app_it_names():
    m = dict(app_ecosystem.registry().get("greenhouse"))
    m["capabilities"] = {"tools": list(m["capabilities"]["tools"]) + ["no_such_tool"],
                         "actions": list(m["capabilities"]["actions"])}
    broken = app_registry.Registry(manifests={**app_ecosystem.registry().manifests, "greenhouse": m})
    found = app_ecosystem.health(broken, SimpleNamespace(scheduler=None))
    assert any("no_such_tool" in p for p in found["greenhouse"])


def test_overlaps_are_between_different_apps_and_said_as_suggestions(reg, tools):
    ctx = _context(tools)
    for o in app_ecosystem.overlaps(reg, ctx):
        assert o["apps"][0] != o["apps"][1] and o["alike"] >= app_ecosystem.OVERLAP
    said = app_ecosystem.check_sentence(reg, ctx)
    assert said.startswith("Every app's record agrees with the code")
    if app_ecosystem.overlaps(reg, ctx):
        assert "My suggestion, not a fault" in said


def test_the_four_tools_are_on_the_pc_and_the_phone_and_belong_to_the_apps_app(tools, reg):
    import inspect

    from core import core_runtime

    names = {"list_my_apps", "describe_app", "which_app", "check_my_apps"}
    assert names <= set(tools._actions)
    assert "register_app_registry_actions(registry)" in inspect.getsource(core_runtime._register_core_assistant_actions)
    assert {reg.owner_of(n) for n in names} == {"module_browser"}
    assert {a.name for a in tools.matching_actions("Is anything wrong with my apps?")} >= names


def test_the_apps_page_carries_the_checked_section(tools):
    import json
    from pathlib import Path

    from core.web_surfaces import _registry_section

    section = _registry_section(_context(tools))
    assert section["manifests"] == len(app_ecosystem.registry().manifests)
    assert section["health"] == [] and set(section) >= {"apps", "devices", "voice", "overlaps", "gaps"}
    example = json.loads((Path(__file__).resolve().parent.parent / "docs" / "schema" / "apps.example.json")
                         .read_text(encoding="utf-8"))
    assert set(example["registry"]) == set(section)
