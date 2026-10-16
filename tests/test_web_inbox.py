"""
The Inbox screen on the web and the phone (Zac, 2026-10-16: "build the
inbox for sending stuff to MIA"): core/web_inbox.py shows what's waiting
(reading the folder first, so the phone needs no timer), and
core/inbox_actions.py files, dismisses and sends notes through
Propose → Approve.
"""

import pytest

from core.actions import ActionCenter, ActionError
from core.inbox_actions import _indexes
from core.web_inbox import inbox_page, item_file
from tests.test_inbox import RECEIPT_TEXT, make_ctx, qapp  # noqa: F401  (qapp is a fixture)


@pytest.fixture
def ctx(tmp_path, monkeypatch, qapp):  # noqa: F811
    context = make_ctx(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def do(ctx, kind, **params):
    proposal = ctx.actions.propose(ctx, kind, params)
    done = ctx.actions.approve(ctx, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal.summary, done.result


def test_indexes():
    assert _indexes("0, 2,x") == [0, 2] and _indexes([1]) == [1] and _indexes(None) == []


def test_sent_files_show_up_at_once_and_file_into_money(ctx):
    ctx.inbox.receive_file("lowes.txt", RECEIPT_TEXT.encode(), source="phone")
    page = inbox_page(ctx)
    [item] = page["pending"]
    assert item["label"] == "Lowe's receipt, $36.23" and item["source"] == "From your phone"
    assert item["files"] == [{"name": "lowes.txt", "kind": "text"}] and page["counts"]["waiting"] == 1
    assert {"id": ctx.mower.asset_id, "name": "Riding Mower"} in page["picks"]["assets"]
    said, result = do(ctx, "inbox.file", item_id=item["id"], asset_id=ctx.mower.asset_id, amount="40")
    assert said == "File Lowe's receipt, $36.23: log $40.00 in Money for the Riding Mower"
    assert result.startswith("Filed: logged $40.00 for the Riding Mower")
    expense = ctx.budget.all_expenses()[-1]
    assert expense.amount == 40 and expense.asset_id == ctx.mower.asset_id
    page = inbox_page(ctx)
    assert page["pending"] == [] and page["done"][0]["filed_note"].startswith("Filed:")
    with pytest.raises(ActionError):  # already filed
        ctx.actions.propose(ctx, "inbox.file", {"item_id": item["id"]})


def test_a_note_dismiss_and_files_stay_inside(ctx):
    said, _ = do(ctx, "inbox.note", title="Mower blade link", text="https://example.com/blade")
    assert said == 'Send MIA the note "Mower blade link"'
    [item] = inbox_page(ctx)["pending"]
    assert item["source"] == "A note" and item["files"][0]["name"] == "Mower blade link.txt"
    assert (item["label"], item["type_label"]) == ("Mower blade link", "Note")
    assert item_file(ctx, item["id"], "Mower blade link.txt").read_text().startswith("Mower blade link")
    assert item_file(ctx, item["id"], "../../inbox.json") is None and item_file(ctx, "nope", "x") is None
    do(ctx, "inbox.dismiss", item_id=item["id"])
    assert inbox_page(ctx)["done"][0]["status"] == "dismissed"
    with pytest.raises(ActionError):
        ctx.actions.propose(ctx, "inbox.note", {"text": "  "})


def test_a_receipt_needs_its_total(ctx):
    ctx.inbox.receive_file("scrap.txt", b"RECEIPT\nThank you for shopping\nVisa", source="phone")
    [item] = inbox_page(ctx)["pending"]
    assert item["needs_amount"]
    with pytest.raises(ActionError):
        ctx.actions.propose(ctx, "inbox.file", {"item_id": item["id"]})
    with pytest.raises(ActionError):
        ctx.actions.propose(ctx, "inbox.file", {"item_id": item["id"], "amount": "-3"})
