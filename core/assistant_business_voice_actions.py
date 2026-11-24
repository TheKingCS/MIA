"""
core.assistant_business_voice_actions
=======================================

His business by voice (DEC-0125: every feature by voice and on screen), the Business page's quotes, orders and
customers: what quotes are still out, what orders are open, a customer's details, adding a customer, making a quote,
a quote accepted (it becomes an order), and an order marked ready, delivered or cancelled. Before these, only a payment,
an invoice draft and "who owes me?" could be done by voice.

How: each change runs the Business page's own action kind (core/business_actions.py: customer.add, quote.add,
quote.accept, order.status) through `_run` (propose, then approve, as the screen does, with its checks, its sentence
and "undo that"); a record is found by the words said (`_one`: a customer by name, a quote or order by its title or
its customer's name). Reading is plain code over the business book; money through `core.region.money`.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_correction_actions import _one, _run, day_of

OPEN_QUOTES = ("Draft", "Sent")
DONE_ORDERS = ("Delivered", "Cancelled")
# What he'd call these, so a business question reaches them on the phone (no embedding model). Not "customer"
# alone: "customer service was terrible" is small talk; customers are reached by name and by "new customer".
WORDS = ("quote", "quotes", "orders", "commission", "commissions")


def _book(context):
    """The business book, or None."""
    return getattr(context, "business", None)


def _names(book) -> dict:
    """Customer id to name."""
    return {c.customer_id: c.name for c in getattr(book, "customers", [])}


def _money(amount) -> str:
    """Money as he reads it."""
    from core.region import money

    return money(float(amount or 0), ",.2f")


def _action_list_quotes(context, arguments: dict) -> str:
    """Tool list_quotes: the quotes still out (draft or sent), each with its customer and price."""
    from core.business_actions import quote_figures

    book = _book(context)
    if book is None:
        return "There's no business book here."
    names = _names(book)
    out = [q for q in book.quotes if q.status in OPEN_QUOTES]
    if not out:
        return "No quotes are out right now."
    lines = []
    for q in out:
        price = quote_figures(context, q)["price"]
        who = f" for {names[q.customer_id]}" if q.customer_id in names else ""
        lines.append(f"{q.title}{who}, {_money(price)} ({q.status.lower()})")
    return f"{len(out)} quote{'s' if len(out) != 1 else ''} out: " + "; ".join(lines) + "."


def _action_list_orders(context, arguments: dict) -> str:
    """Tool list_orders: the open orders (not delivered or cancelled), soonest due first, with customer, price and
    status."""
    book = _book(context)
    if book is None:
        return "There's no business book here."
    names = _names(book)
    open_ = sorted((o for o in book.orders if o.status not in DONE_ORDERS), key=lambda o: (o.due_date or "9999", o.title))
    if not open_:
        return "No open orders right now."
    lines = [f"{o.title}" + (f" for {names[o.customer_id]}" if o.customer_id in names else "")
             + f", {_money(o.price)}, {o.status.lower()}" + (f", due {o.due_date}" if o.due_date else "") for o in open_]
    return f"{len(open_)} open order{'s' if len(open_) != 1 else ''}: " + "; ".join(lines) + "."


def _action_customer_details(context, arguments: dict) -> str:
    """Tool customer_details: one customer's phone, email and notes, found by name."""
    book = _book(context)
    if book is None:
        return "There's no business book here."
    who = _one(list(book.customers), str(arguments.get("customer") or ""), lambda c: c.name, "customer")
    if isinstance(who, str):
        return who
    parts = [f"phone {who.phone}" if who.phone else "", f"email {who.email}" if who.email else "",
             f"notes: {who.notes}" if who.notes else ""]
    shown = "; ".join(p for p in parts if p)
    return f"{who.name}: {shown}." if shown else f"I have {who.name} as a customer, with no phone or email yet."


def _action_add_customer(context, arguments: dict) -> str:
    """Tool add_customer: a new customer (customer.add), with a phone, email or notes if said."""
    params = {k: str(arguments.get(k) or "").strip() for k in ("name", "phone", "email", "notes")}
    if not params["name"]:
        return "What's the customer's name?"
    return _run(context, "customer.add", {k: v for k, v in params.items() if v})


def _action_make_quote(context, arguments: dict) -> str:
    """Tool make_quote: a new quote (quote.add): what it's for, for a customer he already has (by name), how many,
    and a price if he set one (else the Business page's suggested price, from a recipe, applies)."""
    book = _book(context)
    if book is None:
        return "There's no business book here."
    title = str(arguments.get("title") or "").strip()
    if not title:
        return "What's the quote for?"
    params = {"title": title}
    said = str(arguments.get("customer") or "").strip()
    if said:
        who = _one(list(book.customers), said, lambda c: c.name, "customer")
        if isinstance(who, str):
            return who + " Say \"add a customer named ...\" first, or make the quote without one."
        params["customer_id"] = who.customer_id
    for key in ("quantity", "price"):
        if arguments.get(key) not in (None, ""):
            params[key] = arguments[key]
    return _run(context, "quote.add", params)


def _quote_named(book, said: str):
    """An open quote by its title or its customer's name, or a question as a str."""
    names = _names(book)
    return _one([q for q in book.quotes if q.status in OPEN_QUOTES], said,
                lambda q: f"{q.title} {names.get(q.customer_id, '')}".strip(), "quote")


def _action_accept_quote(context, arguments: dict) -> str:
    """Tool accept_quote: a quote accepted (quote.accept): it becomes an order, due when he says."""
    book = _book(context)
    if book is None:
        return "There's no business book here."
    quote = _quote_named(book, str(arguments.get("quote") or ""))
    if isinstance(quote, str):
        return quote
    due = day_of(str(arguments.get("due") or "")) if arguments.get("due") else ""
    if arguments.get("due") and not due:
        return "When is it due? A day like \"friday\" or a date."
    return _run(context, "quote.accept", {"quote_id": quote.quote_id, "due_date": due or ""})


def _action_order_status(context, arguments: dict) -> str:
    """Tool order_status: an order marked ready, delivered or cancelled (order.status); delivered says what's still
    to be paid."""
    book = _book(context)
    if book is None:
        return "There's no business book here."
    status = str(arguments.get("status") or "").strip().capitalize()
    status = {"Done": "Delivered", "Finished": "Delivered", "Canceled": "Cancelled"}.get(status, status)
    if status not in ("Ready", "Delivered", "Cancelled"):
        return "Ready, delivered or cancelled?"
    names = _names(book)
    order = _one([o for o in book.orders if o.status not in DONE_ORDERS], str(arguments.get("order") or ""),
                 lambda o: f"{o.title} {names.get(o.customer_id, '')}".strip(), "order")
    if isinstance(order, str):
        return order
    return _run(context, "order.status", {"order_id": order.order_id, "status": status})


def register_business_voice_actions(registry: AssistantActionRegistry) -> None:
    """Registers list_quotes, list_orders, customer_details, add_customer, make_quote, accept_quote and order_status
    (domain business), the words that reach them (`WORDS`), and his customers' names and open quotes' and orders'
    titles (`_record_names`)."""
    s = {"type": "string"}

    def tool(name, description, properties, required, handler, phrases):
        """One business tool."""
        registry.register(AssistantAction(
            name=name, domain="business", description=description,
            parameters={"type": "object", "properties": properties, "required": required},
            handler=handler, trigger_phrases=phrases))

    tool("list_quotes", "The quotes still out (draft or sent), with customer and price.", {}, [],
         _action_list_quotes, ("quotes out", "quotes are out", "open quotes", "my quotes", "what quotes",
                               "quotes still out", "pending quotes"))
    tool("list_orders", "The open orders (not delivered or cancelled), soonest due first.", {}, [],
         _action_list_orders, ("open orders", "my orders", "what orders", "orders due", "orders are due",
                               "what am i building for"))
    tool("customer_details", "One customer's phone, email and notes, by name.",
         {"customer": {**s, "description": "the customer's name"}}, ["customer"], _action_customer_details,
         ("phone number", "email address", "contact info", "number for", "email for"))
    tool("add_customer", "Add a customer, with a phone, email or notes if given.",
         {"name": {**s, "description": "their name"}, "phone": s, "email": s, "notes": s}, ["name"],
         _action_add_customer, ("new customer", "add a customer", "add customer", "customer named"))
    tool("make_quote", "Make a quote: what it's for, the customer (one he has), how many, and a price if he set one.",
         {"title": {**s, "description": "what it's for, e.g. 'cedar chest'"},
          "customer": {**s, "description": "the customer's name, if any"},
          "quantity": {"type": "number"}, "price": {"type": "number", "description": "only if he named one"}},
         ["title"], _action_make_quote, ("make a quote", "quote for", "new quote", "write up a quote", "quote her",
                                         "quote him", "quote them"))
    tool("accept_quote", "A quote was accepted: it becomes an order, due when he says.",
         {"quote": {**s, "description": "the quote's title or the customer's name"},
          "due": {**s, "description": "when it's due, e.g. 'friday' or a date"}}, ["quote"], _action_accept_quote,
         ("accepted the quote", "took the quote", "said yes to the quote", "quote was accepted", "accepted my quote"))
    tool("order_status", "Mark an order ready, delivered or cancelled.",
         {"order": {**s, "description": "the order's title or the customer's name"},
          "status": {**s, "description": "ready, delivered or cancelled"}}, ["order", "status"], _action_order_status,
         ("delivered the", "mark it delivered", "marked delivered", "is ready for pickup", "cancelled the order",
          "canceled the order", "mark the order"))
    registry.register_domain_keywords("business", WORDS)
    registry.register_entity_names("business", _record_names, match_all_words=True)


def _record_names(context) -> list:
    """His customers' names and his open quotes' and orders' titles, so "mark the bench delivered" or "Dana accepted
    the quote" reaches these tools by the record it names."""
    book = _book(context)
    if book is None:
        return []
    return ([c.name for c in getattr(book, "customers", [])]
            + [q.title for q in getattr(book, "quotes", []) if q.status in OPEN_QUOTES]
            + [o.title for o in getattr(book, "orders", []) if o.status not in DONE_ORDERS])
