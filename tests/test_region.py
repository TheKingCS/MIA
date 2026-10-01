"""
Country-aware crisis lines and money (core/region.py), 2026-10-01.
"""

import time
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import person_settings, region
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager
from core.region import OTHER, REGIONS, country_of, currency_symbol_for, money, region_for
from core.safety_floor import safety_reply


@pytest.fixture(autouse=True)
def dollars_after(monkeypatch):
    monkeypatch.setattr(region, "_symbol", "$")  # never leak a test's currency into others


@pytest.fixture
def people(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    sam = context.profiles.create_profile("Sam", make_active=False)
    sam_view = SimpleNamespace(config=context.config, profiles=context.profiles, profile_id=sam.profile_id)
    return context, sam_view


def test_every_listed_country_has_a_crisis_line_and_emergency_number():
    for reg in REGIONS.values():
        reply = safety_reply(None, reg)
        assert reg.emergency in reply and reg.crisis in reply
    assert "988" in safety_reply() and "911" in safety_reply()  # the US unless told otherwise
    assert "116 123" in safety_reply(None, REGIONS["GB"]) and "999" in safety_reply(None, REGIONS["GB"])
    assert "13 11 14" in safety_reply(None, REGIONS["AU"]) and "000" in safety_reply(None, REGIONS["AU"])


def test_anywhere_else_gets_honest_general_advice():
    reply = safety_reply("my sister", OTHER)
    assert "findahelpline.com" in reply and "112" in reply and "988" not in reply and "my sister" in reply
    assert region.region("XX") is OTHER and region.region(None) is OTHER


def test_country_is_each_persons_own(people):
    context, sam_view = people
    assert country_of(context) == "US" and country_of(sam_view) == "US"  # what MIA assumed before
    context.config.set("region.country", "CA")  # the device's (first-run wizard)
    assert country_of(sam_view) == "CA"
    person_settings.put(sam_view, "region.country", "GB")
    assert country_of(sam_view) == "GB" and region_for(sam_view).name == "United Kingdom"
    assert country_of(context) == "CA"


def test_money_follows_the_signed_in_person(people):
    context, sam_view = people
    assert money(1234.5) == "$1,234.50" and money(-5, ".2f") == "$-5.00" and money(80, ",.0f") == "$80"
    person_settings.put(sam_view, "region.country", "IE")
    assert currency_symbol_for(sam_view) == "€"
    person_settings.put(sam_view, "region.currency", "GBP")
    assert currency_symbol_for(sam_view) == "£"
    region.use_for(sam_view)
    assert money(12) == "£12.00"
    region.use_for(context)
    assert money(12) == "$12.00"
    assert money("n/a") == "$n/a"  # never crashes a screen
