"""The glasses' readout panels for apps that had only questions (core/glasses.py): What MIA Noticed (Needs You
first, in amber), the Lab's latest readings (newest first) and Power's levels (the battery, then each meter, amber
when low). Readouts carry no action."""

from __future__ import annotations

import core.observations_web as observations_web
import core.web_lab as web_lab
import core.web_power as web_power
from core.glasses import _lab_latest, _noticed, _power_levels


def test_what_mia_noticed_leads_with_what_needs_you(monkeypatch):
    monkeypatch.setattr(observations_web, "screen", lambda c, t=None: {
        "findings": [{"title": "A heavy week", "next": "Move a training day", "kind": "Noticed"},
                     {"title": "Rent before payday", "next": "Move it to Monday", "kind": "Needs You"}],
        "insights": [{"source": "Upkeep", "items": [{"title": "Mower oil is due", "next": ""}]}]})
    lines = _noticed(None, None)["lines"]
    assert [(l["text"], l["tone"]) for l in lines] == [("Rent before payday", "attention"), ("A heavy week", ""),
                                                       ("Mower oil is due", "")]
    assert lines[2]["detail"] == "Upkeep" and not any("action" in l for l in lines)


def test_the_labs_newest_readings_and_powers_levels(monkeypatch):
    monkeypatch.setattr(web_lab, "lab_page", lambda c: {"available": True,
        "series": [{"name": "Soil moisture", "latest": "41%", "when": "2 h ago", "at": "2026-11-07T18:00"}],
        "other_series": [{"name": "Furnace · Filter pressure", "latest": "0.6 inH2O", "when": "now", "at": "2026-11-07T20:00"}]})
    assert [l["text"] for l in _lab_latest(None, None)["lines"]] == ["Furnace · Filter pressure", "Soil moisture"]
    monkeypatch.setattr(web_power, "power_page", lambda c: {
        "battery": {"available": True, "percent": 18, "plugged_in": False, "minutes_left": 75, "meter": {"tone": "attention"}},
        "sources": [{"name": "Propane", "meters": [{"name": "Level", "text": "60%", "when": "1 day ago", "meter": {"tone": ""}}]}]})
    lines = _power_levels(None, None)["lines"]
    assert (lines[0]["detail"], lines[0]["tone"]) == ("18% · 1 h 15 min left", "attention")
    assert lines[1]["text"] == "Propane · Level" and lines[1]["detail"] == "60% · 1 day ago"
