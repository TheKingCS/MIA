"""
tests.test_opportunity
========================

Opportunity scoring and recommendations (Procurement P3, core/opportunity.py; the proposal's section 17 rows it
covers): a find is linked to the right need; every opportunity names all nine dimensions with reasons; a price is
called a saving only when it's verified against prices seen, and "bargain" is never said; the recommendation follows
its rules (skip when owned, ordered, over the ceiling or against a spec; wait when high; buy when ready only with a
verified low and every spec; investigate otherwise); the total cost names its unknown parts; and nothing here can
buy, bid or message anyone.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import opportunity
from core.opportunity import compatibility, recommend
from core.price_book import PriceBook
from core.requirements import RequirementBook
from core.world_intel import Discovery, WorldBook

NOW = datetime(2026, 11, 16, 12, 0)


@pytest.fixture
def world(tmp_path):
    """A greenhouse project needing four 12 V fans (ceiling 60), the price book and World Intelligence's store."""
    from unittest.mock import MagicMock

    project = SimpleNamespace(project_id="p1", name="Greenhouse", status="Active")
    ctx = SimpleNamespace(projects=SimpleNamespace(all_projects=lambda: [project],
                                                   get_project=lambda pid: project if pid == "p1" else None),
                          materials=SimpleNamespace(all_materials=lambda: []),
                          inventory=SimpleNamespace(all_items=lambda: []))
    ctx.requirements = RequirementBook(ctx, data_dir=tmp_path / "needs")
    ctx.prices = PriceBook(ctx, data_dir=tmp_path / "prices")
    ctx.world_intel = WorldBook(MagicMock(), data_dir=tmp_path / "world")
    ctx.need = ctx.requirements.add("p1", "ventilation fan", 4, specs="12 V", max_price=60)
    return ctx


def _find(ctx, title, summary="", need=None, n=[0]):  # noqa: B006 - a counter for ids
    """A find from a source, linked to the need by its refs (as core/relevance.py links it)."""
    n[0] += 1
    d = Discovery(f"d{n[0]}", f"k{n[0]}", title, "https://example.com/item", "market", "Example Market",
                  summary=summary, found_at=NOW.isoformat(), last_seen=NOW.isoformat(), score=2.0,
                  refs=[f"requirement:{(need or ctx.need).requirement_id}"] if need is not False else [])
    ctx.world_intel.discoveries.append(d)
    return d


def _seen(ctx, *prices):
    """Prices seen for the same product in the last few weeks."""
    for i, p in enumerate(prices):
        ctx.prices.record("ventilation fan", "Store", p, specs="12 V",
                          at=(NOW - timedelta(days=5 + i)).isoformat(timespec="seconds"))


def test_a_price_is_read_only_with_a_currency_sign_never_from_a_spec():
    assert opportunity.price_in("Ventilation fan 12V, $45") == 45.0
    assert opportunity.price_in("1200 rpm fan, $1,299.50 shipped") == 1299.5
    assert opportunity.price_in("Ventilation fan 12V 1200 rpm") is None


def test_specs_are_found_in_the_listing_and_a_contradiction_fails():
    assert compatibility("12 V", "Ventilation fan, 12V DC, 1200 rpm")["state"] == "met"
    assert compatibility("12 V, waterproof", "Fan 12 v")["state"] == "partly"
    assert compatibility("12 V, waterproof", "Fan 12 v")["missing"] == ["waterproof"]
    assert compatibility("waterproof", "Fan, not waterproof")["state"] == "failed"
    assert compatibility("", "anything")["state"] == "unstated"


def test_the_recommendation_follows_its_rules_in_order():
    assert recommend(True, False, "met", "low")[0] == "skip"
    assert recommend(False, True, "met", "low")[0] == "skip"
    assert recommend(False, False, "failed", "low")[0] == "skip"
    assert recommend(False, False, "met", "high")[0] == "wait"
    assert recommend(False, False, "met", "low")[0] == "buy_when_ready"
    assert recommend(False, False, "partly", "low")[0] == "investigate"
    assert recommend(False, False, "met", "too_few")[0] == "investigate"
    assert recommend(False, False, "met", "usual")[0] == "investigate"


def test_a_find_is_linked_to_its_need_and_names_all_nine_dimensions_with_reasons(world):
    _find(world, "Ventilation fan 12V, $45", "Brand new")
    _find(world, "Garden gnome $5", need=False)  # meets no need: not an opportunity
    [o] = opportunity.opportunities(world, NOW)
    assert o["need"] == "ventilation fan" and o["project"] == "Greenhouse" and o["source"] == "Example Market"
    names = [d["name"] for d in o["dimensions"]]
    assert names == ["Project relevance", "Price advantage", "Compatibility", "Quality", "Urgency",
                     "Geographic accessibility", "Total cost", "Strategic value", "Confidence"]
    assert all(d["value"] and d["reason"] for d in o["dimensions"])


def test_a_price_is_a_saving_only_when_verified_and_bargain_is_never_said(world):
    _find(world, "Ventilation fan 12V, $45")
    [o] = opportunity.opportunities(world, NOW)
    assert o["recommendation"] == "investigate" and "not yet verified" in o["dimensions"][1]["value"]
    _seen(world, 55, 58, 52)
    [o] = opportunity.opportunities(world, NOW)
    assert o["recommendation"] == "buy_when_ready" and "lowest I've seen" in o["dimensions"][1]["value"]
    said = opportunity.sentence(opportunity.opportunities(world, NOW))
    assert said.startswith("Buy when ready: Ventilation fan") and "bargain" not in said.lower()
    assert "bargain" not in inspect.getsource(opportunity).lower().replace('"bargain" is never said', "")


def test_high_over_the_ceiling_owned_ordered_and_contradicted_finds_are_wait_or_skip(world):
    _seen(world, 30, 32, 31)
    _find(world, "Ventilation fan 12V, $40")
    assert opportunity.opportunities(world, NOW)[0]["recommendation"] == "wait"
    world.world_intel.discoveries.clear()
    _find(world, "Ventilation fan 12V, $75")
    [o] = opportunity.opportunities(world, NOW)
    assert o["recommendation"] == "skip" and "most you said" in o["why"] and "ceiling" in o["dimensions"][1]["reason"]
    world.world_intel.discoveries.clear()
    _find(world, "Ventilation fan, not 12V, $20")
    assert opportunity.opportunities(world, NOW)[0]["recommendation"] == "skip"
    world.world_intel.discoveries.clear()
    _find(world, "Ventilation fan 12V, $20")
    world.requirements.update(world.need.requirement_id, status="ordered")
    assert opportunity.opportunities(world, NOW)[0]["why"].startswith("you already have or ordered")


def test_the_total_cost_names_its_unknown_parts_and_counts_what_is_still_needed(world):
    world.requirements.update(world.need.requirement_id, have=1)
    _find(world, "Ventilation fan 12V, $45")
    [o] = opportunity.opportunities(world, NOW)
    total = o["dimensions"][6]
    assert total["value"].startswith("$135.00") and "unknown shipping, tax" in total["value"]
    assert total["reason"] == "for the 3 still needed"


def test_opportunities_rank_by_recommendation_then_score_and_dismissed_finds_are_left_out(world):
    _seen(world, 55, 58, 52)
    a = _find(world, "Ventilation fan 12V, $45")
    b = _find(world, "Ventilation fan, $50")  # a spec not mentioned: investigate
    c = _find(world, "Ventilation fan 12V, $99")  # over the ceiling: skip
    c.score = 99
    got = [o["discovery_id"] for o in opportunity.opportunities(world, NOW)]
    assert got == [a.discovery_id, b.discovery_id, c.discovery_id]
    b.status = "not_for_me"
    assert b.discovery_id not in [o["discovery_id"] for o in opportunity.opportunities(world, NOW)]


def test_nothing_here_can_buy_bid_or_message_anyone():
    code = inspect.getsource(opportunity).split('"""', 2)[2]
    for reach in ("propose(", "run_as_tool", "browser", "send", "commit", "approve", "urlopen", "requests."):
        assert reach not in code, reach
