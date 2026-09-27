"""
Slice B, "Remember Why": the reason chain on Intents, the evidence
builder (core/why_graph.py), the tools (core/assistant_why_actions.py),
and the Perspective path. Checks facts and structure, never wording.
"""

import json
import re
from datetime import date
from pathlib import Path

import pytest

import core.budget_manager as budget_module
import core.config_manager as config_module
import core.intent_manager as intent_module
import core.mission_manager as mission_module
import core.project_manager as project_module
import core.real_estate_manager as real_estate_module
import core.user_memory_manager as memory_module
import core.why_graph as why_module
from core.app_context import AppContext
from core.assistant_chat import NO_WHY_YET_INSTRUCTION, build_chat_request
from core.budget_manager import BudgetManager
from core.config_manager import ConfigManager
from core.conversation_manager import Conversation
from core.conversation_modes import PERSPECTIVE, detect_mode_change
from core.event_bus import EventBus
from core.intent_manager import IntentManager
from core.mission_manager import MissionManager
from core.project_manager import ProjectManager
from core.real_estate_manager import RealEstateManager
from core.user_memory_manager import UserMemoryManager
from core.why_graph import build_why_sheet, describe_changes, record_checkpoint_if_due
from tests.assistant_registry import build_desktop_registry

_MODULES = [budget_module, intent_module, mission_module, project_module, real_estate_module, memory_module, why_module]
TODAY = date(2026, 9, 27)


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    for module in _MODULES:
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.budget = BudgetManager(context)
    context.real_estate = RealEstateManager(context)
    context.intents = IntentManager(context)
    context.projects = ProjectManager(context)
    context.missions = MissionManager(context)
    context.user_memories = UserMemoryManager(context)
    context.assistant_actions = build_desktop_registry()
    return context


def say(ctx, action, **arguments):
    return ctx.assistant_actions.execute(ctx, action, arguments)


def build_chain(ctx):
    say(ctx, "link_my_reason", goal="Factory work", serves="Pay off debt", reason="the factory pays the bills")
    return say(ctx, "link_my_reason", goal="pay off debt", serves="Control over my time")


# ------------------------------------------------------------------ the chain


def test_linking_builds_and_reads_back_the_chain(ctx):
    reply = build_chain(ctx)
    assert reply.startswith("Got it: Factory work → Pay off debt → Control over my time.")
    assert len(ctx.intents.all_intents()) == 3  # "pay off debt" found the existing goal
    factory = next(i for i in ctx.intents.all_intents() if i.name == "Factory work")
    assert factory.reason == "the factory pays the bills"


def test_cycle_is_refused(ctx):
    build_chain(ctx)
    reply = say(ctx, "link_my_reason", goal="Control over my time", serves="Factory work")
    assert "can't link it the other way" in reply
    top = next(i for i in ctx.intents.all_intents() if i.name == "Control over my time")
    assert top.serves_intent_id is None


def test_unlink_and_delete_keep_the_chain_consistent(ctx):
    build_chain(ctx)
    assert say(ctx, "unlink_my_reason", goal="factory work").startswith("Unlinked")
    debt = next(i for i in ctx.intents.all_intents() if i.name == "Pay off debt")
    time_goal = next(i for i in ctx.intents.all_intents() if i.name == "Control over my time")
    ctx.intents.delete_intent(time_goal.intent_id)
    assert ctx.intents.get_intent(debt.intent_id).serves_intent_id is None


def test_intent_fields_round_trip(ctx):
    build_chain(ctx)
    reloaded = IntentManager(ctx)
    factory = next(i for i in reloaded.all_intents() if i.name == "Factory work")
    assert factory.serves_intent_id is not None and factory.reason == "the factory pays the bills"


# ------------------------------------------------------------------ evidence


def seed_life(ctx):
    ctx.budget.add_debt("Chase card", 3000, 24.9)
    ctx.budget.add_debt("Truck loan", 12000, 6.9, debt_type="Auto Loan")
    maple = ctx.real_estate.add_property("Maple duplex", property_type="Rental")
    ctx.real_estate.record_rental_income(maple.property_id, 1450, TODAY.isoformat())
    ctx.real_estate.add_property("The 12 acres", property_type="Land")
    ctx.budget.add_income(amount=2100, category="Paycheck", description="Factory", date=TODAY.isoformat())


def test_evidence_attaches_to_the_right_links(ctx):
    seed_life(ctx)
    build_chain(ctx)
    homestead = say(ctx, "link_my_reason", goal="Control over my time", serves="Homestead life")
    assert "Homestead life" in homestead
    home_intent = next(i for i in ctx.intents.all_intents() if i.name == "Homestead life")
    ctx.projects.add_project("Walipini greenhouse", status="Active", intent_id=home_intent.intent_id)

    sheet = build_why_sheet(ctx, TODAY)
    [chain] = sheet.chains
    by_name = {link.name: link for link in chain}
    assert [link.name for link in chain] == ["Factory work", "Pay off debt", "Control over my time", "Homestead life"]
    assert "Income in the last 30 days: $3,550." in by_name["Factory work"].evidence  # paycheck + rent
    assert "Debt now: $15,000 across 2 debts." in by_name["Pay off debt"].evidence
    assert "You own the land: The 12 acres." in by_name["Homestead life"].evidence
    assert "Project 'Walipini greenhouse': Active." in by_name["Homestead life"].evidence
    assert by_name["Control over my time"].evidence == []  # nothing to measure, and nothing invented
    text = sheet.to_text()
    assert text.startswith("Chain: Factory work -> Pay off debt -> Control over my time -> Homestead life")
    assert 'their words: "the factory pays the bills"' in text


def test_rental_goal_gets_rental_facts(ctx):
    seed_life(ctx)
    say(ctx, "link_my_reason", goal="Grow the rentals", serves="Financial freedom")
    link = build_why_sheet(ctx, TODAY).chains[0][0]
    assert "You own 1 rental: Maple duplex." in link.evidence
    assert "Rent received in the last 30 days: $1,450." in link.evidence


def test_monthly_checkpoint_and_what_changed(ctx):
    seed_life(ctx)
    build_chain(ctx)
    record_checkpoint_if_due(ctx, date(2026, 6, 3))
    record_checkpoint_if_due(ctx, date(2026, 6, 20))  # same month: not a second checkpoint
    chase = next(d for d in ctx.budget.all_debts() if d.name == "Chase card")
    ctx.budget.update_debt(chase.debt_id, balance=0)
    ctx.real_estate.add_property("Oak St house", property_type="Rental")

    sheet = build_why_sheet(ctx, TODAY)
    months = [c["month"] for c in json.loads(why_module._CHECKPOINTS_FILE.read_text())]
    assert months == ["2026-06", "2026-09"]
    assert "Debt is down $3,000 since June 2026 ($15,000 then, $12,000 now)." in sheet.changes
    assert "1 more rental since June 2026 (1 then, 2 now)." in sheet.changes


def test_paid_off_debt_goal_becomes_done(ctx):
    seed_life(ctx)
    build_chain(ctx)
    record_checkpoint_if_due(ctx, date(2026, 5, 1))
    for debt in ctx.budget.all_debts():
        ctx.budget.update_debt(debt.debt_id, balance=0)
    debt_link = build_why_sheet(ctx, TODAY).chains[0][1]
    assert debt_link.done and debt_link.done_because == "the debt is paid off"
    assert "All tracked debt is paid off (it was $15,000 in May 2026)." in debt_link.evidence
    assert "[DONE: the debt is paid off. This used to be a reason" in build_why_sheet(ctx, TODAY).to_text()


def test_marking_achieved(ctx):
    build_chain(ctx)
    assert "Marked 'Pay off debt' achieved" in say(ctx, "mark_goal_achieved", goal="debt")
    assert build_why_sheet(ctx, TODAY).chains[0][1].done
    assert "(done)" in say(ctx, "show_my_why")


def test_wins(ctx):
    build_chain(ctx)
    mission = ctx.missions.add_mission("Frame the coop")
    ctx.missions.update_mission(mission.mission_id, status="completed")
    ctx.user_memories.add_memory("The user paid off the Chase card in August.", category="Wins")
    wins = build_why_sheet(ctx).wins
    assert "Completed the mission 'Frame the coop'." in wins
    assert "The user paid off the Chase card in August." in wins


def test_describe_changes_is_quiet_when_nothing_moved():
    same = {"month": "2026-06", "total_debt": 100.0, "rentals": 1, "land": 0, "projects_complete": 2}
    assert describe_changes(same, dict(same)) == []


# ------------------------------------------------------------------ Perspective


@pytest.mark.parametrize("text", [
    "Hey MIA, remind me why I'm doing all this",
    "Why am I even doing this?",
    "What's the point?",
    "I'm feeling dragged down at work",
    "No bullshit. Remind me why.",
])
def test_perspective_phrases(text):
    assert detect_mode_change(text).mode == PERSPECTIVE


@pytest.mark.parametrize("text", ["What's the point of the tomato bed", "I love my job", "Why is the sky blue?"])
def test_not_perspective(text):
    assert detect_mode_change(text).mode != PERSPECTIVE


def _perspective_request(ctx, prompt="Remind me why I'm doing all this"):
    conversation = Conversation(conversation_id="c1", mode=PERSPECTIVE)
    return build_chat_request(ctx, conversation, prompt)


def test_perspective_without_reasons_says_so(ctx):
    messages, tools = _perspective_request(ctx)
    assert NO_WHY_YET_INSTRUCTION in messages[0]["content"] and tools == []


def test_perspective_gets_the_fact_sheet_and_no_tools(ctx):
    seed_life(ctx)
    build_chain(ctx)
    messages, tools = _perspective_request(ctx)
    system = messages[0]["content"]
    assert tools == []
    assert "Chain: Factory work -> Pay off debt -> Control over my time" in system
    assert "Debt now: $15,000 across 2 debts." in system
    assert "Never invent a number" in system


def test_every_number_in_the_sheet_is_from_the_records(ctx):
    """The property the live check applies to the model's reply: the
    numbers MIA may say are exactly these."""
    seed_life(ctx)
    build_chain(ctx)
    numbers = set(re.findall(r"\$[\d,]+", build_why_sheet(ctx, TODAY).to_text()))
    assert numbers == {"$3,550", "$15,000"}


# ------------------------------------------------------------------ the goal dialog


def test_intent_dialog_offers_other_goals_and_returns_the_link(ctx):
    from PySide6.QtWidgets import QApplication

    from gui.add_edit_intent_dialog import AddEditIntentDialog

    QApplication.instance() or QApplication([])
    build_chain(ctx)
    factory = next(i for i in ctx.intents.all_intents() if i.name == "Factory work")
    dialog = AddEditIntentDialog(intent=factory, intents=ctx.intents.all_intents())
    names = [dialog.serves_combo.itemText(i) for i in range(dialog.serves_combo.count())]
    assert names == ["(nothing bigger)", "Pay off debt", "Control over my time"]  # never itself
    assert dialog.serves_combo.currentText() == "Pay off debt"
    assert dialog.reason_edit.text() == "the factory pays the bills"
    dialog.reason_edit.setText("it's buying my freedom")
    dialog._on_accept()
    assert dialog.entered_reason == "it's buying my freedom"
    assert dialog.entered_serves_intent_id == factory.serves_intent_id
