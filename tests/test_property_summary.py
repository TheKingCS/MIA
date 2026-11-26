"""
tests.test_property_summary
=============================

A property's summary over the last 12 months, with the months of rent logged and the year's pace said as an estimate
(core/assistant_tools get_property_summary, the rentals conversation check 2026-11-26: one month's rent had been read
as a 0.64% cap rate "doing well").
"""

from datetime import date
from types import SimpleNamespace

from core.assistant_tools import AssistantTools


def test_one_month_is_said_as_one_month():
    prop = SimpleNamespace(property_id="p1", name="123 Main St", current_value=280000.0, mortgage_balance=150000.0,
                           sale_date="", status="Active")
    entries = [SimpleNamespace(date=date.today().isoformat(), amount=1800.0)]
    estate = SimpleNamespace(all_properties=lambda: [prop], net_operating_income=lambda pid, a=None, b=None: 1800.0,
                             income_for_property=lambda pid, a=None, b=None: entries)
    said = AssistantTools._action_get_property_summary(SimpleNamespace(real_estate=estate), {"property_name": "123 Main St"})
    assert "from 1 month of rent logged, a cap rate of 0.64% so far" in said
    assert "about 7.7% (an estimate until a full year of rent is logged)" in said
