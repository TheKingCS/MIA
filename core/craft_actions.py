"""
core.craft_actions
====================

The crafting recipes' actions (DEC-0030 phase B, core/craft_recipes.py),
on the action contract in core/actions.py: every one is proposed in
plain words, approved, run, and can be undone.

- `craft_recipe.add/edit/delete`: the recipe itself.
- `craft.receive`: what you bought for a recipe goes into Materials
  (quantities `q_<line>`, what you paid for each line `c_<line>`), and
  the total is recorded as a workshop expense.
- `craft.start`: a build (a Job with the recipe's id).
- `craft.step`: tick a build step (or untick it).
- `craft.finish`: use up the materials, record the hours, make the product.
- `craft.sell`: the build's product sold, linked to the build.
- `craft.cost`: another cost on a build (the dresser you bought to flip,
  stain, a delivery).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_kinds

CRAFT_RECIPE = Record(
    "craft_recipe", "recipe", "recipe_id", "get_recipe", "add_recipe", "update_recipe", "delete_recipe",
    store="craft_recipes", fields=(
        Field("name", "Name", "text", True),
        Field("category", "Kind (bench, planter, shelf…)", "text", say="kind"),
        Field("description", "Description", "textarea"),
        Field("dimensions", "Dimensions", "text"),
        Field("materials", "Materials, one per line (e.g. 4 board 2x4 8ft @ 3.98)", "textarea", say="materials"),
        Field("cut_list", "Cut list", "textarea"),
        Field("tools", "Tools", "textarea"),
        Field("steps", "Steps, one per line", "textarea", say="steps"),
        Field("est_hours", "About how many hours", "amount", say="hours"),
        Field("price", "Sells for (0 if it's not for sale)", "money", say="price"),
        Field("notes", "Notes", "textarea"),
    ))


def _money(x: float) -> str:
    from core.region import money

    return money(x)


def _recipe(context, params):
    recipe = _need(context, "craft_recipes").get_recipe(str(params.get("recipe_id") or ""))
    if recipe is None:
        raise ActionError("That recipe isn't there anymore.")
    return recipe


def _times(params) -> int:
    try:
        times = int(float(params.get("times") or 1))
    except (TypeError, ValueError):
        raise ActionError("How many has to be a whole number.") from None
    if times < 1 or times > 100:
        raise ActionError("Build between 1 and 100 at a time.")
    return times


def _num(params, name: str, label: str) -> float:
    raw = params.get(name)
    if raw in (None, ""):
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ActionError(f"{label} has to be a number.") from None
    if value < 0:
        raise ActionError(f"{label} can't be negative.")
    return value


def _qty(x: float) -> str:
    return f"{x:g}"


# ---------------------------------------------------------------- receive


def _bought(context, params) -> list[tuple]:
    """(line, quantity, paid) for every line with something bought."""
    recipe = _recipe(context, params)
    lines = recipe.lines
    out = []
    for i, line in enumerate(lines):
        q = _num(params, f"q_{i}", line.name)
        if q > 0:
            out.append((line, q, _num(params, f"c_{i}", f"What you paid for {line.name}")))
    if not out:
        raise ActionError("Nothing to receive: put in how much you bought.")
    return out


def _from_budget(params) -> bool:
    """Bought It filled from a receipt the inbox filed into the Budget:
    that money is already recorded there (core/receipt_match.py)."""
    return str(params.get("receipt") or "").startswith("expense:")


def _receive_describe(context, params) -> str:
    recipe = _recipe(context, params)
    bought = _bought(context, params)
    total = sum(p for _l, _q, p in bought)
    things = ", ".join(f"{_qty(q)} {(line.unit + ' ') if line.unit else ''}{line.name}" + (f" ({_money(p)})" if p else "")
                       for line, q, p in bought)
    if _from_budget(params):
        tail = " (already in your Budget from the receipt)"  # never counted twice
    else:
        tail = f"; record {_money(total)} as a workshop expense" if total and getattr(context, "ledger", None) is not None else ""
    return f"Receive for {recipe.name}: {things}{tail}"


def _receive(context, params) -> str:
    from core.craft_recipes import average_cost, key

    recipe = _recipe(context, params)
    bought = _bought(context, params)
    materials = _need(context, "materials")
    by_name = {key(m.name): m for m in materials.all_materials()}
    for line, q, paid in bought:
        each = paid / q if paid else (line.unit_cost or 0.0)
        found = by_name.get(key(line.name))
        if found is None:
            made = materials.add_material(line.name, unit=line.unit, unit_cost=each, quantity_on_hand=q)
            by_name[key(made.name)] = made
        else:
            cost = average_cost(found.quantity_on_hand, found.unit_cost, q, each) if each else found.unit_cost
            materials.update_material(found.material_id, unit_cost=cost)
            materials.adjust_quantity(found.material_id, q)
    total = round(sum(p for _l, _q, p in bought), 2)
    ledger = getattr(context, "ledger", None)
    if total and ledger is not None and not _from_budget(params):
        ledger.add_expense(total, "Materials", f"Materials for {recipe.name}")
    return f"Received {len(bought)} {'thing' if len(bought) == 1 else 'things'} into Materials" + \
        (f" ({_money(total)})." if total else ".")


# ---------------------------------------------------------------- builds


def _start_describe(context, params) -> str:
    from core.craft_recipes import check

    recipe = _recipe(context, params)
    times = _times(params)
    materials = getattr(context, "materials", None)
    short = len(check(recipe, materials.all_materials() if materials else [], times)["shopping"])
    what = f"{times} × {recipe.name}" if times > 1 else recipe.name
    return f"Start building {what}" + (f" (you're still short {short} {'thing' if short == 1 else 'things'})" if short else "")


def _start(context, params) -> str:
    recipe = _recipe(context, params)
    times = _times(params)
    jobs = _need(context, "jobs")
    name = f"{recipe.name} ×{times}" if times > 1 else recipe.name
    job = jobs.add_job(name, description=recipe.description, status="In Progress")
    jobs.update_job(job.job_id, recipe_id=recipe.recipe_id, times=times)
    return f"Started {name}. Tick the steps as you go."


def _build(context, params):
    job = _need(context, "jobs").get_job(str(params.get("job_id") or ""))
    if job is None:
        raise ActionError("That build isn't there anymore.")
    return job


def _build_recipe(context, job):
    recipe = getattr(context, "craft_recipes", None)
    found = recipe.get_recipe(job.recipe_id) if recipe is not None and job.recipe_id else None
    if found is None:
        raise ActionError("That build's recipe isn't there anymore.")
    return found


def _step_index(context, params) -> tuple:
    job = _build(context, params)
    steps = _build_recipe(context, job).step_list
    try:
        i = int(params.get("index"))
    except (TypeError, ValueError):
        raise ActionError("Which step?") from None
    if not 0 <= i < len(steps):
        raise ActionError("That step isn't in the recipe.")
    return job, i, steps[i]


def _step_describe(context, params) -> str:
    job, i, step = _step_index(context, params)
    return f"{'Untick' if i in job.steps_done else 'Done'}: {step}"


def _step(context, params) -> str:
    job, i, step = _step_index(context, params)
    done = [s for s in job.steps_done if s != i] if i in job.steps_done else sorted(job.steps_done + [i])
    context.jobs.update_job(job.job_id, steps_done=done)
    return f"{step}: {'done' if i in done else 'not done yet'}."


def _finishing(context, params) -> tuple:
    from core.craft_recipes import key

    job = _build(context, params)
    if job.status == "Complete":
        raise ActionError(f"{job.name} is already finished.")
    recipe = _build_recipe(context, job)
    hours = _num(params, "hours", "Hours")
    materials = _need(context, "materials")
    by_name = {key(m.name): m for m in materials.all_materials()}
    uses, missing = [], []
    for line in recipe.lines:
        found = by_name.get(key(line.name))
        (uses.append((found, line.quantity * job.times)) if found is not None else missing.append(line.name))
    return job, recipe, hours, uses, missing


def _finish_describe(context, params) -> str:
    job, recipe, hours, uses, missing = _finishing(context, params)
    used = ", ".join(f"{_qty(q)} {m.unit + ' ' if m.unit else ''}{m.name}" for m, q in uses) or "no materials"
    bits = [f"Finish {job.name}: use {used}"]
    if hours:
        bits.append(f"{_qty(hours)} hours")
    bits.append(f"make {job.times} {recipe.name}")
    note = f" ({', '.join(missing)} not in Materials, so not counted)" if missing else ""
    return "; ".join(bits) + note


def _finish(context, params) -> str:
    from core import life_events

    job, recipe, hours, uses, _missing = _finishing(context, params)
    jobs = context.jobs
    for material, quantity in uses:
        jobs.consume_material(job.job_id, material.material_id, quantity)
    products = _need(context, "products")
    product = products.get_product(recipe.product_id) if recipe.product_id else None
    if product is None:
        product = products.add_product(recipe.name, description=recipe.description, base_price=recipe.price)
        context.craft_recipes.update_recipe(recipe.recipe_id, product_id=product.product_id)
    jobs.produce_product(job.job_id, product.product_id, job.times)
    jobs.update_job(job.job_id, status="Complete", labor_hours=hours or job.labor_hours)
    life_events.record(jobs, "build_finished", f"Built {job.name}", [f"job:{job.job_id}", f"recipe:{recipe.recipe_id}"],
                       {"hours": hours, "recipe": recipe.name})
    return f"{job.name} is finished and in stock. Nice work."


def _sale(context, params) -> tuple:
    job = _build(context, params)
    amount = _num(params, "amount", "What it sold for")
    if amount <= 0:
        raise ActionError("Put in what it sold for.")
    product_id = next((p.product_id for p in job.products_produced), "")
    if not product_id:
        raise ActionError(f"Finish {job.name} first.")
    quantity = _num(params, "quantity", "How many") or 1
    return job, amount, product_id, quantity


def _sell_describe(context, params) -> str:
    job, amount, _p, quantity = _sale(context, params)
    return f"Sold {_qty(quantity)} from {job.name} for {_money(amount)}"


def _sell(context, params) -> str:
    job, amount, product_id, quantity = _sale(context, params)
    _need(context, "ledger").record_sale(product_id, quantity, amount, description=f"Sold {job.name}", job_id=job.job_id)
    return f"Sale recorded: {_money(amount)}."


def _cost(context, params) -> tuple:
    from core.ledger_manager import EXPENSE_CATEGORIES

    job = _build(context, params)
    amount = _num(params, "amount", "The cost")
    if amount <= 0:
        raise ActionError("Put in what it cost.")
    category = str(params.get("category") or "Materials")
    if category not in EXPENSE_CATEGORIES:
        raise ActionError(f"Pick one of: {', '.join(EXPENSE_CATEGORIES)}.")
    return job, amount, str(params.get("what") or "").strip() or category, category


def _cost_describe(context, params) -> str:
    job, amount, what, _c = _cost(context, params)
    return f"Add a cost to {job.name}: {what}, {_money(amount)}"


def _cost_add(context, params) -> str:
    job, amount, what, category = _cost(context, params)
    _need(context, "ledger").add_expense(amount, category, what, job_id=job.job_id)
    return f"Added {_money(amount)} to {job.name}."


def _photo_describe(context, params) -> str:
    from core.build_media import path_of

    job = _build(context, params)
    return f"Delete {path_of(context, job.job_id, str(params.get('name') or '')).name} from {job.name}"


def _photo_delete(context, params) -> str:
    from core.build_media import delete

    job = _build(context, params)
    return f"Deleted {delete(context, job.job_id, str(params.get('name') or ''))}."


def receive_form(rows: list[dict]) -> list[dict]:
    """The Bought It form for a shopping list: how many and what you paid, per line."""
    out = []
    for r in rows:
        unit = f" {r['unit']}" if r["unit"] else ""
        out.append({"name": f"q_{r['index']}", "label": f"{r['name']}: how many{unit}", "type": "amount",
                    "required": False, "options": [], "default": r["short"]})
        out.append({"name": f"c_{r['index']}", "label": f"{r['name']}: what you paid (total)", "type": "money",
                    "required": False, "options": [], "default": round(r["short"] * (r["unit_cost"] or 0), 2) or None})
    return out


def _register() -> None:
    kinds = list(record_kinds(CRAFT_RECIPE)) + [
        ActionType("craft.receive", "Bought It", {"recipe_id": "the recipe", "q_<line>": "how many", "c_<line>": "what you paid",
                                                   "receipt": "the receipt it came from (optional)"},
                   _receive_describe, _receive),
        ActionType("craft.start", "Start Build", {"recipe_id": "the recipe", "times": "how many"}, _start_describe, _start),
        ActionType("craft.step", "Done", {"job_id": "the build", "index": "the step"}, _step_describe, _step),
        ActionType("craft.finish", "Finish", {"job_id": "the build", "hours": "hours it took"}, _finish_describe, _finish),
        ActionType("craft.sell", "Sold It", {"job_id": "the build", "amount": "what it sold for", "quantity": "how many"},
                   _sell_describe, _sell),
        ActionType("craft.cost", "Add Cost", {"job_id": "the build", "amount": "what it cost", "what": "what it was",
                                              "category": "kind of cost"}, _cost_describe, _cost_add),
        ActionType("craft.photo_delete", "Delete", {"job_id": "the build", "name": "the photo"}, _photo_describe, _photo_delete),
    ]
    for kind in kinds:
        ACTION_TYPES[kind.kind] = kind


_register()
