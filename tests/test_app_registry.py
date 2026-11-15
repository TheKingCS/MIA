"""
tests.test_app_registry
=========================

The Application Registry (DEC-0175, DEC-0178, migration phase M1; core/app_registry.py, apps/*/manifest.json): every
MIA-native app has one manifest that matches the published schema; together the manifests claim every tool, action
kind, store, job and daily check in the code exactly once, and name nothing that isn't there; the registry agrees
with today's app list (core/web_surfaces.APPS) until it becomes the source in M3; its queries answer from the
manifests; a manifest that can't be read or names itself wrongly is a problem, not a crash; and the generator never
overwrites manifests that exist unless forced.
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


def test_the_registry_agrees_with_todays_app_list(registry):
    from core.web_surfaces import APPS, RETIRED

    assert set(registry.manifests) == {a.module_id for a in APPS} | {"mia"}
    for app in APPS:
        m = registry.get(app.module_id)
        assert (m["name"], m["icon"], m["retired"]) == (app.name, app.icon, app.module_id in RETIRED)
        assert m["components"]["interface"]["web"] == ([app.page] if app.page else [])


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
