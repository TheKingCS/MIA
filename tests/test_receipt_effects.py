"""
tests.test_receipt_effects
============================

Receipts that do things (core/receipt_effects.py) and the everyday
mailbox they come from (core/inbox_mail.fetch_receipts): a grocery receipt
stocks the pantry and ticks the grocery list, an oil change is marked done
on the truck at the receipt's mileage, a Lowe's receipt adds to the
materials at the price paid; an emailed receipt files itself (unless it
looks logged already, or that's turned off), and Undo, on screen or by
voice, takes back exactly what it did; and the mailbox is read without
marking anything read, taking only receipts.
"""

from __future__ import annotations

from datetime import date
from email.message import EmailMessage

import pytest

from core import receipt_effects as effects
from core.inbox_mail import fetch_receipts, looks_like_receipt
from core.kitchen_manager import KitchenManager
from core.material_manager import MaterialManager
from tests.test_inbox import drop, make_ctx, qapp  # noqa: F401  (qapp: the Qt fixture make_ctx's stores need)

GROCERY = """KROGER
11/05/2026
GV WHL MLK GAL 0078742         3.49
LG EGGS 12CT                   2.99
BNLS CHKN BRST 2.1LB           9.87
BNNA                           1.29
SUBTOTAL                      17.64
TAX                            0.00
TOTAL                         17.64
"""

OIL_CHANGE = """Valvoline Instant Oil Change
Date: 11/03/2026
Vehicle: Ford F-150   Mileage In: 84,512
FULL SYNTHETIC OIL CHANGE      79.99
ENGINE AIR FILTER              24.99
TOTAL                         104.98
"""

LOWES = """Lowe's Home Improvement
11/06/2026
2X4X8 STUD 6 @ 3.98           23.88
PLYWD 3/4 4X8 1 @ 52.00       52.00
DECK SCREWS 5LB                34.98
TOTAL                         110.86
"""


def test_reading_a_receipt():
    """Receipt names read like a person wrote them; foods find their shelf; the kind of receipt comes from the store
    or its lines; services and the odometer are found; promotions aren't receipts."""
    assert effects.readable_name("GV WHL MLK GAL 0078742") == "Whole milk"
    assert effects.readable_name("BNLS CHKN BRST 2.1LB") == "Boneless chicken breast"
    assert effects.pantry_category("Whole milk") == "Dairy" and effects.pantry_category("Deck screws") == ""
    assert effects.kind_of("Kroger", GROCERY, []) == effects.GROCERY
    assert effects.kind_of("Valvoline", OIL_CHANGE, []) == effects.AUTO
    assert effects.kind_of("Lowe's", LOWES, []) == effects.BUILDING
    assert effects.kind_of("Panera", "SOUP 6.99", [{"description": "SOUP"}]) == ""
    assert effects.services_in(OIL_CHANGE) == ["Oil change", "Engine air filter"]
    assert effects.odometer_in(OIL_CHANGE) == 84512
    assert effects.services_in("SOURDOUGH LOAF 4.99") == []
    assert looks_like_receipt("Lowe's <receipts@lowes.com>", "Your Lowe's receipt")
    assert looks_like_receipt("orders@kroger.com", "Thank you for your order")
    assert not looks_like_receipt("deals@lowes.com", "30% off deck stain this weekend")
    assert not looks_like_receipt("Mom <mom@example.com>", "Dinner Sunday?")


@pytest.fixture
def ctx(tmp_path, monkeypatch, qapp):  # noqa: F811
    """The inbox tests' world with a kitchen (milk already in the pantry, eggs on the grocery list), the truck's
    oil change task (every 5,000 miles), and the workshop's 2x4 studs."""
    context = make_ctx(tmp_path, monkeypatch)
    context.kitchen = KitchenManager(context, data_dir=tmp_path / "kitchen")
    context.materials = MaterialManager(context, data_dir=tmp_path / "materials")
    context.milk = context.kitchen.add_pantry_item("Whole milk", quantity=1, category="Dairy")
    context.eggs = context.kitchen.add_grocery_item("Eggs")
    context.oil = context.maintenance.add_task(context.truck.asset_id, "Oil change", trigger_type="mileage",
                                               meter_unit="miles", meter_interval=5000)
    context.studs = context.materials.add_material(name="2x4 stud", unit="each", unit_cost=3.5, quantity_on_hand=4)
    context.maintenance.update_asset(context.truck.asset_id, category="Vehicle")
    return context


def emailed(text: str, subject: str, sender: str) -> bytes:
    """A receipt as an email: its subject, sender and the receipt as the body."""
    message = EmailMessage()
    message["Subject"], message["From"] = subject, sender
    message.set_content(text)
    return message.as_bytes()


def test_an_emailed_grocery_receipt_files_itself_and_undoes_exactly(ctx):
    """Emailed, it files on its own: milk tops up the milk already there, chicken and bananas go in on their shelves,
    eggs come off the grocery list, the total goes in Money. Undo takes back exactly that (milk bought since stays)
    and the receipt waits again."""
    [item] = drop(ctx, "message.eml", emailed(GROCERY, "Your Kroger receipt", "receipts@kroger.com"), source="email")
    assert item.receipt_kind == effects.GROCERY and item.auto and item.status == "filed"
    assert item.filed_note.startswith("Filed by MIA:")
    assert ctx.kitchen.get_pantry_item(ctx.milk.item_id).quantity == 2
    shelves = {p.name: p.category for p in ctx.kitchen.all_pantry_items()}
    assert shelves.get("Boneless chicken breast") == "Meat" and shelves.get("Bananas") == "Produce"
    assert ctx.kitchen.get_grocery_item(ctx.eggs.item_id).checked
    assert [e.amount for e in ctx.budget.all_expenses()] == [17.64]
    assert ctx.inbox.auto_filed()[0].item_id == item.item_id
    ctx.kitchen.update_pantry_item(ctx.milk.item_id, quantity=3)  # a gallon bought since, by hand
    said = ctx.inbox.unfile(item.item_id)
    assert "took the expense out of Money" in said and not ctx.budget.all_expenses()
    assert ctx.kitchen.get_pantry_item(ctx.milk.item_id).quantity == 2
    assert "Boneless chicken breast" not in {p.name for p in ctx.kitchen.all_pantry_items()}
    assert not ctx.kitchen.get_grocery_item(ctx.eggs.item_id).checked
    again = ctx.inbox.get_item(item.item_id)
    assert again.status == "pending" and not again.auto and again.note.startswith("Undone")


def test_an_oil_change_is_done_at_its_mileage_and_undone(ctx):
    """The truck's oil change is done on the receipt's date at 84,512 miles and the air filter starts being tracked;
    Undo puts the oil change back as it was and removes the new task and the odometer reading."""
    before = ctx.maintenance.get_task(ctx.oil.task_id).last_completed
    [item] = drop(ctx, "message.eml", emailed(OIL_CHANGE, "Your service receipt", "valvoline.com"), source="email")
    assert item.receipt_kind == effects.AUTO and item.auto
    task = ctx.maintenance.get_task(ctx.oil.task_id)
    assert task.last_completed == "2026-11-03" and task.last_completed_meter_value == 84512
    assert "Engine air filter" in [t.title for t in ctx.maintenance.tasks_for_asset(ctx.truck.asset_id)]
    assert ctx.maintenance.readings_for_task(ctx.oil.task_id)
    ctx.inbox.unfile(item.item_id)
    task = ctx.maintenance.get_task(ctx.oil.task_id)
    assert task.last_completed == before and task.last_completed_meter_value is None
    assert "Engine air filter" not in [t.title for t in ctx.maintenance.tasks_for_asset(ctx.truck.asset_id)]
    assert not ctx.maintenance.readings_for_task(ctx.oil.task_id)


def test_lowes_adds_materials_at_the_price_paid(ctx):
    """Dropped in by hand it waits; filed with the screws unticked, six studs join the four on hand at $3.98 and
    plywood is new; Undo puts the studs back to four at $3.50 and removes the plywood."""
    [item] = drop(ctx, "receipt.txt", LOWES)
    assert item.receipt_kind == effects.BUILDING and item.status == "pending"  # only emailed receipts file themselves
    keep = [i for i, e in enumerate(item.effects) if "SCREWS" not in e["label"].upper()]
    ctx.inbox.file_item(item.item_id, effect_indexes=keep)
    studs = ctx.materials.get_material(ctx.studs.material_id)
    assert studs.quantity_on_hand == 10 and studs.unit_cost == 3.98
    names = [m.name.lower() for m in ctx.materials.all_materials()]
    assert any("plywood" in n for n in names) and not any("screw" in n for n in names)
    ctx.inbox.unfile(item.item_id)
    studs = ctx.materials.get_material(ctx.studs.material_id)
    assert studs.quantity_on_hand == 4 and studs.unit_cost == 3.5
    assert [m.material_id for m in ctx.materials.all_materials()] == [ctx.studs.material_id]


def test_when_it_waits_instead(ctx):
    """The same purchase arriving twice (a forward, or an order email and its receipt) is logged once: the second
    waits, saying why. With automatic filing turned
    off (by asking), emailed receipts wait too; asked, she turns it back on."""
    from core.assistant_inbox_actions import _action_set_receipt_autofile

    [first] = drop(ctx, "message.eml", emailed(GROCERY, "Your Kroger receipt", "receipts@kroger.com"), source="email")
    [second] = drop(ctx, "message.eml", emailed(GROCERY, "Fwd: Your Kroger receipt", "me@example.com"), source="email")
    assert first.auto and second.status == "pending" and "already logged" in second.note
    assert "wait in the Inbox" in _action_set_receipt_autofile(ctx, {"on": False})
    [third] = drop(ctx, "message.eml", emailed(OIL_CHANGE, "Your service receipt", "valvoline.com"), source="email")
    assert third.status == "pending" and not third.auto
    assert "on my own again" in _action_set_receipt_autofile(ctx, {"on": "true"})


def test_undo_by_voice_and_on_screen(ctx):
    """"Undo the Kroger receipt" finds it by name; the Inbox screen lists what MIA filed with an Undo, which goes
    through the action contract."""
    from core.actions import ActionCenter
    from core.assistant_inbox_actions import _action_undo_receipt
    from core.web_inbox import inbox_page

    [item] = drop(ctx, "message.eml", emailed(GROCERY, "Your Kroger receipt", "receipts@kroger.com"), source="email")
    page = inbox_page(ctx)
    assert page["auto"][0]["id"] == item.item_id and page["auto_on"]
    assert "Undid" in _action_undo_receipt(ctx, {"item": "the kroger receipt"})
    assert ctx.inbox.get_item(item.item_id).status == "pending"
    ctx.inbox.file_item(item.item_id)
    ctx.actions = ActionCenter()
    proposal = ctx.actions.propose(ctx, "inbox.unfile", {"item_id": item.item_id})
    assert proposal.summary.startswith("Undo filing")
    assert ctx.actions.approve(ctx, proposal.proposal_id).status == "executed"
    assert ctx.inbox.get_item(item.item_id).status == "pending"


class FakeMailbox:
    """An everyday mailbox over IMAP: three messages (a receipt, a promotion, a note from family); it records how
    each was opened and fetched."""

    def __init__(self):
        """The messages by UID, and nothing done yet."""
        self.messages = {
            7: emailed(LOWES, "Your Lowe's receipt", "receipts@lowes.com"),
            8: emailed("Big savings", "30% off deck stain", "deals@lowes.com"),
            9: emailed("See you Sunday", "Dinner Sunday?", "mom@example.com"),
        }
        self.calls = []

    def login(self, user, password):
        """Signs in."""
        self.calls.append(("login",))

    def select(self, folder, readonly=False):
        """Opens the folder (recording whether read-only)."""
        self.calls.append(("select", readonly))
        return "OK", [b"3"]

    def response(self, name):
        """The folder's UIDVALIDITY."""
        return "OK", [b"42"]

    def uid(self, command, *args):
        """SEARCH by UID or date, and FETCH headers or the whole message (recording what was fetched)."""
        self.calls.append((command,) + args)
        if command == "SEARCH":
            if args[1].startswith("UID"):
                low = int(args[1].split()[1].split(":")[0])
                return "OK", [" ".join(str(u) for u in self.messages if u >= low).encode() or b"9"]
            return "OK", [b"7 8 9"]
        raw = self.messages[int(args[0])]
        if "HEADER.FIELDS" in args[1]:
            return "OK", [(b"head", raw.split(b"\n\n", 1)[0])]
        return "OK", [(b"body", raw)]

    def logout(self):
        """Signs out."""


def test_the_everyday_mailbox_is_left_as_it_is():
    """Only the receipt is downloaded; the folder is read-only and every fetch peeks; the next check starts after
    the last message seen."""
    box = FakeMailbox()
    messages, state = fetch_receipts("imap.example.com", "me", "pw", connect=lambda h, p: box,
                                     today=date(2026, 11, 7))
    assert len(messages) == 1 and b"Lowe's receipt" in messages[0]
    assert ("select", True) in box.calls
    fetches = [c for c in box.calls if c[0] == "FETCH"]
    assert fetches and all("PEEK" in c[2] for c in fetches)
    assert sum("HEADER" not in c[2] for c in fetches) == 1  # only the receipt's whole message
    assert state == {"uidvalidity": "42", "last_uid": 9}
    again, state = fetch_receipts("imap.example.com", "me", "pw", connect=lambda h, p: box, state=state)
    assert again == [] and state["last_uid"] == 9
