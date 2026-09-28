"""
"Propose, you confirm" (core/passing_mentions.py): offers to record what
the owner mentions in passing, made after MIA's reply and carried out
only on a yes; wired through core/talk_it_out.py for every chat surface.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

import core.budget_manager as budget_module
import core.config_manager as config_module
import core.conversation_manager as conversation_module
import core.data_logger_manager as data_logger_module
import core.kitchen_manager as kitchen_module
import core.maintenance_manager as maintenance_module
from core.app_context import AppContext
from core.assistant_turn import run_assistant_turn
from core.budget_manager import BudgetManager
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.conversation_modes import LISTEN
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.kitchen_manager import KitchenManager
from core.llm_manager import ChatReply, ToolCall
from core.maintenance_manager import MaintenanceManager
from core.passing_mentions import detect_offer, is_yes
from core.talk_it_out import pre_turn, with_offer
from tests.assistant_registry import build_desktop_registry

_MODULES = [budget_module, conversation_module, data_logger_module, kitchen_module, maintenance_module]


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
    context.data_logger = DataLoggerManager(context)
    context.maintenance = MaintenanceManager(context)
    context.kitchen = KitchenManager(context)
    context.conversations = ConversationManager(context)
    context.assistant_actions = build_desktop_registry()
    context.mower = context.maintenance.add_asset("Riding Mower", category="Power Equipment")
    context.blades = context.maintenance.add_task(context.mower.asset_id, "Sharpen blades", interval_days=30)
    context.truck = context.maintenance.add_asset("Pickup Truck", category="Vehicle")
    context.maintenance.add_task(context.truck.asset_id, "Change engine oil", interval_days=90)
    context.budget.add_bill(name="Electric", amount=120.0, due_date="2026-10-01", category="Utilities", recurrence="monthly")
    context.budget.add_debt(name="Chase Freedom", balance=4200.0, interest_rate=24.99, minimum_payment=90.0)
    context.kitchen.add_grocery_item("Eggs")
    return context


def offer(ctx, text):
    found = detect_offer(text, ctx)
    return found.question if found else None


# ------------------------------------------------------------------ what counts


def test_work_on_an_item_matching_a_task(ctx):
    assert offer(ctx, "I sharpened the mower blades this morning") == "Want me to mark “Sharpen blades” done on the Riding Mower?"
    assert offer(ctx, "Changed the oil in the truck, $45") == "Want me to mark “Change engine oil” done on the Pickup Truck and log the $45.00?"


def test_other_work_becomes_a_note(ctx):
    found = detect_offer("Ugh, the mower got a new battery today, $120.", ctx)
    assert found.question == "Want me to note that on the Riding Mower's page and log the $120.00?"
    assert found.calls == [("add_asset_note", {"asset_name": "Riding Mower", "note": "The mower got a new battery today, $120"})]


def test_bills_debts_and_groceries(ctx):
    assert offer(ctx, "Finally paid the electric bill") == "Want me to mark the Electric bill paid?"
    assert offer(ctx, "I paid $200 on the Chase Freedom card today") == "Want me to record the $200.00 payment on Chase Freedom?"
    assert offer(ctx, "We're out of milk and bread again") == "Want me to add milk and bread to the grocery list?"
    assert offer(ctx, "We're out of eggs") is None  # already on the list


@pytest.mark.parametrize("text", [
    "The mower needs a new battery",
    "Should I sharpen the mower blades?",
    "I'm going to change the oil in the truck this weekend",
    "I didn't get to the mower today",
    "The truck is running great",
    "I love my new mower",
    "I paid way too much for dinner",
    "Work was awful, I just want to go home",
])
def test_no_offer_for_plans_questions_and_small_talk(ctx, text):
    assert detect_offer(text, ctx) is None


def test_what_counts_as_yes():
    for text in ("yes", "Yeah!", "sure", "yes please", "Do it", "go ahead", "ok thanks", "Yep, thank you"):
        assert is_yes(text), text
    for text in ("no", "not now", "yes but not the cost", "what?", "Yeah the mower is old"):
        assert not is_yes(text), text


# ------------------------------------------------------------------ the conversation


def turn(ctx, conversation, prompt, model_reply="Nice, that should help."):
    """One turn on the shared path (phone/voice), with a stand-in model."""
    ctx.llm = SimpleNamespace(chat_with_tools=lambda messages, tools: ChatReply(content=model_reply))
    return run_assistant_turn(ctx, conversation, prompt).replies


def test_offer_then_yes_records_it(ctx):
    conversation = ctx.conversations.create_conversation()
    [reply] = turn(ctx, conversation, "Ugh, the mower got a new battery today, $120.")
    assert reply == "Nice, that should help. Want me to note that on the Riding Mower's page and log the $120.00?"
    assert ctx.budget.all_expenses() == []  # nothing until yes
    [done] = turn(ctx, conversation, "yeah")
    assert "Logged $120.00" in done
    [expense] = ctx.budget.all_expenses()
    assert expense.asset_id == ctx.mower.asset_id and expense.category == "Maintenance"
    assert "new battery" in ctx.maintenance.get_asset(ctx.mower.asset_id).notes.lower()
    assert conversation.messages[-1].content == done
    # A second yes does nothing special.
    [again] = turn(ctx, conversation, "yes", model_reply="Anything else?")
    assert again == "Anything else?" and len(ctx.budget.all_expenses()) == 1


def test_yes_to_a_task_offer_marks_it_done(ctx):
    conversation = ctx.conversations.create_conversation()
    turn(ctx, conversation, "I sharpened the mower blades this morning")
    [done] = turn(ctx, conversation, "sure")
    assert ctx.maintenance.get_task(ctx.blades.task_id).last_completed
    assert "Sharpen blades" in done


def test_anything_but_yes_drops_the_offer(ctx):
    conversation = ctx.conversations.create_conversation()
    turn(ctx, conversation, "Finally paid the electric bill")
    turn(ctx, conversation, "no, I'll do it later", model_reply="Okay.")
    [reply] = turn(ctx, conversation, "yes", model_reply="Yes to what?")
    assert reply == "Yes to what?" and ctx.budget.all_expenses() == []


def test_no_offer_when_the_model_already_ran_the_tool(ctx):
    conversation = ctx.conversations.create_conversation()
    ctx.llm = SimpleNamespace(chat_with_tools=lambda m, t: ChatReply(
        content="", tool_calls=[ToolCall(name="mark_bill_paid", arguments={"name": "Electric"})]))
    run_assistant_turn(ctx, conversation, "Finally paid the electric bill")
    assert len(ctx.budget.all_expenses()) == 1
    [reply] = turn(ctx, conversation, "yes", model_reply="Great.")
    assert reply == "Great." and len(ctx.budget.all_expenses()) == 1  # never paid twice


def test_no_offers_while_listening_journaling_or_off_the_record(ctx):
    for setup in ({"mode": LISTEN}, {"journal": True}, {"off_record": True}):
        conversation = ctx.conversations.create_conversation()
        for key, value in setup.items():
            setattr(conversation, key, value)
        pre_turn(ctx, conversation, "Ugh, the mower got a new battery today")
        assert with_offer(conversation, "That's rough.") == "That's rough.", setup


def test_an_old_offer_expires(ctx):
    conversation = ctx.conversations.create_conversation()
    turn(ctx, conversation, "Finally paid the electric bill")
    conversation.pending_offer.created -= 31 * 60
    [reply] = turn(ctx, conversation, "yes", model_reply="Hm?")
    assert reply == "Hm?" and ctx.budget.all_expenses() == []
