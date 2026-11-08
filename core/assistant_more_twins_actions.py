"""
core.assistant_more_twins_actions
===================================

More voice twins for what the screens change (DEC-0125, 2026-11-08), each
through the screen's own action kind (core/assistant_correction_actions.py
`_run`: the screen's checks and sentence, and "undo that"):

- remember_this ("remember that my truck takes 5W-30"): memory.add, said
  back so the person knows it's kept (it was only ever picked up after the
  reply, silently); never a password, PIN, code or card number;
- order_paid ("Customer A paid for the PCB order"): order.pay, the order by
  its title or its customer's name, the amount said, else what's still owed;
- delete_last_weigh_in ("delete my last weigh-in"): fitness.weigh_in_delete;
- rename_mission: mission.edit, the name only;
- remove_operating_line ("take early mornings out of my operating journal"):
  operating.remove (adding and rating stay quick commands).
"""

from __future__ import annotations

import re

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_correction_actions import _one, _run

# Passwords, PINs and card numbers stay screen-only (DEC-0125's one exception, Zac 2026-11-07): never kept by voice.
_SECRET = re.compile(r"\b(password|passcode|pass code|pin|pin number|gate code|door code|alarm code|lock code|"
                     r"security code|card number|cvv|cvc|social security|ssn|routing number|account number)s?\b",
                     re.IGNORECASE)
SECRET_REPLY = ("Passwords, PINs, codes and card numbers stay on a screen, never by voice. Add it in Passwords, "
                "where it's kept locked.")


def _action_remember_this(context, arguments: dict) -> str:
    """Tool remember_this: keeps a fact the person asked MIA to remember (memory.add) and says so; never a password,
    PIN, code or card number (those stay screen-only, in Passwords)."""
    text = " ".join(str(arguments.get("fact") or "").split())
    if not text:
        return "What should I remember?"
    if _SECRET.search(text):
        return SECRET_REPLY
    return _run(context, "memory.add", {"text": text})


def _action_order_paid(context, arguments: dict) -> str:
    """Tool order_paid: a payment on an order (order.pay), found by its title or its customer's name; the amount
    said, else what's still owed on it."""
    book = getattr(context, "business", None)
    if book is None:
        return "There are no orders here."
    said = " ".join(str(arguments.get("order") or "").lower().split())
    customers = {c.customer_id: c.name for c in getattr(book, "customers", [])}
    open_orders = [o for o in book.orders if o.status not in ("Delivered", "Cancelled")] or list(book.orders)
    order = _one(open_orders, said, lambda o: f"{o.title} {customers.get(o.customer_id, '')}".strip(), "order")
    if isinstance(order, str):
        return order
    amount = arguments.get("amount")
    if amount in (None, ""):
        from core.business_actions import _paid

        amount = round(order.price - _paid(context, order), 2)
        if amount <= 0:
            return f"{order.title} is already paid in full."
    return _run(context, "order.pay", {"order_id": order.order_id, "amount": amount})


def _action_delete_last_weigh_in(context, arguments: dict) -> str:
    """Tool delete_last_weigh_in: deletes the newest weigh-in (fitness.weigh_in_delete)."""
    fitness = getattr(context, "fitness", None)
    weigh_ins = fitness.weigh_ins() if fitness is not None else []
    if not weigh_ins:
        return "There are no weigh-ins to delete."
    return _run(context, "fitness.weigh_in_delete", {"entry_id": weigh_ins[-1]["id"]})


def _action_rename_mission(context, arguments: dict) -> str:
    """Tool rename_mission: a mission's new name (mission.edit, the name only)."""
    missions = getattr(context, "missions", None)
    if missions is None:
        return "There are no missions here."
    mission = _one(missions.all_missions(), arguments.get("mission"), lambda m: m.name, "mission")
    if isinstance(mission, str):
        return mission
    name = " ".join(str(arguments.get("name") or "").split())
    return _run(context, "mission.edit", {"mission_id": mission.mission_id, "name": name}) if name \
        else f"What should {mission.name} be called?"


def _action_remove_operating_line(context, arguments: dict) -> str:
    """Tool remove_operating_line: takes a line out of the Operating Journal (operating.remove)."""
    journal = getattr(context, "operating_journal", None)
    if journal is None:
        return "There's no operating journal here."
    line = _one(journal.lines, arguments.get("line"), lambda l: l["text"], "line")
    return line if isinstance(line, str) else _run(context, "operating.remove", {"line_id": line["id"]})


def register_more_twins_actions(registry: AssistantActionRegistry) -> None:
    """Registers remember_this (memory), order_paid (ledger), delete_last_weigh_in (workout), rename_mission
    (missions) and remove_operating_line (operating_journal), and the word "mission" for Missions."""
    registry.register_domain_keywords("missions", ("mission", "missions"))

    def tool(name, domain, description, properties, required, handler, phrases):
        """One tool, its parameters all strings."""
        registry.register(AssistantAction(
            name=name, domain=domain, description=description,
            parameters={"type": "object", "properties": {k: {"type": "string", "description": v}
                                                         for k, v in properties.items()}, "required": required},
            handler=handler, trigger_phrases=phrases))

    tool("remember_this", "memory", "Remember a fact the user asks MIA to remember about them or their things.",
         {"fact": "The fact, in a sentence, e.g. 'My truck takes 5W-30 oil.'"}, ["fact"], _action_remember_this,
         ("remember that", "remember this", "please remember", "don't forget that", "keep in mind that"))
    tool("order_paid", "ledger", "Record that a customer paid for an order (all of it, or the amount said).",
         {"order": "The order's title or the customer's name.", "amount": "What they paid, if said."}, ["order"],
         _action_order_paid, ("paid for the", "paid for their", "paid the rest", "paid in full", "payment for the"))
    tool("delete_last_weigh_in", "workout", "Delete the most recent weigh-in, when it was wrong.", {}, [],
         _action_delete_last_weigh_in, ("delete my last weigh-in", "delete the last weigh-in", "remove my last weigh-in",
                                        "that weigh-in was wrong", "delete that weigh-in"))
    tool("rename_mission", "missions", "Rename one of the user's missions.",
         {"mission": "Its name now.", "name": "The new name."}, ["mission", "name"], _action_rename_mission,
         ("rename the mission", "rename my mission", "rename mission"))
    tool("remove_operating_line", "operating_journal", "Take a line out of the user's Operating Journal.",
         {"line": "Words from the line."}, ["line"], _action_remove_operating_line,
         ("out of my operating journal", "from my operating journal", "off my operating journal"))
