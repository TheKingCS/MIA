"""
tests.test_id_wallet
======================

The ID wallet (core/id_wallet.py): cards kept with their numbers and photos sealed at rest, numbers masked in lists
and never in what MIA says or in an action, expiry reminders on Today, and "show my license" opening the card.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import core.at_rest as at_rest
from core.actions import ACTION_TYPES, ActionError
from core.id_wallet import RENEW_DAYS, IdWallet, describe, expiry_state, find_card, masked, wants_card

TODAY = date.today()


@pytest.fixture
def wallet(tmp_path):
    """A wallet in a temporary folder, sealing with a test key."""
    at_rest.use_key(bytes(range(32)))
    yield IdWallet(SimpleNamespace(), data_dir=tmp_path)
    at_rest.use_key(None)


def test_numbers_are_masked_and_expiry_is_in_words():
    assert masked("D1234-5678-9012") == "•••• 9012" and masked("12") == "••••" and masked("") == ""
    assert expiry_state((TODAY + timedelta(days=RENEW_DAYS)).isoformat(), TODAY)["state"] == "soon"
    assert expiry_state((TODAY - timedelta(days=1)).isoformat(), TODAY)["state"] == "expired"
    assert expiry_state("", TODAY)["state"] == "none"


def test_cards_and_photos_are_sealed_on_disk_and_open_again(wallet, tmp_path):
    card = wallet.add(kind="Driver's license", name="Texas driver's license", number="D1234-5678-9012",
                      expires=(TODAY + timedelta(days=25)).isoformat())
    wallet.set_photo(card["id"], "front", b"\x89PNG fake", "front.png")
    on_disk = (tmp_path / "id_wallet.json").read_text()
    assert on_disk.startswith(at_rest.PREFIX) and "D1234" not in on_disk
    assert (tmp_path / "id_wallet" / f"{card['id']}-front.photo").read_text().startswith(at_rest.PREFIX)
    again = IdWallet(SimpleNamespace(), data_dir=tmp_path)
    assert again.get(card["id"])["number"] == "D1234-5678-9012"
    assert again.photo(card["id"], "front") == (b"\x89PNG fake", "image/png")
    assert again.photo(card["id"], "back") is None
    with pytest.raises(ValueError):
        wallet.set_photo(card["id"], "front", b"x", "scan.pdf")


def test_lists_and_words_never_carry_a_number(wallet):
    wallet.add(kind="Passport", name="US passport", number="X99887766", expires="2029-04-09")
    context = SimpleNamespace(id_wallet=wallet)
    assert "X99887766" not in str(wallet.listing()) and "X99887766" not in describe(context)
    assert "US passport (expires 2029-04-09)" in describe(context)
    assert "X99887766" not in str(wallet.due())


def test_show_my_license_opens_that_card(wallet):
    lic = wallet.add(kind="Driver's license", name="Texas driver's license")
    wallet.add(kind="Auto insurance", name="Truck insurance card")
    context = SimpleNamespace(id_wallet=wallet)
    assert wants_card(context, "Show my driver's license") == (f"wallet.html?show={lic['id']}", "Texas driver's license")
    assert wants_card(context, "pull up my truck insurance card")[1] == "Truck insurance card"
    assert wants_card(context, "show my passport") is None
    assert find_card(wallet.cards, "insurance")["name"] == "Truck insurance card"


def test_removing_a_card_is_the_only_action_and_carries_no_number(wallet):
    card = wallet.add(name="Truck registration", kind="Vehicle registration", number="REG-55")
    action = ACTION_TYPES["wallet.delete"]
    assert set(action.params) == {"card_id"}
    context = SimpleNamespace(id_wallet=wallet)
    assert action.describe(context, {"card_id": card["id"]}) == "Take Truck registration out of your wallet"
    assert action.execute(context, {"card_id": card["id"]}) == "Took Truck registration out of your wallet."
    with pytest.raises(ActionError):
        action.execute(context, {"card_id": card["id"]})
    assert not any(k.startswith("wallet.") and k != "wallet.delete" for k in ACTION_TYPES)


def test_a_card_to_renew_shows_on_today(wallet):
    from core.today import today_items

    wallet.add(name="Texas driver's license", expires=(TODAY + timedelta(days=20)).isoformat())
    wallet.add(name="Old passport", expires=(TODAY - timedelta(days=3)).isoformat())
    wallet.add(name="New passport", expires=(TODAY + timedelta(days=900)).isoformat())
    items = {(i.title, i.when) for i in today_items(SimpleNamespace(id_wallet=wallet), TODAY) if i.module_id == "id_wallet"}
    assert items == {("Texas driver's license expires", "waiting"), ("Old passport expired", "overdue")}
