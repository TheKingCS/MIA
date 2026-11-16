"""
tests.test_grants
===================

Tiers and the grant check, watching only (DEC-0156, proposed; migration phase M4; core/grants.py): every tool and
action kind has a tier in its app's manifest; the kinds that always ask are tiered at the person's yes, so there is
one classification; a person's own press is always theirs; on MIA's own initiative reading and drafting are allowed,
a change needs a grant, and paying, sending or deleting needs the person's yes whatever was granted; the tools that
carry outside text are tagged and are exactly the ones the model's handling knows; the hook in the action contract
watches, counts and never stops anything; and the registry refuses a capability without a tier.
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


def test_the_hook_in_the_action_contract_watches_counts_and_never_stops_anything(monkeypatch):
    from core import actions, taught_skills

    monkeypatch.setattr(grants, "_would_refuse", {})
    ran = []
    kind = actions.ActionType("zz.pay", "Pay", {}, lambda c, p: "Pay it", lambda c, p: ran.append(1) or "Paid.")
    monkeypatch.setitem(actions.ACTION_TYPES, "zz.pay", kind)
    monkeypatch.setitem(grants.tiers(), "zz.pay", WITH_APPROVAL)
    assert actions.run_as_tool(None, "zz.pay", {}) == "Paid." and grants.report() == {}  # the person asked
    token = taught_skills._UNAPPROVED.set({})
    try:
        said = actions.run_as_tool(None, "zz.pay", {})  # a skill's step, not said yes to: the skill's own guard stops it
    finally:
        taught_skills._UNAPPROVED.reset(token)
    assert said == "That step needs your yes first." and grants.report() == {"zz.pay": 1} and len(ran) == 1
    monkeypatch.setattr(grants, "decide", lambda *a, **k: 1 / 0)
    assert grants.observe("zz.pay", MIA).allowed  # watching that fails never breaks the change


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
