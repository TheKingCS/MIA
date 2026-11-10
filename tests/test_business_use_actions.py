"""
tests.test_business_use_actions
=================================

Business use of a tool on its asset page (core/business_use_actions.py, 2026-11-09): Log Use and Remove go through
the action contract (refused without an amount, a real tool or a real day), the page shows this year's figures and
jobs once something is logged and only the form before, and the life state counts the tools and jobs.
"""

from datetime import date

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.business_use import BusinessUseManager
from core.business_use_actions import page_section
from tests.engine_world import build_world

TODAY = date(2026, 11, 9)


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The test world with a business-use log and a mower."""
    context = build_world(tmp_path, monkeypatch)
    context.business_use = BusinessUseManager(context, data_dir=context.home_dir)
    context.mower = context.maintenance.add_asset("Riding mower", category="Power Equipment")
    return context


def _log(world, **params):
    """Runs asset.business_use_log for the mower (describe, then execute, as approving does)."""
    kind = ACTION_TYPES["asset.business_use_log"]
    params = {"asset_id": world.mower.asset_id, **params}
    kind.describe(world, params)
    return kind.execute(world, params)


def test_log_use_is_refused_without_an_amount_a_tool_or_a_real_day(world):
    """No hours or miles, a tool that's gone, or a day that isn't one: refused, nothing logged."""
    with pytest.raises(ActionError):
        _log(world, hours="")
    with pytest.raises(ActionError):
        _log(world, asset_id="gone", hours=2)
    with pytest.raises(ActionError):
        _log(world, hours=2, date="next tuesday")
    assert world.business_use.entries_for(world.mower.asset_id) == []


def test_logged_use_shows_on_the_page_and_remove_takes_it_back(world):
    """Before anything is logged the section is only the form; after two jobs it has the figures and the jobs, newest
    first, and Remove takes one off."""
    assert page_section(world, world.mower, TODAY)["logged"] is False
    assert "2026 so far on Riding mower: 2 business hours." in _log(world, hours="2", client="Maple duplex",
                                                                    date="2026-11-02")
    _log(world, hours=1, purpose="personal", date="2026-11-05")
    section = page_section(world, world.mower, TODAY)
    assert section["logged"] and section["unit"] == "hours"
    labels = {f["label"]: f["value"] for f in section["figures"]}
    assert labels["Business use"] == "2 hours"
    assert [j["date"] for j in section["jobs"]] == ["2026-11-05", "2026-11-02"]
    assert section["jobs"][1]["for"] == "Maple duplex"
    ACTION_TYPES["asset.business_use_remove"].execute(world, section["jobs"][0]["remove"]["params"])
    assert len(page_section(world, world.mower, TODAY)["jobs"]) == 1


def test_the_asset_page_and_the_life_state_carry_it(world):
    """The asset page has the section; the life state's business_use area counts the tools and this year's jobs."""
    from core import life_areas
    from core.web_equipment import asset_page

    _log(world, hours=3, date="2026-11-01")
    assert asset_page(world, world.mower.asset_id, TODAY)["business_use"]["logged"] is True
    area = life_areas.areas(world, TODAY)["business_use"]
    assert area["counts"] == {"tools": 1, "jobs_this_year": 1}
