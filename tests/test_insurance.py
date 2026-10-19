"""
The insurance check-up (core/insurance.py, DEC-0034): policies, what's
worth a look, a policy's PDF read into the form, quotes side by side (a
cheaper quote that covers less says so), the drafted quote request, and
switching (a mission, then the policy becomes the quote and the saving is
recorded). Placeholder data only.
"""

from datetime import date

import pytest

from core.insurance import (InsuranceBook, annual, checks, compare, insurance_page, parse_coverage, read_policy,
                            renewal_notes)
from tests.engine_world import build_world

TODAY = date(2026, 10, 19)
CAR_COVER = "Bodily injury: 100,000/300,000\nProperty damage: 100,000\nCollision: $500 deductible\nComprehensive: included"


@pytest.fixture
def world(tmp_path, monkeypatch):
    from core.actions import ActionCenter

    w = build_world(tmp_path, monkeypatch)
    w.insurance = InsuranceBook(w, data_dir=w.home_dir)
    w.actions = ActionCenter()
    return w


def _car(w, **more):
    values = dict(premium=600.0, every="6 Months", renews="2026-11-20", deductible=500.0, coverage=CAR_COVER,
                  last_premium=520.0)
    values.update(more)
    return w.insurance.add_policy("Car", "Placeholder Mutual", **values)


def test_amounts_and_coverage_lines():
    assert annual(600, "6 Months") == 1200 and annual(50, "Month") == 600
    lines = parse_coverage(CAR_COVER + "\nRental: none\n100/300 Uninsured motorist")
    by = {c["key"]: c for c in lines}
    assert by["bodily injury"]["amounts"] == [100000, 300000]
    assert by["rental reimbursement"]["included"] is False
    assert parse_coverage("BI: 100/300")[0]["key"] == "bodily injury"
    assert parse_coverage("BI: 100/300")[0]["amounts"] == [100000, 300000]  # policies write thousands


def test_whats_worth_a_look(world):
    truck = world.maintenance.add_asset("2009 Placeholder Pickup", "Vehicle") if hasattr(world.maintenance, "add_asset") else None
    car = _car(world, asset_id=truck.asset_id if truck else "")
    world.insurance.add_policy("Renters", "Other Insurer Co", premium=15, every="Month")
    said = " ".join(c["text"] for c in checks(world, car, world.insurance.policies, TODAY))
    assert "Renews in 32 days" in said and "Up 15%" in said
    assert "bundle" in said and "deductible" in said
    if truck:
        assert "2009 vehicle" in said


def test_quotes_side_by_side_never_hide_less_coverage(world):
    car = _car(world)
    same = world.insurance.add_quote(car.policy_id, "Cheaper Same", premium=500, coverage=CAR_COVER, deductible=500)
    less = world.insurance.add_quote(car.policy_id, "Cheapest Less", premium=400, deductible=1000,
                                     coverage="Bodily injury: 50,000/100,000\nProperty damage: 100,000\nCollision: $1,000")
    got = compare(car, world.insurance.quotes_for(car.policy_id))
    first, second = got["quotes"]
    assert first["id"] == same.quote_id and first["same_coverage"] and first["saves"] == 200
    assert second["id"] == less.quote_id and second["saves"] == 400
    said = "; ".join(second["covers_less"])
    assert "lower Bodily injury" in said and "no Comprehensive" in said and "higher deductible" in said
    assert got["best"] == same.quote_id and got["best_saves"] == 200  # the cheapest isn't the best: it covers less


def test_reading_a_declarations_page():
    text = """PLACEHOLDER MUTUAL AUTO POLICY DECLARATIONS  Policy Number: PM-1234567
    Policy Period: 05/20/2026 to 11/20/2026   Total 6-Month Premium: $612.40
    Bodily Injury $100,000/$300,000   Property Damage $100,000   Collision Deductible $500
    Comprehensive $250"""
    got = read_policy(text.replace("PLACEHOLDER MUTUAL", "Progressive"))
    assert got["insurer"] == "Progressive" and got["kind"] == "Car"
    assert got["premium"] == 612.40 and got["every"] == "6 Months" and got["renews"] == "2026-11-20"
    assert got["deductible"] == 500 and got["policy_number"] == "PM-1234567"
    assert "Bodily Injury: $100,000/$300,000" in got["coverage"]
    assert read_policy("nothing useful here") == {}


def test_renewal_heads_up_once(world):
    car = _car(world)
    notes = renewal_notes(world, TODAY)
    assert len(notes) == 1 and "renews in 32 days" in notes[0][0] and "went up 15%" in notes[0][1]
    assert world.insurance.note_given(notes[0][2]) and not world.insurance.note_given(notes[0][2])
    world.insurance.update_policy(car.policy_id, renews="2027-06-01")
    assert renewal_notes(world, TODAY) == []


def test_actions_request_choose_switch(world):
    from core import life_events

    world.email_drafts = type("Drafts", (), {"made": [], "create": lambda self, to, s, b: self.made.append((to, s, b))})()
    p = world.actions.propose(world, "insurance_policy.add", {"kind": "Car", "insurer": "Placeholder Mutual", "premium": "600",
                                                     "every": "6 Months", "coverage": CAR_COVER, "agent_email": "agent@example.com"})
    assert "Add the policy" in p.summary
    world.actions.approve(world, p.proposal_id)
    car = world.insurance.policies[0]
    assert car.name == "Car insurance"

    p = world.actions.propose(world, "insurance.request", {"policy_id": car.policy_id})
    assert "agent@example.com" in p.summary and "You press Send" in p.summary
    world.actions.approve(world, p.proposal_id)
    to, subject, body = world.email_drafts.made[0]
    assert to == ["agent@example.com"] and "Bodily injury: 100,000/300,000" in body and subject.startswith("Quote request")

    p = world.actions.propose(world, "insurance_quote.add", {"policy_id": car.policy_id, "insurer": "Cheaper Same", "premium": "500",
                                                   "every": "6 Months", "coverage": CAR_COVER})
    world.actions.approve(world, p.proposal_id)
    quote = world.insurance.quotes[0]
    p = world.actions.propose(world, "insurance.choose", {"quote_id": quote.quote_id})
    assert "saving $200.00 a year" in p.summary
    world.actions.approve(world, p.proposal_id)
    mission = next(m for m in world.missions.all_missions() if "Switch car insurance" in m.name)
    assert len(mission.objectives) == 5 and world.insurance.get_policy(car.policy_id).chosen_quote_id == quote.quote_id

    p = world.actions.propose(world, "insurance.switched", {"quote_id": quote.quote_id})
    world.actions.approve(world, p.proposal_id)
    car = world.insurance.get_policy(car.policy_id)
    assert car.insurer == "Cheaper Same" and car.premium == 500 and car.last_premium == 600 and not world.insurance.quotes
    won = [e for e in life_events.events_for(world) if e.type == "insurance_switched"]
    assert won and "saves $200.00 a year" in won[0].summary


def test_the_page(world):
    _car(world)
    page = insurance_page(world, TODAY)
    assert page["available"] and page["summary"]["policies"] == 1 and page["summary"]["per_year"] == 1200
    assert page["summary"]["renewing_soon"] == 1 and page["policies"][0]["checklist"]
    assert {f["name"] for f in page["forms"]["quote"]["fields"]} >= {"policy_id", "insurer", "premium", "coverage"}


def test_grown_ups_only(world):
    from core.child_accounts import CHILD_APPS

    assert "insurance" not in CHILD_APPS
