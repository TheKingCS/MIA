"""
tests.test_invoice_email
==========================

An order's invoice (core/business_actions.invoice_email, brainstorm 5.1): what, the price, what's been paid, the
balance and when it's due, drafted for his Send, never sent; a paid-up order's is a receipt.
"""

from types import SimpleNamespace

from core import business_actions as ba


def _ctx(paid):
    customer = SimpleNamespace(name="Sam Lee", email="sam@example.com")
    book = SimpleNamespace(get_customer=lambda cid: customer)
    return SimpleNamespace(business=book, profiles=None, _paid=paid)


def test_the_invoice_says_what_is_paid_and_left(monkeypatch):
    order = SimpleNamespace(title="Cedar bench", customer_id="c1", quantity=1, price=300.0, due_date="2026-12-05")
    monkeypatch.setattr(ba, "_book", lambda context: context.business)
    monkeypatch.setattr(ba, "_paid", lambda context, o: 100.0)
    to, subject, body = ba.invoice_email(_ctx(100), order)
    assert to == ["sam@example.com"] and subject == "Invoice: Cedar bench"
    assert "Hi Sam," in body and "Paid so far: $100.00" in body and "Balance due: $200.00" in body
    assert "Due December 5" in body and "margin" not in body.lower()


def test_a_paid_order_gets_a_receipt(monkeypatch):
    order = SimpleNamespace(title="Cedar bench", customer_id="c1", quantity=2, price=300.0, due_date="")
    monkeypatch.setattr(ba, "_book", lambda context: context.business)
    monkeypatch.setattr(ba, "_paid", lambda context, o: 300.0)
    _to, subject, body = ba.invoice_email(_ctx(300), order)
    assert subject == "Receipt: Cedar bench" and "Paid in full" in body and "(2 ×)" in body


def test_the_invoice_is_only_drafted_on_his_press():
    from core.actions import ACTION_TYPES

    kind = ACTION_TYPES["order.invoice"]
    assert kind.label == "Email Invoice"
    src = open(ba.__file__, encoding="utf-8").read()
    body = src[src.index("def _invoice(context"):src.index("def _feature_describe")]
    assert "email_drafts.create(" in body and ".send(" not in body
