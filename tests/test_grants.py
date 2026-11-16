"""
tests.test_grants
===================

Tiers, grants and the grant check (DEC-0156, approved; migration phase M4; core/grants.py): every tool and
action kind has a tier in its app's manifest; the kinds that always ask are tiered at the person's yes, so there is
one classification; a person's own press is always theirs; on MIA's own initiative reading and drafting are allowed,
a change needs a grant, and paying, sending or deleting needs the person's yes whatever was granted; the tools that
carry outside text are tagged and are exactly the ones the model's handling knows; the check is enforced where her
initiative reaches a change (a skill's step asks until the skill is learned, a learned one still asks to pay and
never does what's never hers); a learned skill and a published workflow are the grants, listed and taken back; nothing
gives a grant but earning or approving it; and the registry refuses a capability without a tier.
"""

import pytest

from core import app_registry, grants
from core.grants import MIA, NEVER, OBSERVE, PERSON, SUGGEST, WITH_APPROVAL, WITHIN_GRANT


@pytest.fixture(scope="module")
def registry():
    """The registry as the repository's manifests make it."""
    return app_registry.load()


def test_every_tool_and_action_kind_has_a_tier(registry):
    from core import parity
    from core.actions import ACTION_TYPES

    tiers = {}
    for m in registry.manifests.values():
        tiers.update(m["capabilities"]["tiers"])
    assert set(tiers) == set(parity.desktop_registry()._actions) | set(ACTION_TYPES)
    assert set(tiers.values()) <= set(grants.TIERS)
    assert grants.tier_of("bill.pay") == WITH_APPROVAL and grants.tier_of("list_watches") == OBSERVE
    assert grants.tier_of("no.such_thing") is None


def test_the_kinds_that_always_ask_are_the_ones_tiered_at_the_persons_yes(registry):
    from core.actions import ACTION_TYPES
    from core.taught_skills import always_asks

    for kind in ACTION_TYPES:
        if always_asks(kind):
            assert grants.tier_of(kind) in (WITH_APPROVAL, NEVER), kind
    assert grants.default_action_tier("quote.send") == WITH_APPROVAL
    assert grants.default_action_tier("grocery.add") == WITHIN_GRANT


def test_a_tool_starts_at_the_tier_its_name_and_marks_earn():
    assert grants.default_tool_tier("list_bills") == OBSERVE
    assert grants.default_tool_tier("plan_meal") == SUGGEST
    assert grants.default_tool_tier("add_grocery_item") == WITHIN_GRANT
    assert grants.default_tool_tier("delete_note") == WITH_APPROVAL
    assert grants.default_tool_tier("tidy_things", destructive=True) == WITH_APPROVAL
    assert grants.tier_of("draft_email") == SUGGEST  # it only drafts; a person presses Send


def test_a_persons_own_press_is_always_theirs_and_mias_initiative_goes_by_the_tier():
    for tier in grants.TIERS + (None,):
        assert grants.decide(tier, PERSON).allowed
    assert grants.decide(OBSERVE, MIA).allowed and grants.decide(SUGGEST, MIA).allowed
    assert not grants.decide(WITHIN_GRANT, MIA).allowed and grants.decide(WITHIN_GRANT, MIA, granted=True).allowed
    assert not grants.decide(WITH_APPROVAL, MIA, granted=True).allowed  # a grant never covers paying or deleting
    assert not grants.decide(NEVER, MIA, granted=True).allowed
    unknown = grants.decide(None, MIA, granted=True)
    assert not unknown.allowed and unknown.tier == WITH_APPROVAL  # an untagged capability is treated as the strictest


def test_tools_that_carry_outside_text_are_tagged_and_handled_for_the_model(registry):
    from core.tool_loop import OUTSIDE_TOOLS

    tagged = {n for m in registry.manifests.values() for n in m["capabilities"]["outside"]}
    assert tagged == OUTSIDE_TOOLS | grants.FRAMED_TOOLS
    assert {"list_inbox", "world_finds", "browser_read", "look_up_online"} <= tagged


def test_no_tool_reads_outside_sources_without_being_tagged(registry):
    """A sweep by each tool's own code: one that calls the web search, the browser's page text or the mail must be
    tagged as outside text, or be listed here with why it isn't."""
    import inspect

    from core import parity

    not_outside = {
        "learn_browser_task": "starts a recording; says nothing a page wrote",
        "list_browser_tasks": "the person's own taught tasks",
        "browser_close": "closes the window; says nothing a page wrote",
    }
    tagged = {n for m in registry.manifests.values() for n in m["capabilities"]["outside"]}
    missed = []
    for name, tool in parity.desktop_registry()._actions.items():
        try:
            source = inspect.getsource(tool.handler)
        except (OSError, TypeError):
            source = ""
        reads_outside = any(mark in source for mark in ("untrusted(", "online_lookup.", "world_page("))
        if (reads_outside or tool.domain == "browser") and name not in tagged and name not in not_outside:
            if name == "list_watches":  # reads the page's data for the watches (the person's own names), not the finds
                continue
            missed.append(name)
    assert missed == []


def _skill_context(tmp_path):
    """A context with a skill book, a kind that changes a record (zz.note) and one that pays (zz.pay)."""
    from types import SimpleNamespace

    from core.taught_skills import SkillBook

    context = SimpleNamespace(assistant_actions=None, actions=None, creations=None)
    context.taught_skills = SkillBook(context, data_dir=tmp_path)
    return context


@pytest.fixture
def kinds(monkeypatch):
    """Two stand-in action kinds with tiers: zz.note (within a grant) and zz.pay (the person's yes); `ran` counts."""
    from core import actions

    ran = []
    for kind, tier in (("zz.note", WITHIN_GRANT), ("zz.pay", WITH_APPROVAL), ("zz.sign", NEVER)):
        monkeypatch.setitem(actions.ACTION_TYPES, kind, actions.ActionType(
            kind, kind, {}, lambda c, p, k=kind: f"Do {k}", lambda c, p, k=kind: ran.append(k) or f"Did {k}."))
        monkeypatch.setitem(grants.tiers(), kind, tier)
    monkeypatch.setattr(grants, "_would_refuse", {})
    return ran


def test_the_check_holds_mias_initiative_and_never_the_persons(kinds):
    from core import actions, taught_skills

    assert actions.run_as_tool(None, "zz.pay", {}) == "Did zz.pay."  # the person asked: theirs to do
    for standing, kind, runs in ((False, "zz.note", False), (True, "zz.note", True), (True, "zz.pay", False),
                                 (True, "zz.sign", False)):
        held = {"blocked": None, "standing": standing}
        token = taught_skills._UNAPPROVED.set(held)
        try:
            said = actions.run_as_tool(None, kind, {})
        finally:
            taught_skills._UNAPPROVED.reset(token)
        assert (said == f"Did {kind}.") is runs and (held["blocked"] is None) is runs, (standing, kind)
    assert grants.report() == {"zz.note": 1, "zz.pay": 1, "zz.sign": 1}


def test_a_skill_asks_before_each_change_until_it_is_learned_and_its_grant_can_be_taken_back(tmp_path, kinds):
    from core import grant_actions, taught_skills  # noqa: F401  (the take-back kind registers on import)
    from core.actions import ACTION_TYPES

    context = _skill_context(tmp_path)
    skill = context.taught_skills.add("Friday reset", [{"kind": "action", "action": "zz.note", "params": {}}])
    assert grants.standing(context) == []
    for _ in range(taught_skills.CLEAN_RUNS):  # practising: it asks, the person says yes
        assert taught_skills.start(context, skill.skill_id)["status"] == "waiting"
        assert taught_skills.answer(context, "yes")["status"] == "done"
    assert skill.state == taught_skills.LEARNED
    [grant] = grants.standing(context)
    assert grant.grant_id == f"skill:{skill.skill_id}" and grant.kind == "skill" and "1 step" in grant.covers
    assert taught_skills.start(context, skill.skill_id, watched=False)["status"] == "done"  # learned: no asking
    take = ACTION_TYPES["grant.take_back"]
    assert "back to practising with you" in take.describe(context, {"grant": "friday reset"})
    assert "back to practising" in take.execute(context, {"grant_id": grant.grant_id})
    assert grants.standing(context) == [] and skill.state == taught_skills.PRACTISING and skill.clean_runs == 0
    assert taught_skills.start(context, skill.skill_id)["status"] == "waiting"  # it asks again
    with pytest.raises(ValueError):
        take.execute(context, {"grant_id": grant.grant_id})


def test_a_learned_skill_still_asks_for_what_needs_a_yes_and_never_does_what_is_never_hers(tmp_path, kinds):
    from core import taught_skills

    context = _skill_context(tmp_path)
    pay = context.taught_skills.add("Pay it", [{"kind": "action", "action": "zz.pay", "params": {}}])
    sign = context.taught_skills.add("Sign it", [{"kind": "action", "action": "zz.sign", "params": {}}])
    pay.state = sign.state = taught_skills.LEARNED
    assert taught_skills.start(context, pay.skill_id)["status"] == "waiting" and kinds == []
    assert taught_skills.answer(context, "yes")["status"] == "done" and kinds == ["zz.pay"]
    stopped = taught_skills.start(context, sign.skill_id)
    assert stopped["status"] == "stopped" and "only ever done by you" in " ".join(stopped["said"]) and kinds == ["zz.pay"]


def test_a_published_workflow_is_a_grant_listed_with_what_it_may_do_and_put_away_when_taken_back(tmp_path):
    from types import SimpleNamespace

    retired = []
    spec = {"kind": "workflow", "limits": {"adds_per_run": 2},
            "steps": [{"step": "tell", "text": "x"}, {"step": "add", "to": "creation:C-0001", "values": {}}]}
    store = SimpleNamespace(published=lambda: [{"id": "C-0002", "title": "Weekly tally"}, {"id": "C-0001", "title": "A screen"}],
                            shown=lambda i: {"spec": spec if i == "C-0002" else {"kind": "screen"}},
                            retire=lambda i: retired.append(i))
    context = SimpleNamespace(taught_skills=None, creations=store)
    [grant] = grants.standing(context)
    assert grant.grant_id == "workflow:C-0002" and "add up to 2 record(s) a run to C-0001" in grant.covers
    assert grants.find(context, "weekly") == grant and grants.find(context, "nothing like it") is None
    assert "put away" in grants.take_back(context, grant.grant_id) and retired == ["C-0002"]


def test_nothing_gives_a_grant_but_earning_or_approving_it():
    """No action kind and no tool gives a grant (DEC-0156: untrusted text can never grant)."""
    from core import parity
    from core.actions import ACTION_TYPES

    assert [k for k in ACTION_TYPES if k.startswith("grant.")] == ["grant.take_back"]
    names = [n for n in parity.desktop_registry()._actions if "grant" in n]
    assert sorted(names) == ["list_grants", "take_back_grant"]
    assert grants.tier_of("grant.take_back") == WITH_APPROVAL and grants.tier_of("take_back_grant") == WITH_APPROVAL


def test_the_registry_refuses_a_capability_without_a_tier_or_below_what_it_must_be(registry):
    m = registry.get("budget")
    caps = dict(m["capabilities"], tiers={k: v for k, v in m["capabilities"]["tiers"].items() if k != "bill.pay"})
    untiered = app_registry.Registry(manifests={**registry.manifests, "budget": dict(m, capabilities=caps)})
    assert any("bill.pay has no tier" in p for p in app_registry._tier_problems(untiered.manifests))
    caps = dict(m["capabilities"], tiers=dict(m["capabilities"]["tiers"], **{"bill.pay": WITHIN_GRANT}))
    lowered = app_registry.Registry(manifests={**registry.manifests, "budget": dict(m, capabilities=caps)})
    assert any("bill.pay always asks" in p for p in app_registry._tier_problems(lowered.manifests))
    caps = dict(m["capabilities"], outside=["list_bills"])
    stray = app_registry.Registry(manifests={**registry.manifests, "budget": dict(m, capabilities=caps)})
    assert any("list_bills carries outside text" in p for p in app_registry._tier_problems(stray.manifests))
