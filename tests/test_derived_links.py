"""
tests.test_derived_links
==========================

The ties the stores' own fields already say, made into derived links (core/links.py, 2026-11-08, for
core/connections.py's `connections.unlinked`): a mission is part of its project and trip, a skill builds on its
prerequisites, a trip is part of its expedition, a job uses its workshop recipe, a recipe uses the materials its
lines name, a policy is related to the asset it covers, a project is related to the skills it trains. And the
point of it: a remark about a skill now ties to a project weeks old that trains it. None of them is a waiting word,
so the Life State's "what waits on what" stays the person's own.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace as N

from core import connections as cx
from core import links
from core.gamification import SkillWeight

OLD = (datetime(2026, 11, 8) - timedelta(days=21)).isoformat(timespec="seconds")


def _ctx(**stores):
    """A context with just the stores named, each listing its records the way links reads them."""
    listers = {"missions": "all_missions", "skills": "all_skills", "trips": "all_trips", "jobs": "all_jobs",
               "products": "all_products", "insurance": "policies", "projects": "all_projects",
               "craft_recipes": "all_recipes", "materials": "all_materials"}
    return N(**{name: N(**{listers[name]: (lambda rows=rows: list(rows))}) for name, rows in stores.items()})


def _derived(ctx) -> set:
    """The derived links as (source, relation, target) triples."""
    return {(l.source, l.relation, l.target) for l in links.derived_links(ctx)}


def test_the_fields_already_say_these_ties():
    ctx = _ctx(
        missions=[N(mission_id="m1", status="active", project_id="p1", trip_id="t1", task_id="x9", skill_rewards=[])],
        skills=[N(skill_id="s2", name="Joinery", prerequisite_skill_ids=["s1"])],
        trips=[N(trip_id="t1", name="Creek", expedition_id="e1")],
        jobs=[N(job_id="j1", name="Run", recipe_id="r1")],
        insurance=[N(policy_id="pol1", insurer="Acme", asset_id="a1")],
        projects=[N(project_id="p1", name="Bookshelf", intent_id=None, skill_weights=[SkillWeight("s1", 50)])],
    )
    found = _derived(ctx)
    assert {("mission:m1", "PART_OF", "project:p1"), ("mission:m1", "PART_OF", "trip:t1"),
            ("skill:s2", "BUILDS_ON", "skill:s1"), ("trip:t1", "PART_OF", "expedition:e1"),
            ("job:j1", "USES", "craft_recipe:r1"), ("policy:pol1", "RELATED_TO", "asset:a1"),
            ("project:p1", "RELATED_TO", "skill:s1")} <= found
    assert not any("x9" in t for _, _, t in found)  # a mission's task_id doesn't say which kind of task: left out


def test_a_workshop_recipe_uses_the_materials_its_lines_name():
    from core.craft_recipes import CraftRecipe

    recipe = CraftRecipe(recipe_id="r1", name="Bird feeder", materials="2 board cedar\nWood glue\n4 screw brass")
    ctx = _ctx(craft_recipes=[recipe],
               materials=[N(material_id="mat1", name="Cedar"), N(material_id="mat2", name="Wood glue")])
    found = _derived(ctx)
    assert ("craft_recipe:r1", "USES", "material:mat1") in found
    assert ("craft_recipe:r1", "USES", "material:mat2") in found
    assert not any(t.startswith("material:") and "brass" in t for _, _, t in found)  # not in stock: no link


def test_a_remark_about_a_skill_now_ties_to_the_project_that_trains_it():
    ctx = _ctx(skills=[N(skill_id="s1", name="Carpentry", prerequisite_skill_ids=[])],
               projects=[N(project_id="p1", name="Bookshelf", status="Planning", description="", intent_id=None,
                           created_at=OLD, skill_weights=[SkillWeight("s1", 50)])])
    found = cx.find(ctx, "I've been practising carpentry every night", date(2026, 11, 8))
    assert found and found[0]["ref"] == "project:p1" and found[0]["via"] == "link" and found[0]["through"] == "Carpentry"


def test_derived_links_never_use_the_waiting_words():
    """REQUIRES, DEPENDS_ON and BLOCKED_BY are the person's stated "what waits on what" (the Life State's chains)."""
    from core.craft_recipes import CraftRecipe

    ctx = _ctx(skills=[N(skill_id="s2", name="Joinery", prerequisite_skill_ids=["s1"])],
               jobs=[N(job_id="j1", name="Run", recipe_id="r1")],
               craft_recipes=[CraftRecipe(recipe_id="r1", name="Feeder", materials="2 board cedar")],
               materials=[N(material_id="mat1", name="Cedar")])
    assert not {r for _, r, _ in _derived(ctx)} & {"REQUIRES", "DEPENDS_ON", "BLOCKED_BY"}
