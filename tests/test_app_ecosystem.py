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


@pytest.fixture(autouse=True)
def no_recovered_files(monkeypatch, tmp_path):
    """Each test starts with no record of reset stores: another test in the run may have reset one on purpose."""
    from core import dev_store

    monkeypatch.setattr(dev_store, "DEV_DATA", tmp_path / "dev")


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


def test_a_record_that_couldnt_be_loaded_is_pinned_on_its_app_without_rebuilding_her_tools(monkeypatch):
    """Fable's review (DEC-0174): the running check rebuilt the PC's whole tool list each time, which a phone or a
    runtime without a window can't do; comparing records with the code is the tests' job."""
    def never():
        raise AssertionError("the running check must not rebuild the tool list")

    monkeypatch.setattr(parity, "desktop_registry", never)
    broken = app_registry.Registry(manifests=dict(app_ecosystem.registry().manifests),
                                   load_problems=["greenhouse: its manifest can't be read (ValueError)",
                                                  "zeppelin: its manifest lacks id"])
    found = app_ecosystem.health(broken, SimpleNamespace(scheduler=None))
    assert found == {"greenhouse": ["greenhouse: its manifest can't be read (ValueError)"],
                     "zeppelin": ["zeppelin: its manifest lacks id"]}
    assert "Wrong now" in app_ecosystem.check_sentence(broken, SimpleNamespace(scheduler=None, assistant_actions=None,
                                                                              data_dir=None))


def test_overlaps_are_between_different_apps_and_said_as_suggestions(reg, tools):
    ctx = _context(tools)
    for o in app_ecosystem.overlaps(reg, ctx):
        assert o["apps"][0] != o["apps"][1] and o["alike"] >= app_ecosystem.OVERLAP
    said = app_ecosystem.check_sentence(reg, ctx)
    assert said.startswith("Every app's record loaded")
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


def _job(name, n, error=""):
    """A scheduler record for one job failing `n` times in a row."""
    return {"name": name, "failures_in_a_row": n, "last_error": error}


def test_each_app_has_a_status_from_its_jobs_its_breakages_and_its_stores(reg, tools, monkeypatch):
    """M5: failing (a job backing off), needs attention (a job failed once, something broke this week, a store was
    reset), hidden, working; each with why, and never from the model."""
    greenhouse_job = reg.get("greenhouse")["runtime"]["background"][0]
    world_job = reg.get("world_intel")["runtime"]["background"][0]
    issues = [{"status": "open", "kinds": ["tool_error"], "title": "record_price broke", "count": 2,
               "examples": [{"tool": "record_price"}]},
              {"status": "open", "kinds": ["page_error"], "title": "the Kitchen page broke", "count": 1,
               "examples": [{"page": "/web/kitchen.html#plan"}]},
              {"status": "fixed", "kinds": ["tool_error"], "title": "old", "count": 9, "examples": [{"tool": "list_bills"}]}]
    ctx = SimpleNamespace(assistant_actions=tools, scheduler=SimpleNamespace(
        status=lambda: [_job(greenhouse_job, 3, "timed out"), _job(world_job, 1)]),
        failures=SimpleNamespace(issues=lambda days: issues))
    monkeypatch.setattr(app_ecosystem, "_recovered", lambda r, now=None: {"notes": ["its notes couldn't be read and started empty"]})
    monkeypatch.setattr(app_ecosystem, "_hidden", lambda c: {"music"})
    s = app_ecosystem.statuses(reg, ctx)
    assert s["greenhouse"]["status"] == "failing" and "timed out" in s["greenhouse"]["why"][0]
    assert s["world_intel"]["status"] == "needs_attention"  # its job once, and record_price broke this week
    assert any("record_price broke (2 times this week)" == w for w in s["world_intel"]["why"])
    assert s["kitchen"]["status"] == "needs_attention" and s["notes"]["status"] == "needs_attention"
    assert s["budget"]["status"] == "working"  # its breakage is marked fixed
    assert s["music"]["status"] == "hidden" and s["maintenance"]["status"] == "retired"
    assert set(app_ecosystem.health(reg, ctx)) == {"greenhouse", "world_intel", "kitchen", "notes"}
    said = app_ecosystem.details_sentence(reg, "Greenhouse", ctx)
    assert "Right now it's failing: its job" in said


def test_an_app_whose_dependency_is_gone_says_so(reg):
    m = dict(reg.get("greenhouse"), dependencies=[{"application_id": "zeppelin"}])
    broken = app_registry.Registry(manifests={**reg.manifests, "greenhouse": m})
    s = app_ecosystem.statuses(broken, SimpleNamespace(scheduler=None, failures=None))
    assert s["greenhouse"] == {"status": "missing_dependency", "why": ["it needs zeppelin, which isn't here"]}


def test_a_stores_reset_is_pinned_on_the_app_that_owns_it(reg, monkeypatch, tmp_path):
    from core import dev_store

    monkeypatch.setattr(dev_store, "DEV_DATA", tmp_path)
    dev_store.DevStore(tmp_path / "recovered").append({"file": "world_intel.json"})
    dev_store.DevStore(tmp_path / "recovered").append({"file": "not_a_store.json"})
    assert app_ecosystem._recovered(reg) == {"world_intel": ["its world intel couldn't be read and started empty"]}


def test_the_apps_page_shows_each_apps_status():
    import json
    from pathlib import Path

    example = json.loads((Path(__file__).resolve().parent.parent / "docs" / "schema" / "apps.example.json")
                         .read_text(encoding="utf-8"))
    apps = [a for g in example["groups"] for a in g["apps"]]
    assert all(a["status"] in app_ecosystem.STATUSES for a in apps) and all("status_why" in a for a in apps)
    js = (Path(__file__).resolve().parent.parent / "web" / "apps.js").read_text(encoding="utf-8")
    assert "statusChip(app)" in js and "needs_attention" in js
