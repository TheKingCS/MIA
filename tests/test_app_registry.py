"""
tests.test_app_registry
=========================

The Application Registry (DEC-0175, DEC-0178, migration phase M1; core/app_registry.py, apps/*/manifest.json): every
MIA-native app has one manifest that matches the published schema; together the manifests claim every tool, action
kind, store, job and daily check in the code exactly once, and name nothing that isn't there; since M3 the app list
(core/web_surfaces.APPS, RETIRED) is read from the manifests in their order; its queries answer from the manifests; a
manifest that can't be read or names itself wrongly is a problem, not a crash; two apps can't share a sidebar place;
and the generator never overwrites manifests unless forced, and then keeps what only a person writes.
"""

import json

import pytest

from core import app_registry, schema_check


@pytest.fixture(scope="module")
def registry():
    """The registry as the repository's manifests make it."""
    return app_registry.load()


def test_every_manifest_matches_the_published_schema(registry):
    schema = schema_check.load("app_manifest.schema.json")
    bad = {i: schema_check.errors(m, schema) for i, m in registry.manifests.items()}
    assert {i: e for i, e in bad.items() if e} == {}


def test_the_manifests_claim_everything_in_the_code_exactly_once_and_nothing_that_isnt_there(registry):
    assert registry.problems() == []


def test_the_app_list_is_read_from_the_manifests_in_their_order(registry):
    from core.web_surfaces import APPS, RETIRED

    ordered = sorted((m for i, m in registry.manifests.items() if i != "mia"), key=lambda m: m["order"])
    assert [a.module_id for a in APPS] == [m["id"] for m in ordered]
    assert APPS[0].module_id == "web_home"
    for app in APPS:
        m = registry.get(app.module_id)
        assert (app.name, app.icon, app.tagline, app.description, app.group, app.ask) == (
            m["name"], m["icon"], m["tagline"], m["description"], m["group"], m["ask"])
        assert app.domains == tuple(m["domains"]) and (app.page or None) == (m["components"]["interface"]["web"] or [None])[0]
    assert RETIRED == {m["id"] for m in ordered if m["retired"]}


def test_the_phone_app_carries_the_manifests_it_reads_its_app_list_from():
    from pathlib import Path

    gradle = Path(__file__).resolve().parent.parent / "android-phone" / "app" / "build.gradle.kts"
    assert '"apps/*/manifest.json"' in gradle.read_text(encoding="utf-8")


def test_two_apps_cant_share_a_sidebar_place(registry):
    twin = dict(registry.get("greenhouse"), order=registry.get("kitchen")["order"])
    doubled = app_registry.Registry(manifests={**registry.manifests, "greenhouse": twin})
    assert any("share the sidebar place" in p for p in doubled.problems())


def test_the_queries_answer_from_the_manifests(registry):
    assert registry.owner_of("world_watch.add") == "world_intel" and registry.owner_of("watch_for") == "world_intel"
    assert "requirement.add" in registry.capabilities_of("world_intel")["actions"]
    assert "world_intel" in registry.on_device("glasses")
    assert all(m["id"] != "mia" for m in registry.apps())
    assert not any(m["retired"] for m in registry.apps()) and any(m["retired"] for m in registry.apps(True))
    assert registry.dependents_of("world_intel") == []


def test_a_bad_manifest_is_a_problem_not_a_crash(tmp_path):
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "manifest.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "liar").mkdir()
    (tmp_path / "liar" / "manifest.json").write_text(json.dumps({
        "manifest_version": 1, "id": "someone_else", "name": "x", "version": "1.0.0", "entry": "voice",
        "components": {}, "capabilities": {}, "runtime": {}}), encoding="utf-8")
    (tmp_path / "thin").mkdir()
    (tmp_path / "thin" / "manifest.json").write_text(json.dumps({"id": "thin"}), encoding="utf-8")
    reg = app_registry.load(tmp_path)
    assert reg.manifests == {}
    assert any("can't be read" in p for p in reg.load_problems)
    assert any("says id someone_else" in p for p in reg.load_problems)
    assert any("lacks" in p for p in reg.load_problems)


def test_the_generator_never_overwrites_manifests_unless_forced(tmp_path):
    from tools import app_manifests

    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        app_manifests.write(folder=tmp_path)
    assert (tmp_path / "x" / "manifest.json").read_text(encoding="utf-8") == "{}"


def test_regenerating_keeps_what_only_a_person_writes(tmp_path):
    from tools import app_manifests

    target = tmp_path / "manifest.json"
    target.write_text(json.dumps({"version": "2.1.0", "permissions": ["network:feeds"], "x-note": "kept",
                                  "components": {"services": ["core/world_intel.py"]}}), encoding="utf-8")
    fresh = {"version": "1.0.0", "permissions": [], "components": {"services": [], "data": ["a"]}}
    kept = app_manifests._keep_hand_fields(fresh, target)
    assert kept["version"] == "2.1.0" and kept["permissions"] == ["network:feeds"] and kept["x-note"] == "kept"
    assert kept["components"] == {"services": ["core/world_intel.py"], "data": ["a"]}
    assert app_manifests._keep_hand_fields({"v": 1}, tmp_path / "none.json") == {"v": 1}


def test_regenerating_keeps_a_decided_tier_and_gives_a_new_capability_the_rules(tmp_path):
    from tools import app_manifests

    target = tmp_path / "manifest.json"
    target.write_text(json.dumps({"permissions": ["network:feeds", "stores.write:gone"], "capabilities": {
        "tiers": {"old_tool": "never", "dropped_tool": "observe"}, "outside": ["old_tool", "dropped_tool"]}}),
        encoding="utf-8")
    fresh = {"permissions": ["stores.write:kept"], "components": {},
             "capabilities": {"tools": ["old_tool", "new_tool"], "actions": [],
                              "tiers": {"old_tool": "act_within_grant", "new_tool": "observe"}, "outside": []}}
    kept = app_manifests._keep_hand_fields(fresh, target)
    assert kept["capabilities"]["tiers"] == {"old_tool": "never", "new_tool": "observe"}
    assert kept["capabilities"]["outside"] == ["old_tool"]
    assert kept["permissions"] == ["network:feeds", "stores.write:kept"]  # a store's permission follows the code
