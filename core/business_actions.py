"""
core.business_actions
=======================

Quotes, customers, orders and the portfolio (DEC-0030 phase C,
core/business_book.py) on the action contract: proposed in plain words,
approved, run, undoable.

- `customer.*`, `quote.*`, `order.*`: add, edit, delete.
- `quote.send` / `quote.decline`; `quote.accept` makes the order.
- `order.pay`: a payment (a deposit or the rest) into the workshop ledger,
  tied to the order's build when there is one.
- `order.build`: starts the recipe's build for the order (craft.start)
  and ties the payments so far to it.
- `order.status`: Ready / Delivered / Cancelled.
- `portfolio.feature`: feature a finished build first in the portfolio (or stop).
"""

from __future__ import annotations

from dataclasses import replace

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_kinds

CUSTOMER = Record("customer", "customer", "customer_id", "get_customer", "add_customer", "update_customer",
                  "delete_customer", store="business", fields=(
                      Field("name", "Name", "text", True), Field("phone", "Phone", "text"),
                      Field("email", "Email", "text"), Field("notes", "Notes (what they like, how they found you)", "textarea")))
QUOTE = Record("quote", "quote", "quote_id", "get_quote", "add_quote", "update_quote", "delete_quote",
               store="business", fields=(
                   Field("title", "What it's for", "text", True),
                   Field("customer_id", "Customer", "pick", options=("customers",), say="customer"),
                   Field("recipe_id", "From a recipe", "pick", options=("recipes",), say="recipe"),
                   Field("quantity", "How many", "int", default=1),
                   Field("labor_rate", "Your labor rate per hour", "money", say="labor rate"),
                   Field("margin", "Margin (%)", "amount", default=20),
                   Field("extras", "Extras (delivery, hardware…)", "money"),
                   Field("price", "Price (blank: the suggested price)", "money"),
                   Field("valid_until", "Good until", "date"),
                   Field("notes", "Notes", "textarea")))
ORDER = Record("order", "order", "order_id", "get_order", "add_order", "update_order", "delete_order",
               store="business", fields=(
                   Field("title", "What it is", "text", True),
                   Field("customer_id", "Customer", "pick", options=("customers",), say="customer"),
                   Field("recipe_id", "From a recipe", "pick", options=("recipes",), say="recipe"),
                   Field("quantity", "How many", "int", default=1),
                   Field("price", "Agreed price", "money", True),
                   Field("due_date", "Due", "date"),
                   Field("notes", "Notes", "textarea")))


def _money(x) -> str:
    from core.region import money

    return money(x)


def _book(context):
    return _need(context, "business")


def _who(context, customer_id: str) -> str:
    c = _book(context).get_customer(customer_id or "") if customer_id else None
    return f" for {c.name}" if c is not None else ""


def _check_refs(context, params) -> None:
    book = _book(context)
    if params.get("customer_id") and book.get_customer(str(params["customer_id"])) is None:
        raise ActionError("That customer isn't there anymore.")
    recipes = getattr(context, "craft_recipes", None)
    if params.get("recipe_id") and (recipes is None or recipes.get_recipe(str(params["recipe_id"])) is None):
        raise ActionError("That recipe isn't there anymore.")


def _plain(kind_describe, noun):
    """A record's sentence with names, not ids, for customer and recipe."""
    def describe(context, params):
        _check_refs(context, params)
        kind_describe(context, params)  # its own checks
        if "title" in params:
            return f"{noun} {params.get('title')}{_who(context, params.get('customer_id'))}"
        return kind_describe(context, params)
    return describe


def quote_figures(context, quote) -> dict:
    """What the quote comes to: materials and hours from its recipe, your
    rate, extras and margin; the suggested price and the price."""
    from core.business_book import suggested_price
    from core.craft_recipes import check

    materials = hours = 0.0
    recipes = getattr(context, "craft_recipes", None)
    recipe = recipes.get_recipe(quote.recipe_id) if recipes is not None and quote.recipe_id else None
    if recipe is not None:
        stock = context.materials.all_materials() if getattr(context, "materials", None) is not None else []
        materials = check(recipe, stock, quote.quantity)["est_material_cost"]
        hours = recipe.est_hours * quote.quantity
    rate = quote.labor_rate or float(context.config.get("workshop.labor_rate_per_hour", 0) or 0) \
        if getattr(context, "config", None) is not None else quote.labor_rate
    suggested = suggested_price(materials, hours, rate, quote.extras, quote.margin)
    return {"materials": round(materials, 2), "hours": hours, "rate": rate, "labor": round(hours * rate, 2),
            "extras": quote.extras, "margin": quote.margin, "suggested": suggested,
            "price": quote.price or suggested, "recipe": recipe.name if recipe is not None else ""}


def _quote(context, params):
    q = _book(context).get_quote(str(params.get("quote_id") or ""))
    if q is None:
        raise ActionError("That quote isn't there anymore.")
    return q


def _order(context, params):
    o = _book(context).get_order(str(params.get("order_id") or ""))
    if o is None:
        raise ActionError("That order isn't there anymore.")
    return o


def _quote_status(status):
    def describe(context, params):
        q = _quote(context, params)
        if q.status == "Accepted":
            raise ActionError(f"{q.title} is already accepted.")
        return f"Mark the quote {q.title}{_who(context, q.customer_id)} as {status.lower()}"

    def execute(context, params):
        q = _quote(context, params)
        _book(context).update_quote(q.quote_id, status=status)
        return f"{q.title}: {status.lower()}."
    return describe, execute


def _accept_describe(context, params) -> str:
    q = _quote(context, params)
    if q.status == "Accepted":
        raise ActionError(f"{q.title} is already accepted.")
    return f"Accept {q.title}{_who(context, q.customer_id)} at {_money(quote_figures(context, q)['price'])}: it becomes an order"


def _accept(context, params) -> str:
    q = _quote(context, params)
    book = _book(context)
    price = quote_figures(context, q)["price"]
    order = book.add_order(q.title, customer_id=q.customer_id, recipe_id=q.recipe_id, quantity=q.quantity,
                           price=price, due_date=str(params.get("due_date") or ""), notes=q.notes, quote_id=q.quote_id)
    book.update_quote(q.quote_id, status="Accepted", order_id=order.order_id)
    return f"Accepted. {q.title} is an order now."


def _amount(params) -> float:
    try:
        value = float(str(params.get("amount") or 0).replace(",", "").lstrip("$"))
    except ValueError:
        raise ActionError("The amount has to be a number.") from None
    if value <= 0:
        raise ActionError("Put in what they paid.")
    return round(value, 2)


def _paid(context, order) -> float:
    ledger = getattr(context, "ledger", None)
    if ledger is None:
        return 0.0
    return round(sum(r.amount for r in ledger.all_revenue() if r.entry_id in order.payment_ids), 2)


def _pay_describe(context, params) -> str:
    o = _order(context, params)
    amount = _amount(params)
    left = round(o.price - _paid(context, o), 2)
    what = "the deposit" if not o.payment_ids and amount < o.price else "a payment"
    return f"Record {what} of {_money(amount)} on {o.title}{_who(context, o.customer_id)}" + \
        (f" ({_money(max(0.0, left - amount))} left after it)" if o.price else "")


def _pay(context, params) -> str:
    o = _order(context, params)
    amount = _amount(params)
    ledger = _need(context, "ledger")
    job_id = o.job_ids[0] if o.job_ids else ""
    entry = ledger.add_revenue(amount, description=f"Order: {o.title}", job_id=job_id, notes=f"order:{o.order_id}")
    _book(context).update_order(o.order_id, payment_ids=o.payment_ids + [entry.entry_id])
    left = round(o.price - _paid(context, _order(context, params)), 2)
    return f"Payment recorded: {_money(amount)}." + (f" {_money(left)} left." if left > 0 else " Paid in full.")


def _build_describe(context, params) -> str:
    o = _order(context, params)
    if not o.recipe_id:
        raise ActionError(f"{o.title} has no recipe to build from. Edit it to pick one.")
    if o.job_ids:
        raise ActionError(f"{o.title} is already being built.")
    return f"Start building {o.title} ({o.quantity} from its recipe)"


def _build(context, params) -> str:
    from core.craft_actions import _start

    o = _order(context, params)
    jobs = _need(context, "jobs")
    before = {j.job_id for j in jobs.all_jobs()}
    _start(context, {"recipe_id": o.recipe_id, "times": o.quantity})
    job = next(j for j in jobs.all_jobs() if j.job_id not in before)
    ledger = getattr(context, "ledger", None)
    if ledger is not None:
        for entry_id in o.payment_ids:  # payments so far count for the build
            if ledger.get_revenue(entry_id) is not None:
                ledger.update_revenue(entry_id, job_id=job.job_id)
    _book(context).update_order(o.order_id, job_ids=[job.job_id], status="Building")
    return f"Started the build for {o.title}. It's in Workshop → Builds."


def _status_describe(context, params) -> str:
    from core.business_book import ORDER_STATUSES

    o = _order(context, params)
    status = str(params.get("status") or "")
    if status not in ORDER_STATUSES:
        raise ActionError(f"Pick one of: {', '.join(ORDER_STATUSES)}.")
    note = ""
    if status == "Delivered":
        left = round(o.price - _paid(context, o), 2)
        note = f" ({_money(left)} still to be paid)" if left > 0 else ""
    return f"Mark {o.title}{_who(context, o.customer_id)} as {status.lower()}{note}"


def _status(context, params) -> str:
    o = _order(context, params)
    status = str(params["status"])
    was = o.status
    _book(context).update_order(o.order_id, status=status)
    if status == "Delivered" and was != "Delivered" and o.job_ids:  # it left the shop: out of stock
        jobs, products = getattr(context, "jobs", None), getattr(context, "products", None)
        job = jobs.get_job(o.job_ids[0]) if jobs is not None else None
        if job is not None and products is not None:
            for made in job.products_produced:
                if products.get_product(made.product_id) is not None:
                    products.adjust_stock(made.product_id, -made.quantity_produced)
    return f"{o.title}: {status.lower()}."


def quote_email(context, quote) -> tuple[list[str], str, str]:
    """The email for a quote, from the person (they press Send): who it's
    to, the subject and the body. Only what the customer needs: what, how
    many, the size, the price, how long it's good for. Never the margin or
    the labor rate (core/craft_recipes.py keeps those)."""
    book = _book(context)
    customer = book.get_customer(quote.customer_id) if quote.customer_id else None
    f = quote_figures(context, quote)
    recipes = getattr(context, "craft_recipes", None)
    recipe = recipes.get_recipe(quote.recipe_id) if recipes is not None and quote.recipe_id else None
    profiles = getattr(context, "profiles", None)
    me = profiles.get_active_profile() if profiles is not None else None
    first = (customer.name.split(" ")[0] if customer is not None and customer.name else "")
    lines = [f"Hi {first}," if first else "Hi,", "", f"Thanks for asking about {quote.title}. Here's your quote:", ""]
    lines.append(f"- {quote.title}" + (f" ({quote.quantity} ×)" if quote.quantity > 1 else ""))
    if recipe is not None and recipe.dimensions:
        lines.append(f"- Size: {recipe.dimensions}")
    if recipe is not None and recipe.description:
        lines.append(f"- {recipe.description}")
    lines.append(f"- Price: {_money(f['price'])}" + (" total" if quote.quantity > 1 else ""))
    if quote.valid_until:
        from datetime import date

        try:
            lines.append(f"- Good until {date.fromisoformat(quote.valid_until):%B} {date.fromisoformat(quote.valid_until).day}")
        except ValueError:
            pass
    if quote.notes:
        lines += ["", quote.notes]
    lines += ["", "Let me know if you'd like to go ahead, or if you have any questions.", "", getattr(me, "name", "") or ""]
    to = [customer.email] if customer is not None and customer.email else []
    return to, f"Your quote: {quote.title}", "\n".join(lines).rstrip() + "\n"


def _email_describe(context, params) -> str:
    q = _quote(context, params)
    if getattr(context, "email_drafts", None) is None:
        raise ActionError("Email drafts aren't available here.")
    to, _s, _b = quote_email(context, q)
    who = f" to {to[0]}" if to else " (add the customer's email, or put it in when you send)"
    return f"Draft the quote email for {q.title}{who}. You press Send"


def _email(context, params) -> str:
    q = _quote(context, params)
    to, subject, body = quote_email(context, q)
    context.email_drafts.create(to, subject, body)
    return "Drafted. Check it, then Send, Copy or open it in your mail app."


def _feature_describe(context, params) -> str:
    job = _need(context, "jobs").get_job(str(params.get("job_id") or ""))
    if job is None:
        raise ActionError("That build isn't there anymore.")
    on = job.job_id in _book(context).featured
    return f"{'Stop featuring' if on else 'Feature'} {job.name} in the portfolio"


def _feature(context, params) -> str:
    job = _need(context, "jobs").get_job(str(params.get("job_id") or ""))
    on = _book(context).toggle_featured(job.job_id)
    return f"{job.name} is {'featured' if on else 'no longer featured'}."


def _register() -> None:
    kinds = list(record_kinds(CUSTOMER))
    for record, noun in ((QUOTE, "Add the quote"), (ORDER, "Add the order")):
        for k in record_kinds(record):
            kinds.append(replace(k, describe=_plain(k.describe, noun)) if k.kind.endswith(".add") else
                         replace(k, describe=(lambda d: lambda c, p: (_check_refs(c, p), d(c, p))[1])(k.describe))
                         if k.kind.endswith(".edit") else k)
    send, decline = _quote_status("Sent"), _quote_status("Declined")
    kinds += [
        ActionType("quote.send", "Sent", {"quote_id": "the quote"}, *send),
        ActionType("quote.decline", "Declined", {"quote_id": "the quote"}, *decline),
        ActionType("quote.email", "Email Quote", {"quote_id": "the quote"}, _email_describe, _email),
        ActionType("quote.accept", "Accepted", {"quote_id": "the quote", "due_date": "when it's due"}, _accept_describe, _accept),
        ActionType("order.pay", "Payment", {"order_id": "the order", "amount": "what they paid"}, _pay_describe, _pay),
        ActionType("order.build", "Start Build", {"order_id": "the order"}, _build_describe, _build),
        ActionType("order.status", "Status", {"order_id": "the order", "status": "Ready, Delivered or Cancelled"},
                   _status_describe, _status),
        ActionType("portfolio.feature", "Feature", {"job_id": "the build"}, _feature_describe, _feature),
    ]
    for kind in kinds:
        ACTION_TYPES[kind.kind] = kind


_register()
