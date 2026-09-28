"""
Sorting bank charges to businesses (core/business_tagging.py): learning
from the owner's choices, auto-tagging after a sync, the review list,
the voice tools and the review dialog.
"""

from datetime import date
from pathlib import Path

import pytest

import core.budget_manager as budget_module
import core.config_manager as config_module
import core.real_estate_manager as real_estate_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.business_tagging import PERSONAL, apply_choice, auto_tag_new, learn, merchant_key, pending_review, suggest
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.real_estate_manager import RealEstateManager
from tests.assistant_registry import build_desktop_registry

TODAY = date(2026, 9, 28)


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    for module in (budget_module, real_estate_module):
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.budget = BudgetManager(context)
    context.real_estate = RealEstateManager(context)
    context.assistant_actions = build_desktop_registry()
    context.lawn = context.budget.add_business_entity(name="Johnson Lawn Care", entity_type="Sole Proprietorship")
    context.rentals = context.budget.add_business_entity(name="Maple Rentals LLC")
    return context


_counter = [0]


def bank_charge(ctx, description, amount=20.0, when="2026-09-20", **fields):
    _counter[0] += 1
    return ctx.budget.add_expense(amount=amount, description=description, date=when,
                                  plaid_transaction_id=f"txn-{_counter[0]}", **fields)


def owner_sorted(ctx, description, entity_id, times):
    for _ in range(times):
        charge = bank_charge(ctx, description, when="2026-08-01")
        apply_choice(ctx, charge.entry_id, entity_id)


def test_merchant_names():
    assert merchant_key("SHELL OIL 57444 BOWLING GRN") == merchant_key("Shell") == "shell"
    assert merchant_key("The Home Depot #1234") == "home depot"
    assert merchant_key("LOWE'S #0123") == "lowes"
    assert merchant_key("Tractor Supply Co") == "tractor supply"
    assert merchant_key("#1234") == ""


def test_learning_from_the_owner_and_how_sure_to_be(ctx):
    owner_sorted(ctx, "SHELL OIL 57444", ctx.lawn.entity_id, 2)
    history = learn(ctx.budget.all_expenses())
    new = bank_charge(ctx, "Shell Service Station")
    entities = ctx.budget.all_business_entities()
    guess = suggest(new, history, entities)
    assert guess.entity_id == ctx.lawn.entity_id and not guess.sure and "2 times" in guess.reason
    owner_sorted(ctx, "Shell", ctx.lawn.entity_id, 1)
    assert suggest(new, learn(ctx.budget.all_expenses()), entities).sure
    # Mixed history isn't "sure".
    owner_sorted(ctx, "Shell", PERSONAL, 1)
    assert not suggest(new, learn(ctx.budget.all_expenses()), entities).sure


def test_personal_is_learned_too_and_names_help(ctx):
    owner_sorted(ctx, "WALMART SUPERCENTER", PERSONAL, 3)
    entities = ctx.budget.all_business_entities()
    guess = suggest(bank_charge(ctx, "Walmart"), learn(ctx.budget.all_expenses()), entities)
    assert guess.entity_id == PERSONAL and guess.sure
    named = suggest(bank_charge(ctx, "MAPLE ST HARDWARE for maple rentals"), {}, entities)
    assert named.entity_id == ctx.rentals.entity_id and not named.sure


def test_a_rental_propertys_expenses_go_to_its_business(ctx):
    house = ctx.real_estate.add_property(name="12 Maple St", property_type="Rental")
    ctx.real_estate.update_property(house.property_id, entity_id=ctx.rentals.entity_id)
    charge = bank_charge(ctx, "City Water", property_id=house.property_id)
    result = auto_tag_new(ctx, TODAY)
    assert ctx.budget.get_expense(charge.entry_id).entity_id == ctx.rentals.entity_id
    assert result.tagged and result.waiting == 0


def test_after_a_sync_sure_ones_are_tagged_and_the_rest_wait(ctx):
    owner_sorted(ctx, "Shell", ctx.lawn.entity_id, 3)
    fuel = bank_charge(ctx, "SHELL OIL 1234", 52.10)
    unknown = bank_charge(ctx, "Etsy", 18.00)
    old = bank_charge(ctx, "Etsy", 9.00, when="2026-01-01")  # too old to ask about
    typed = ctx.budget.add_expense(amount=5, description="Coffee")  # typed in, not from the bank
    result = auto_tag_new(ctx, TODAY)
    tagged = ctx.budget.get_expense(fuel.entry_id)
    assert tagged.entity_id == ctx.lawn.entity_id and tagged.entity_auto and tagged.entity_reviewed
    assert [e.entry_id for e, _ in pending_review(ctx, TODAY)] == [unknown.entry_id]
    assert result.describe() == ("Tagged 1 to Johnson Lawn Care automatically; 1 charge needs a business "
                                 "(Budget → Review Business Tags).")
    assert old.entry_id and typed.entry_id  # neither is asked about
    # MIA's own tags never teach her.
    assert learn([tagged]) == {}


def test_nothing_happens_without_a_business(tmp_path, monkeypatch):
    for module in (budget_module,):
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.budget = BudgetManager(context)
    context.budget.add_expense(amount=5, description="Shell", plaid_transaction_id="t1")
    assert pending_review(context) == [] and auto_tag_new(context).describe() == ""


def test_voice_tools(ctx):
    say = lambda name, **args: ctx.assistant_actions.execute(ctx, name, args)  # noqa: E731
    assert say("list_untagged_charges") == "Every bank charge is sorted."
    owner_sorted(ctx, "Shell", ctx.lawn.entity_id, 1)
    bank_charge(ctx, "SHELL OIL 57444", 52.10, when=date.today().isoformat())
    bank_charge(ctx, "Walmart", 30.00, when=date.today().isoformat())
    listing = say("list_untagged_charges")
    assert listing.startswith("2 charges need a business") and "(probably Johnson Lawn Care)" in listing
    reply = say("tag_charge", charge="the Shell charge", business="lawn care")
    assert "as Johnson Lawn Care" in reply and "remember" in reply
    assert "as personal" in say("tag_charge", charge="Walmart", business="personal")
    assert say("list_untagged_charges") == "Every bank charge is sorted."
    assert "don't have a business called" in say("tag_charge", charge="Shell", business="bakery")


def test_review_dialog(ctx):
    from PySide6.QtWidgets import QApplication

    from gui.business_tags_dialog import LATER, BusinessTagsDialog

    QApplication.instance() or QApplication([])
    owner_sorted(ctx, "Shell", ctx.lawn.entity_id, 3)
    auto = bank_charge(ctx, "Shell", when=date.today().isoformat())
    auto_tag_new(ctx)
    guessed = bank_charge(ctx, "Tractor Supply for maple rentals", when=date.today().isoformat())
    later = bank_charge(ctx, "Etsy", when=date.today().isoformat())
    dialog = BusinessTagsDialog(ctx)
    assert dialog._pending_table.rowCount() == 2 and dialog._auto_table.rowCount() == 1
    combos = {entry_id: combo for entry_id, combo, _ in dialog._rows}
    assert combos[guessed.entry_id].currentData() == ctx.rentals.entity_id  # MIA's guess preselected
    assert combos[later.entry_id].currentData() == LATER
    combos[auto.entry_id].setCurrentIndex(combos[auto.entry_id].findData(PERSONAL))  # MIA was wrong
    dialog._save()
    assert ctx.budget.get_expense(guessed.entry_id).entity_id == ctx.rentals.entity_id
    corrected = ctx.budget.get_expense(auto.entry_id)
    assert corrected.entity_id == "" and corrected.entity_reviewed and not corrected.entity_auto
    assert not ctx.budget.get_expense(later.entry_id).entity_reviewed  # still waiting
