"""
core.assistant_correction_actions
===================================

Fixing and planning by voice what the screens already let you change
(DEC-0125: every action has a voice twin; 2026-11-08). Measuring the
screens' 332 action kinds against her tools showed everyday ones with no
voice twin: taking something off the grocery list, clearing what's checked
off, a pantry item gone, rating or starring a recipe, planning a meal for a
day, changing or deleting a bill, deleting an expense. "Undo that" only
takes back the latest change.

Each tool finds the record by the words said and runs the screen's own
action kind (`_run`: propose then approve, as the quick commands do), so the
checks, the sentence and "undo that" are the screen's. A name that matches
more than one record, or none, is asked about; nothing is changed then.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.assistant_actions import AssistantAction, AssistantActionRegistry

_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_MEALS = ("breakfast", "lunch", "dinner", "snack")


def _run(context, kind: str, params: dict) -> str:
    """Runs one of the screen's action kinds for the person (propose, then approve) and says what happened, or why
    not; undoable."""
    from core.actions import ActionError

    actions = getattr(context, "actions", None)
    if actions is None:
        return "That isn't available on this MIA."
    try:
        done = actions.approve(context, actions.propose(context, kind, params, proposed_by="mia").proposal_id)
    except ActionError as problem:
        return str(problem)
    if done.status != "executed":
        return done.result or "That didn't work; nothing was changed."
    return f"{done.result} (Say “undo that” to take it back.)"


def _one(items, said: str, name_of, what: str):
    """Pure logic. The one item whose name holds the words said (an exact name wins), else a question as a str: which
    one, or that there's none."""
    said = " ".join(str(said or "").lower().split())
    if not said:
        return f"Which {what}?"
    exact = [i for i in items if name_of(i).lower() == said]
    found = exact or [i for i in items if said in name_of(i).lower()]
    if len(found) == 1:
        return found[0]
    if not found:
        return f"I don't see a {what} called {said}."
    return f"Which {what}? " + ", ".join(name_of(i) for i in found[:6]) + "."


def day_of(said: str, today: Optional[date] = None) -> Optional[str]:
    """Pure logic. A day said as words or a date, as an ISO date: "today", "tomorrow", a weekday (the next one, today
    counting), or "2026-11-12"; None when it isn't a day."""
    today = today or date.today()
    said = " ".join(str(said or "").lower().split()).removeprefix("on ").removeprefix("this ").removeprefix("next ")
    if said in ("", "today", "tonight"):
        return today.isoformat()
    if said == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if said in _DAYS:
        return (today + timedelta(days=(_DAYS.index(said) - today.weekday()) % 7)).isoformat()
    try:
        return date.fromisoformat(said).isoformat()
    except ValueError:
        return None


def _kitchen(context):
    """The kitchen store, or None."""
    return getattr(context, "kitchen", None)


def _action_remove_grocery_item(context, arguments: dict) -> str:
    """Tool remove_grocery_item: takes the named item off the grocery list (grocery.delete)."""
    kitchen = _kitchen(context)
    if kitchen is None:
        return "There's no grocery list here."
    item = _one(kitchen.all_grocery_items(), arguments.get("item"), lambda i: i.name, "grocery item")
    return item if isinstance(item, str) else _run(context, "grocery.delete", {"item_id": item.item_id})


def _action_clear_checked_groceries(context, arguments: dict) -> str:
    """Tool clear_checked_groceries: clears what's checked off the grocery list (grocery.clear_checked)."""
    return _run(context, "grocery.clear_checked", {})


def _action_remove_pantry_item(context, arguments: dict) -> str:
    """Tool remove_pantry_item: removes the named item from the pantry for good (pantry.delete); running out is a
    quantity of 0 instead (update_pantry_item)."""
    kitchen = _kitchen(context)
    if kitchen is None:
        return "There's no pantry here."
    item = _one(kitchen.all_pantry_items(), arguments.get("item"), lambda i: i.name, "pantry item")
    return item if isinstance(item, str) else _run(context, "pantry.delete", {"item_id": item.item_id})


def _recipe(context, said):
    """The recipe named, or a question as a str."""
    kitchen = _kitchen(context)
    if kitchen is None:
        return "There are no recipes here."
    return _one(kitchen.all_recipes(), said, lambda r: r.name, "recipe")


def _action_rate_recipe(context, arguments: dict) -> str:
    """Tool rate_recipe: the person's 1 to 5 stars for a recipe (recipe.rate)."""
    recipe = _recipe(context, arguments.get("recipe"))
    if isinstance(recipe, str):
        return recipe
    try:
        stars = int(float(str(arguments.get("stars") or "").split()[0]))
    except (ValueError, IndexError):
        return f"How many stars for {recipe.name}, 1 to 5?"
    return _run(context, "recipe.rate", {"recipe_id": recipe.recipe_id, "rating": max(0, min(5, stars))})


def _action_favorite_recipe(context, arguments: dict) -> str:
    """Tool favorite_recipe: stars a recipe as a favorite, or takes the star off (recipe.favorite)."""
    recipe = _recipe(context, arguments.get("recipe"))
    if isinstance(recipe, str):
        return recipe
    off = str(arguments.get("favorite", "yes")).strip().lower() in ("no", "false", "off", "remove", "unfavorite")
    return _run(context, "recipe.favorite", {"recipe_id": recipe.recipe_id, "favorite": not off})


def _action_plan_meal(context, arguments: dict) -> str:
    """Tool plan_meal: puts a recipe on a day's breakfast, lunch, dinner or snack in the meal plan (meal.plan)."""
    recipe = _recipe(context, arguments.get("recipe"))
    if isinstance(recipe, str):
        return recipe
    day = day_of(str(arguments.get("day") or ""))
    if day is None:
        return f"Which day for {recipe.name}?"
    meal = str(arguments.get("meal") or "dinner").strip().lower()
    if meal not in _MEALS:
        meal = "dinner"
    servings = arguments.get("servings") or 1
    return _run(context, "meal.plan", {"date": day, "meal": meal, "recipe_id": recipe.recipe_id, "servings": servings})


def _bill(context, said):
    """The bill named, or a question as a str."""
    budget = getattr(context, "budget", None)
    if budget is None:
        return "There are no bills here."
    return _one(budget.all_bills(), said, lambda b: b.name, "bill")


def _action_change_bill(context, arguments: dict) -> str:
    """Tool change_bill: a bill's new amount and/or due date (bill.edit); only what was said changes."""
    bill = _bill(context, arguments.get("bill"))
    if isinstance(bill, str):
        return bill
    params = {"bill_id": bill.bill_id}
    if arguments.get("amount") not in (None, ""):
        params["amount"] = arguments["amount"]
    if arguments.get("due_date") not in (None, ""):
        due = day_of(str(arguments["due_date"]))
        if due is None:
            return f"When is {bill.name} due now? A date, please."
        params["due_date"] = due
    if len(params) == 1:
        return f"What changed about {bill.name}: the amount or the due date?"
    return _run(context, "bill.edit", params)


def _action_delete_bill(context, arguments: dict) -> str:
    """Tool delete_bill: removes a bill the person no longer has (bill.delete)."""
    bill = _bill(context, arguments.get("bill"))
    return bill if isinstance(bill, str) else _run(context, "bill.delete", {"bill_id": bill.bill_id})


def _action_delete_expense(context, arguments: dict) -> str:
    """Tool delete_expense: deletes a logged expense, the newest one whose description or payee holds the words
    said (expense.delete)."""
    budget = getattr(context, "budget", None)
    if budget is None:
        return "There are no expenses here."
    said = " ".join(str(arguments.get("expense") or "").lower().split())
    if not said:
        return "Which expense?"
    found = [e for e in budget.all_expenses() if said in f"{e.description} {getattr(e, 'payee', '')}".lower()]
    if not found:
        return f"I don't see an expense for {said}."
    newest = max(found, key=lambda e: e.date or "")
    return _run(context, "expense.delete", {"entry_id": newest.entry_id})


def register_correction_actions(registry: AssistantActionRegistry) -> None:
    """Registers the groceries, pantry, recipe, meal plan, bill and expense corrections (each in its area's domain)."""
    def tool(name, domain, description, properties, required, handler, phrases):
        """One tool, its parameters all strings."""
        registry.register(AssistantAction(
            name=name, domain=domain, description=description,
            parameters={"type": "object", "properties": {k: {"type": "string", "description": v}
                                                         for k, v in properties.items()}, "required": required},
            handler=handler, trigger_phrases=phrases))

    tool("remove_grocery_item", "groceries", "Take an item off the grocery list.", {"item": "The item, e.g. milk."},
         ["item"], _action_remove_grocery_item,
         ("off the grocery list", "off the list", "remove from the grocery list", "don't need", "take off the list"))
    tool("clear_checked_groceries", "groceries", "Clear the items already checked off the grocery list.", {}, [],
         _action_clear_checked_groceries, ("clear the checked", "clear checked", "clear what's checked",
                                           "clear the grocery list"))
    tool("remove_pantry_item", "groceries", "Remove an item from the pantry list for good (not when it's just run out).",
         {"item": "The item, e.g. flour."}, ["item"], _action_remove_pantry_item,
         # Not "we're out of": being out is a quantity of 0 (update_pantry_item), the item kept for restocking.
         ("out of the pantry", "from the pantry", "off the pantry"))
    tool("rate_recipe", "kitchen", "Rate a recipe 1 to 5 stars.", {"recipe": "The recipe's name.",
                                                                    "stars": "1 to 5."}, ["recipe", "stars"],
         _action_rate_recipe, ("rate the", "stars for the", "give the recipe"))
    tool("favorite_recipe", "kitchen", "Mark a recipe as a favorite, or take it off the favorites.",
         {"recipe": "The recipe's name.", "favorite": "yes, or no to take it off."}, ["recipe"],
         _action_favorite_recipe, ("a favorite", "a favourite", "to my favorites", "off my favorites",
                                   "favorite recipe", "favourite recipe"))
    tool("plan_meal", "kitchen", "Put a recipe in the meal plan for a day's breakfast, lunch, dinner or snack.",
         {"recipe": "The recipe's name.", "day": "today, tomorrow, a weekday, or a date.",
          "meal": "breakfast, lunch, dinner or snack.", "servings": "How many, if said."}, ["recipe", "day"],
         _action_plan_meal, ("plan the", "for dinner", "for lunch", "for breakfast", "meal plan", "plan dinner",
                             "plan lunch"))
    tool("change_bill", "budget", "Change a bill's amount or due date.",
         {"bill": "The bill, e.g. electric.", "amount": "The new amount, if it changed.",
          "due_date": "The new due date, if it changed."}, ["bill"], _action_change_bill,
         ("bill is now", "bill went up", "bill went down", "bill is due", "change the bill", "bill changed"))
    tool("delete_bill", "budget", "Remove a bill the user no longer has.", {"bill": "The bill's name."}, ["bill"],
         _action_delete_bill, ("delete the bill", "remove the bill", "cancel the bill", "no longer have the bill",
                               "cancelled my"))
    tool("delete_expense", "budget", "Delete an expense that was logged by mistake.",
         {"expense": "Words from what it was or who was paid."}, ["expense"], _action_delete_expense,
         ("delete the expense", "remove the expense", "delete that expense", "logged by mistake"))
