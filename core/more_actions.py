"""
core.more_actions
===================

Every change the Journal, Workshop, Expeditions, Music and Files screens
make (Zac, 2026-10-16: "they are empty right now and just bring up a chat
with MIA"), as action kinds on the contract in core/actions.py, most from
the shared table in core/record_actions.py.

- Journal: `journal.add/edit/delete` (tags written "garden, ideas").
- Workshop: parts (`component.*`, `component.adjust`), materials
  (`material.*`, `material.adjust`), products (`product.*`,
  `product.adjust`), jobs (`job.*`, `job.use`, `job.make`), and the
  shop's own money: sales (`sale.add/delete`, a product sale takes it out
  of stock) and costs (`shop_expense.add/delete`).
- Expeditions: `expedition.*`, `trip.*`, `trip.status`, and the trip's
  packing list (`gear.add/toggle/remove`).
- Music: `playlist.add/rename/delete`, `playlist.add_track`,
  `playlist.remove_track`, `music.scan`.
- Files: `myfile.folder/rename/delete` (core/my_files.py; uploads go
  through /api/files/upload).

Every store here writes through atomic_write_text, so "undo" takes a
change back. Nothing here sends anything anywhere.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, field_dict, get, parse, record_form, record_kinds, show


def _lists():
    """The choice lists the record forms need (job statuses, shop expense categories, trip activity types), imported
    late so this module loads before those stores.
    """
    from core.job_manager import JOB_STATUSES
    from core.ledger_manager import EXPENSE_CATEGORIES
    from core.trip_manager import ACTIVITY_TYPES

    return tuple(JOB_STATUSES), tuple(EXPENSE_CATEGORIES), tuple(ACTIVITY_TYPES)


_JOB_STATUSES, _COSTS, _ACTIVITIES = _lists()
TRIP_STATUSES = ("planned", "active", "completed")

RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("component", "part", "component_id", "get_component", "add_component", "update_component",
           "delete_component", store="components", fields=(
               Field("name", "Name", "text", True),
               Field("category", "Kind", "text", say="kind"),
               Field("value", "Value", "text"),
               Field("package", "Package", "text"),
               Field("quantity", "How many", "int", default=0, say="count"),
               Field("location", "Where it's kept", "text", say="kept in"),
               Field("notes", "Notes", "textarea"),
           )),
    Record("material", "material", "material_id", "get_material", "add_material", "update_material",
           "delete_material", store="materials", fields=(
               Field("name", "Name", "text", True),
               Field("unit", "Unit (sheet, ft, kg...)", "text", say="unit"),
               Field("quantity_on_hand", "On hand", "amount", default=0.0, say="on hand"),
               Field("reorder_threshold", "Reorder at", "amount", default=0.0, say="reorder at"),
               Field("unit_cost", "Cost per unit", "money", default=0.0, say="cost per unit"),
               Field("supplier", "Supplier", "text"),
               Field("location", "Where it's kept", "text", say="kept in"),
               Field("notes", "Notes", "textarea"),
           )),
    Record("product", "product", "product_id", "get_product", "add_product", "update_product", "delete_product",
           store="products", fields=(
               Field("name", "Name", "text", True),
               Field("base_price", "Price", "money", default=0.0, say="price"),
               Field("quantity_in_stock", "In stock", "amount", default=0.0, say="in stock"),
               Field("description", "Description", "textarea"),
               Field("notes", "Notes", "textarea"),
           )),
    Record("job", "job", "job_id", "get_job", "add_job", "update_job", "delete_job", store="jobs", fields=(
        Field("name", "Name", "text", True),
        Field("status", "Status", "choice", options=_JOB_STATUSES, default="Planned", quiet_default=True),
        Field("labor_hours", "Hours worked", "amount", default=0.0, say="hours"),
        Field("description", "What it is", "textarea"),
        Field("notes", "Notes", "textarea"),
    )),
    Record("expedition", "expedition", "expedition_id", "get_expedition", "add_expedition", "update_expedition",
           "delete_expedition", store="expeditions", delete_note="Its trips stay, without an expedition.", fields=(
               Field("name", "Name", "text", True),
               Field("location", "Where", "text", say="in"),
               Field("start_date", "Starts", "date", say="from"),
               Field("end_date", "Ends", "date", say="to"),
               Field("notes", "Notes", "textarea"),
           )),
)}

# People & Pets (2026-10-17): the people and animals in your life.
RECORDS["person"] = Record("person", "person", "person_id", "get_person", "add_person", "update_person", "delete_person",
                           store="relationships", fields=(
                               Field("name", "Name", "text", True),
                               Field("relationship", "Who they are (sister, friend…)", "text", say="who"),
                               Field("birthday", "Birthday", "date"),
                               Field("email", "Email", "text"),
                               Field("favorite_things", "Favorite things", "textarea", say="favorites"),
                               Field("gift_ideas", "Gift ideas", "textarea", say="gift ideas"),
                               Field("notes", "Notes and memories", "textarea", say="notes"),
                           ))
RECORDS["pet"] = Record("pet", "pet", "pet_id", "get_pet", "add_pet", "update_pet", "delete_pet",
                        store="relationships", fields=(
                            Field("name", "Name", "text", True),
                            Field("species", "What they are (dog, cat…)", "text", say="species"),
                            Field("birthday", "Birthday or adoption day", "date", say="birthday"),
                            Field("medical_notes", "Vet and medical notes", "textarea", say="medical notes"),
                            Field("notes", "Notes", "textarea"),
                        ))

# The Toolbox's inventory (core/inventory_manager.py): what's kept around the house, how many, and where.
RECORDS["inventory"] = Record("inventory", "item", "item_id", "get_item", "add_item", "update_item", "delete_item",
                              store="inventory", fields=(
                                  Field("name", "Name", "text", True),
                                  Field("quantity", "How many", "int", default=0, say="count"),
                                  Field("category", "Kind", "text", say="kind"),
                                  Field("location", "Where it's kept", "text", say="kept in"),
                                  Field("notes", "Notes", "textarea"),
                              ))

# A project (core/project_manager.py): a build or job of the person's own, on the Projects page (core/web_projects.py);
# its budget is project.budget and its tasks task.* there.
RECORDS["project"] = Record("project", "project", "project_id", "get_project", "add_project", "update_project",
                            "delete_project", store="projects", fields=(
                                Field("name", "Name", "text", True),
                                Field("status", "Status", "choice", options=("Planning", "Active", "On Hold", "Complete"),
                                      default="Planning"),
                                Field("due_date", "Due", "date", say="due"),
                                Field("description", "What it is", "textarea", say="description"),
                            ))

# A trip belongs to an expedition (chosen on the page).
TRIP = Record("trip", "trip", "trip_id", "get_trip", "add_trip", "update_trip", "delete_trip", store="trips", fields=(
    Field("name", "Name", "text", True),
    Field("activity_type", "Activity", "choice", options=("", *_ACTIVITIES), default="", say="activity"),
    Field("start_date", "Starts", "date", say="from"),
    Field("end_date", "Ends", "date", say="to"),
    Field("notes", "Notes", "textarea"),
))

SALE = Record("sale", "sale", "entry_id", "get_revenue", "add_revenue", "", "delete_revenue", store="ledger", fields=(
    Field("amount", "Amount", "money", True),
    Field("description", "What sold", "text", say="for"),
    Field("date", "Date", "date"),
    Field("notes", "Notes", "textarea"),
), title_attrs=("description",))

SHOP_EXPENSE = Record("shop_expense", "shop cost", "entry_id", "get_expense", "add_expense", "", "delete_expense",
                      store="ledger", fields=(
                          Field("amount", "Amount", "money", True),
                          Field("category", "Kind", "choice", options=_COSTS, default="Other", say="kind"),
                          Field("description", "What for", "text", say="for"),
                          Field("date", "Date", "date"),
                          Field("notes", "Notes", "textarea"),
                      ), title_attrs=("description", "category"))


def forms() -> dict:
    """Every form these screens open (JSON-ready), a product's listing among them."""
    out = {key: record_form(r) for key, r in RECORDS.items()}
    out["trip"] = record_form(TRIP)
    out["sale"] = record_form(SALE)
    out["shop_expense"] = record_form(SHOP_EXPENSE)
    out["journal"] = {"noun": "entry", "id_param": "entry_id", "fields": [field_dict(f) for f in JOURNAL_FIELDS]}
    out["listing"] = {"noun": "listing", "id_param": "product_id", "fields": [
        field_dict(Field("platform", "Where (Etsy, web store, local...)", "text", True)),
        field_dict(Field("price", "Price there", "money", default=0.0)),
        field_dict(Field("status", "Status", "choice", options=("Active", "Inactive", "Sold Out"), default="Active")),
        field_dict(Field("url", "Link (optional)", "text")),
    ]}
    out["product_sale"] = {"noun": "sale", "id_param": "product_id", "fields": [
        field_dict(Field("quantity", "How many", "amount", True, default=1)),
        field_dict(Field("amount", "Total paid", "money", True)),
        field_dict(Field("date", "Date", "date"))]}
    return out


# ------------------------------------------------------------------ helpers


def _number(params, name: str, label: str, allow_negative: bool = True) -> float:
    """A number from the form (commas allowed), or ActionError naming the field; with allow_negative=False it must be
    more than 0.
    """
    try:
        value = float(str(params.get(name, "")).replace(",", "").strip())
    except ValueError:
        raise ActionError(f"{label} has to be a number.") from None
    if not allow_negative and value <= 0:
        raise ActionError(f"{label} has to be more than 0.")
    return value


def _call(fn, *args, **kwargs):
    """Calls a store method, turning the ValueError it raises for bad input into an ActionError the person sees."""
    try:
        return fn(*args, **kwargs)
    except ValueError as problem:
        raise ActionError(str(problem)) from None


def _qty(value: float) -> str:
    """A quantity without a trailing .0 (3, 2.5)."""
    return f"{value:g}"


# ------------------------------------------------------------------ journal

JOURNAL_FIELDS = (
    Field("title", "Title", "text", True),
    Field("body", "Entry", "textarea"),
    Field("tags", "Tags (comma separated)", "text"),
    Field("conditions", "Weather / conditions", "text"),
)


def tags_of(raw) -> list[str]:
    """Pure logic. "Garden, ideas ,garden" -> ["garden", "ideas"]."""
    out: list[str] = []
    for bit in str(raw or "").replace(";", ",").split(","):
        tag = bit.strip().lstrip("#").lower()
        if tag and tag not in out:
            out.append(tag)
    return out


def _journal_values(params, only_given: bool) -> dict:
    """The journal entry's fields read from the form (tags split from "garden, ideas"); with only_given, just the fields
    the form sent, for an edit.
    """
    values = {}
    for f in JOURNAL_FIELDS:
        if only_given and f.name not in params:
            continue
        values[f.name] = tags_of(params.get("tags")) if f.name == "tags" else parse(f, params.get(f.name))
    return values


def _entry(context, params):
    """The journal entry the form names, or ActionError when it's gone."""
    entry = _need(context, "journal").get_entry(str(params.get("entry_id") or ""))
    if entry is None:
        raise ActionError("That entry isn't there anymore.")
    return entry


def _journal_add_describe(context, params) -> str:
    """The sentence the approval card shows for adding a journal entry, naming the trip's log when it's one (Propose);
    raises ActionError when it can't be done."""
    v = _journal_values(params, False)
    trip = _journal_trip(context, params)
    return (f"Add the journal entry \"{v['title']}\"" + (f" to the {trip.name} log" if trip else "")
            + (f" (tagged {', '.join(v['tags'])})" if v["tags"] else ""))


def _journal_trip(context, params):
    """The trip a journal entry is a log of (`trip_id`, from a trip on the Expeditions page), None for a plain note;
    ActionError when the trip named isn't there."""
    trip_id = str(params.get("trip_id") or "").strip()
    if not trip_id:
        return None
    trip = getattr(_need(context, "trips"), "get_trip")(trip_id)
    if trip is None:
        raise ActionError("That trip isn't here any more.")
    return trip


def _journal_add(context, params) -> str:
    """Does adding the journal entry once it's approved (a trip's log when `trip_id` names one, with its weather in
    conditions), and says what happened."""
    v = _journal_values(params, False)
    trip = _journal_trip(context, params)
    _need(context, "journal").add_entry(**v, trip_id=trip.trip_id if trip else None)
    return f"Saved \"{v['title']}\" in your journal" + (f", on {trip.name}." if trip else ".")


def _journal_changes(context, params):
    """The entry and the fields an edit would actually change, as (field, old, new)."""
    entry = _entry(context, params)
    found = [(k, getattr(entry, k), new) for k, new in _journal_values(params, True).items()
             if (getattr(entry, k) or "") != (new or "")]
    return entry, found


def _journal_edit_describe(context, params) -> str:
    """The sentence the approval card shows for editing an entry: which parts change ("Nothing to change" when none do) (Propose); raises ActionError when it can't be done."""
    entry, found = _journal_changes(context, params)
    if not found:
        raise ActionError("Nothing to change.")
    names = {"title": "title", "body": "the entry", "tags": "tags", "conditions": "conditions"}
    return f"Change \"{entry.title}\": " + ", ".join(names[k] for k, _o, _n in found)


def _journal_edit(context, params) -> str:
    """Does the edit, writing only the changed fields once it's approved, and says what happened."""
    entry, found = _journal_changes(context, params)
    context.journal.update_entry(entry.entry_id, **{k: new for k, _o, new in found})
    return f"\"{entry.title}\" is updated."


def _journal_delete_describe(context, params) -> str:
    """The sentence the approval card shows for deleting an entry (Propose); raises ActionError when it can't be done."""
    return f"Delete the journal entry \"{_entry(context, params).title}\". Undo brings it back."


def _journal_delete(context, params) -> str:
    """Does deleting the entry (undo brings it back) once it's approved, and says what happened."""
    entry = _entry(context, params)
    context.journal.delete_entry(entry.entry_id)
    return f"Deleted \"{entry.title}\"."


# ------------------------------------------------------------------ stock up / down


def _adjuster(key: str, store: str, getter: str, adjust: str, attr: str, unit_attr: str = "", whole: bool = False,
              id_param: str = ""):
    """Builds the describe/execute pair for an `X.adjust` kind (component, material, product, inventory): add or take a delta from
    the item's count, showing the before and after. whole=True insists on whole numbers (parts); a zero change is
    refused. One builder so the adjust kinds behave the same. `id_param` names the item's parameter (its record's,
    "item_id" for the inventory; "<key>_id" by default).
    """
    def item(context, params):
        found = getattr(_need(context, store), getter)(str(params.get(id_param or f"{key}_id") or ""))
        if found is None:
            raise ActionError(f"That {key} isn't there anymore.")
        return found

    def delta(params):
        value = _number(params, "delta", "The change")
        if whole and value != int(value):
            raise ActionError("Use a whole number.")
        if value == 0:
            raise ActionError("Nothing to change.")
        return int(value) if whole else value

    def describe(context, params) -> str:
        it, d = item(context, params), delta(params)
        unit = f" {getattr(it, unit_attr)}" if unit_attr and getattr(it, unit_attr, "") else ""
        now = getattr(it, attr)
        return f"{'Add' if d > 0 else 'Take'} {_qty(abs(d))}{unit} {'to' if d > 0 else 'from'} {it.name} ({_qty(now)} → {_qty(now + d)})"

    def execute(context, params) -> str:
        it, d = item(context, params), delta(params)
        after = _call(getattr(getattr(context, store), adjust), getattr(it, id_param or f"{key}_id"), d)
        return f"{it.name}: {_qty(getattr(after, attr))} now."

    return describe, execute


# ------------------------------------------------------------------ jobs: use materials, make products


def _job(context, params):
    """The job the form names, or ActionError when it's gone."""
    job = _need(context, "jobs").get_job(str(params.get("job_id") or ""))
    if job is None:
        raise ActionError("That job isn't there anymore.")
    return job


def _job_use_describe(context, params) -> str:
    """The sentence the approval card shows for `job.use`: the material a job used and the shelf count before and after (Propose); raises ActionError when it can't be done."""
    job = _job(context, params)
    material = _need(context, "materials").get_material(str(params.get("material_id") or ""))
    if material is None:
        raise ActionError("Pick a material.")
    qty = _number(params, "quantity", "How much", allow_negative=False)
    unit = f" {material.unit}" if material.unit else ""
    return f"{job.name} used {_qty(qty)}{unit} of {material.name} (takes it off the shelf: {_qty(material.quantity_on_hand)} → {_qty(material.quantity_on_hand - qty)})"


def _job_use(context, params) -> str:
    """Does `job.use`, taking the material off the shelf once it's approved, and says what happened."""
    job = _job(context, params)
    qty = _number(params, "quantity", "How much", allow_negative=False)
    _call(context.jobs.consume_material, job.job_id, str(params.get("material_id")), qty)
    return f"Logged on {job.name}."


def _job_make_describe(context, params) -> str:
    """The sentence the approval card shows for `job.make`: what a job made and the stock before and after (Propose); raises ActionError when it can't be done."""
    job = _job(context, params)
    product = _need(context, "products").get_product(str(params.get("product_id") or ""))
    if product is None:
        raise ActionError("Pick a product.")
    qty = _number(params, "quantity", "How many", allow_negative=False)
    return f"{job.name} made {_qty(qty)} {product.name} (stock {_qty(product.quantity_in_stock)} → {_qty(product.quantity_in_stock + qty)})"


def _job_make(context, params) -> str:
    """Does `job.make`, adding the product to stock once it's approved, and says what happened."""
    job = _job(context, params)
    qty = _number(params, "quantity", "How many", allow_negative=False)
    _call(context.jobs.produce_product, job.job_id, str(params.get("product_id")), qty)
    return f"Logged on {job.name}."


# ------------------------------------------------------------------ sales and costs


def _money_record_describe(record: Record):
    """Builds the describe for adding a shop money record (sale or cost): its amount and what it was for."""
    def describe(context, params) -> str:
        values = {f.name: parse(f, params.get(f.name)) for f in record.fields}
        what = values.get("description") or values.get("category") or record.noun
        return f"Add the {record.noun} {show(record.fields[0], values['amount'])} ({what})"
    return describe


def _money_record_add(record: Record, method: str):
    """Builds the execute for adding a shop money record through the ledger method named."""
    def execute(context, params) -> str:
        values = {f.name: parse(f, params.get(f.name)) for f in record.fields}
        _call(getattr(_need(context, "ledger"), method), **values)
        return f"Added the {record.noun}."
    return execute


def _listing_product(context, params):
    """The product a listing change is for; ActionError when it's gone."""
    product = _need(context, "products").get_product(str(params.get("product_id") or ""))
    if product is None:
        raise ActionError("That product isn't there anymore.")
    return product


def _listing_values(params) -> tuple[str, float, str, str]:
    """(platform, price, status, link) for a new listing, checked: a platform is needed, the price is 0 or more, the
    status one of the product store's."""
    from core.product_manager import LISTING_STATUSES

    platform = " ".join(str(params.get("platform") or "").split())
    if not platform:
        raise ActionError("Where is it listed? (Etsy, a web store, local...)")
    price = _number({"price": params.get("price") or 0}, "price", "Price")
    if price < 0:
        raise ActionError("Price can't be negative.")
    status = str(params.get("status") or "Active").strip().title()
    if status not in LISTING_STATUSES:
        raise ActionError("Status: " + ", ".join(LISTING_STATUSES) + ".")
    return platform, price, status, str(params.get("url") or "").strip()


def _listing_add_describe(context, params) -> str:
    """The approval sentence for listing.add: "List Walnut bowl on Etsy at $40.00"."""
    from core.region import money

    product = _listing_product(context, params)
    platform, price, status, _ = _listing_values(params)
    return f"List {product.name} on {platform}" + (f" at {money(price)}" if price else "") + \
        (f" ({status.lower()})" if status != "Active" else "")


def _listing_add(context, params) -> str:
    """Does listing.add."""
    product = _listing_product(context, params)
    platform, price, status, url = _listing_values(params)
    context.products.add_listing(product.product_id, platform=platform, price=price, status=status, url=url)
    return f"{product.name} is listed on {platform}."


def _listing_of(context, params):
    """(the product, the listing the params name); ActionError when either is gone."""
    product = _listing_product(context, params)
    listing = next((li for li in product.listings if li.listing_id == str(params.get("listing_id") or "")), None)
    if listing is None:
        raise ActionError("That listing isn't there anymore.")
    return product, listing


def _listing_remove_describe(context, params) -> str:
    """The approval sentence for listing.remove: "Take Walnut bowl off Etsy"."""
    product, listing = _listing_of(context, params)
    return f"Take {product.name} off {listing.platform}"


def _listing_remove(context, params) -> str:
    """Does listing.remove: the listing comes off the product (the product stays)."""
    product, listing = _listing_of(context, params)
    context.products.remove_listing(product.product_id, listing.listing_id)
    return f"Took {product.name} off {listing.platform}."


def _sell_describe(context, params) -> str:
    """The sentence the approval card shows for `product.sell`: how many, the total paid and the stock before and after (Propose); raises ActionError when it can't be done."""
    product = get(context, RECORDS["product"], params)
    qty = _number(params, "quantity", "How many", allow_negative=False)
    amount = parse(Field("amount", "Total paid", "money", True), params.get("amount"))
    return f"Sold {_qty(qty)} {product.name} for {show(SALE.fields[0], amount)} (stock {_qty(product.quantity_in_stock)} → {_qty(product.quantity_in_stock - qty)})"


def _sell(context, params) -> str:
    """Does `product.sell`: records the sale in the ledger, which takes it out of stock once it's approved, and says what happened."""
    product = get(context, RECORDS["product"], params)
    qty = _number(params, "quantity", "How many", allow_negative=False)
    amount = parse(Field("amount", "Total paid", "money", True), params.get("amount"))
    day = parse(Field("date", "Date", "date"), params.get("date"))
    _call(_need(context, "ledger").record_sale, product.product_id, qty, amount,
          description=f"{_qty(qty)} × {product.name}", date=day)
    return f"Sale logged. {product.name}: {_qty(context.products.get_product(product.product_id).quantity_in_stock)} left."


def _ledger_delete(record: Record, getter: str, method: str):
    """Builds the describe/execute pair for deleting a sale or a shop cost from the ledger."""
    def item(context, params):
        found = getattr(_need(context, "ledger"), getter)(str(params.get("entry_id") or ""))
        if found is None:
            raise ActionError(f"That {record.noun} isn't there anymore.")
        return found

    def describe(context, params) -> str:
        it = item(context, params)
        return f"Delete the {record.noun} {show(record.fields[0], it.amount)} ({it.description or getattr(it, 'category', '')})"

    def execute(context, params) -> str:
        it = item(context, params)
        getattr(context.ledger, method)(it.entry_id)
        return f"Deleted the {record.noun}. Undo brings it back."

    return describe, execute


# ------------------------------------------------------------------ trips


def _expedition_of(context, params):
    """The expedition a new trip belongs to, or ActionError asking for one."""
    expedition = _need(context, "expeditions").get_expedition(str(params.get("expedition_id") or ""))
    if expedition is None:
        raise ActionError("Pick the expedition this trip belongs to.")
    return expedition


def _trip_values(params, only_given: bool) -> dict:
    """The trip's fields read from the form (only the ones sent, with only_given)."""
    return {f.name: parse(f, params.get(f.name)) for f in TRIP.fields if not only_given or f.name in params}


def _trip_add_describe(context, params) -> str:
    """The sentence the approval card shows for `trip.add`: the trip, its expedition, activity and start (Propose); raises ActionError when it can't be done."""
    expedition = _expedition_of(context, params)
    v = _trip_values(params, False)
    bits = [v["activity_type"].lower() if v["activity_type"] else "", f"from {show(TRIP.fields[2], v['start_date'])}" if v["start_date"] else ""]
    return f"Add the trip {v['name']} to {expedition.name}" + (f": {', '.join(b for b in bits if b)}" if any(bits) else "")


def _trip_add(context, params) -> str:
    """Does `trip.add` once it's approved, and says what happened."""
    expedition = _expedition_of(context, params)
    v = _trip_values(params, False)
    _call(_need(context, "trips").add_trip, expedition.expedition_id, **v)
    return f"Added {v['name']} to {expedition.name}."


def _trip(context, params):
    """The trip the form names (record_actions.get raises when it's gone)."""
    return get(context, TRIP, params)


def _trip_status_describe(context, params) -> str:
    """The sentence the approval card shows for `trip.status`: Start, Finish or move back to planned (the same status is refused) (Propose); raises ActionError when it can't be done."""
    trip = _trip(context, params)
    new = str(params.get("status") or "")
    if new not in TRIP_STATUSES:
        raise ActionError("A trip is planned, active or completed.")
    if new == trip.status:
        raise ActionError(f"{trip.name} is already {new}.")
    said = {"active": "Start", "completed": "Finish", "planned": "Move back to planned:"}[new]
    return f"{said} {trip.name}"


def _trip_status(context, params) -> str:
    """Does `trip.status` once it's approved, and says what happened."""
    trip = _trip(context, params)
    new = str(params.get("status"))
    context.trips.update_trip(trip.trip_id, status=new)
    return f"{trip.name} is {new}."


def _gear_index(trip, params) -> int:
    """Which packing-list item the form means, by its index, or ActionError when it's not on the list."""
    try:
        index = int(params.get("index"))
    except (TypeError, ValueError):
        raise ActionError("Pick an item on the list.") from None
    if not 0 <= index < len(trip.gear):
        raise ActionError("That item isn't on the list anymore.")
    return index


def _gear_add_describe(context, params) -> str:
    """The sentence the approval card shows for `gear.add` (Propose); raises ActionError when it can't be done."""
    trip = _trip(context, params)
    label = str(params.get("label") or "").strip()
    if not label:
        raise ActionError("What's the item?")
    return f"Add {label} to the packing list for {trip.name}"


def _gear_add(context, params) -> str:
    """Does `gear.add`, putting the item on the trip's packing list once it's approved, and says what happened."""
    trip = _trip(context, params)
    label = str(params.get("label") or "").strip()
    context.trips.add_gear_item(trip.trip_id, label)
    return f"{label} is on the list."


def _gear_toggle_describe(context, params) -> str:
    """The sentence the approval card shows for `gear.toggle`: Pack or Unpack the item (Propose); raises ActionError when it can't be done."""
    trip = _trip(context, params)
    item = trip.gear[_gear_index(trip, params)]
    return f"{'Unpack' if item.packed else 'Pack'} {item.label}"


def _gear_toggle(context, params) -> str:
    """Does `gear.toggle` once it's approved, and says what happened."""
    trip = _trip(context, params)
    index = _gear_index(trip, params)
    after = context.trips.toggle_gear_packed(trip.trip_id, index)
    item = after.gear[index]
    return f"{item.label}: {'packed' if item.packed else 'not packed'}."


def _gear_remove_describe(context, params) -> str:
    """The sentence the approval card shows for `gear.remove` (Propose); raises ActionError when it can't be done."""
    trip = _trip(context, params)
    return f"Take {trip.gear[_gear_index(trip, params)].label} off the list"


def _gear_remove(context, params) -> str:
    """Does `gear.remove` once it's approved, and says what happened."""
    trip = _trip(context, params)
    index = _gear_index(trip, params)
    label = trip.gear[index].label
    context.trips.remove_gear_item(trip.trip_id, index)
    return f"{label} is off the list."


# ------------------------------------------------------------------ music


def _playlist(context, params):
    """The playlist the form names, or ActionError when it's gone."""
    playlist = _need(context, "music").get_playlist(str(params.get("playlist_id") or ""))
    if playlist is None:
        raise ActionError("That playlist isn't there anymore.")
    return playlist


def _track(context, params):
    """The song the form names, or ActionError when it's no longer in the library."""
    track = _need(context, "music").get_track(str(params.get("track_id") or ""))
    if track is None:
        raise ActionError("That song isn't in the library anymore.")
    return track


def _name(params) -> str:
    """The name the form gives, or ActionError asking for one."""
    name = str(params.get("name") or "").strip()
    if not name:
        raise ActionError("Give it a name.")
    return name


def _playlist_add(context, params) -> str:
    """Does `playlist.add`, making the playlist once it's approved, and says what happened."""
    name = _name(params)
    _need(context, "music").create_playlist(name)
    return f"Made the playlist {name}."


def _playlist_rename(context, params) -> str:
    """Does `playlist.rename` once it's approved, and says what happened."""
    playlist, name = _playlist(context, params), _name(params)
    context.music.rename_playlist(playlist.playlist_id, name)
    return f"Renamed to {name}."


def _playlist_delete(context, params) -> str:
    """Does `playlist.delete` (the songs stay in the library) once it's approved, and says what happened."""
    playlist = _playlist(context, params)
    context.music.delete_playlist(playlist.playlist_id)
    return f"Deleted the playlist {playlist.name}. The songs stay in your library."


def _playlist_add_track_describe(context, params) -> str:
    """The sentence the approval card shows for `playlist.add_track` (a song already on it is refused) (Propose); raises ActionError when it can't be done."""
    playlist, track = _playlist(context, params), _track(context, params)
    if track.track_id in playlist.track_ids:
        raise ActionError(f"{track.title} is already on {playlist.name}.")
    return f"Add {track.title} to {playlist.name}"


def _playlist_add_track(context, params) -> str:
    """Does `playlist.add_track`, checking again first once it's approved, and says what happened."""
    _playlist_add_track_describe(context, params)
    playlist, track = _playlist(context, params), _track(context, params)
    context.music.add_track_to_playlist(playlist.playlist_id, track.track_id)
    return f"Added {track.title} to {playlist.name}."


def _playlist_remove_track(context, params) -> str:
    """Does `playlist.remove_track` once it's approved, and says what happened."""
    playlist, track = _playlist(context, params), _track(context, params)
    context.music.remove_track_from_playlist(playlist.playlist_id, track.track_id)
    return f"Took {track.title} off {playlist.name}."


def _scan(context, params) -> str:
    """Does `music.scan`: rescans the music folder and counts new, updated and gone songs (or says the folder is
    missing) once it's approved, and says what happened.
    """
    result = _need(context, "music").scan_library()
    if result.root_missing:
        return f"MIA couldn't find the music folder ({context.music.root_path}). Set it in Settings."
    return f"Library scanned: {result.added} new, {result.updated} updated, {result.removed} gone."


# ------------------------------------------------------------------ files


def _myfiles(context):
    """The person's My Files area (core/my_files.py), which keeps every path inside it."""
    from core.my_files import MyFiles

    return MyFiles.for_context(context)


def _folder_describe(context, params) -> str:
    """The sentence the approval card shows for `myfile.folder` (Propose); raises ActionError when it can't be done."""
    name = _name(params)
    where = str(params.get("path") or "")
    return f"Make the folder {name}" + (f" in {where}" if where else "")


def _folder(context, params) -> str:
    """Does `myfile.folder`, making the folder (a path outside My Files is refused) once it's approved, and says what happened."""
    try:
        made = _myfiles(context).make_folder(str(params.get("path") or ""), _name(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"Made {made}."


def _rename_describe(context, params) -> str:
    """The sentence the approval card shows for `myfile.rename` (Propose); raises ActionError when it can't be done."""
    return f"Rename {str(params.get('path') or '')} to {_name(params)}"


def _rename(context, params) -> str:
    """Does `myfile.rename` once it's approved, and says what happened."""
    try:
        _myfiles(context).rename(str(params.get("path") or ""), _name(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return "Renamed."


def _delete_describe(context, params) -> str:
    """The sentence the approval card shows for `myfile.delete`, saying whether it's a whole folder, and that it can't be undone (Propose); raises ActionError when it can't be done."""
    path = str(params.get("path") or "")
    try:
        kind = "folder and everything in it" if _myfiles(context).is_folder(path) else "file"
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"Delete the {kind} {path}. This can't be undone."


def _delete(context, params) -> str:
    """Does `myfile.delete` once it's approved, and says what happened."""
    try:
        _myfiles(context).delete(str(params.get("path") or ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return "Deleted."


# ------------------------------------------------------------------ expedition photos and files, uploaded songs


def _media_describe(context, params) -> str:
    """The sentence the approval card shows for deleting a photo or file from an expedition (it can't be undone) (Propose); raises ActionError when it can't be done."""
    from core.expedition_media import path_of

    try:
        path = path_of(context, str(params.get("expedition_id") or ""), str(params.get("ref") or ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"Delete {path.name} from this expedition. This can't be undone."


def _media_delete(context, params) -> str:
    """Does deleting the expedition's photo or file (core/expedition_media.py) once it's approved, and says what happened."""
    from core.expedition_media import delete

    try:
        return f"Deleted {delete(context, str(params.get('expedition_id') or ''), str(params.get('ref') or ''))}."
    except ValueError as problem:
        raise ActionError(str(problem)) from None


def _song_describe(context, params) -> str:
    """The sentence the approval card shows for deleting a song; only songs uploaded to MIA, never ones from the person's own music folder (Propose); raises ActionError when it can't be done."""
    track = _track(context, params)
    if not context.music.uploaded(track):
        raise ActionError(f"{track.title} is from your music folder; MIA only deletes songs you uploaded to her.")
    return f"Delete {track.title} from your library. This can't be undone."


def _song_delete(context, params) -> str:
    """Does deleting the uploaded song's file and its library entry, checking again first once it's approved, and says what happened."""
    from pathlib import Path

    _song_describe(context, params)
    track = _track(context, params)
    Path(track.file_path).unlink(missing_ok=True)
    context.music.delete_track(track.track_id)
    return f"Deleted {track.title}."


# ------------------------------------------------------------------ people: caught up


def _caught_describe(context, params) -> str:
    """The sentence the approval card shows for "caught up with" a person (Propose); raises ActionError when it can't be done."""
    person = get(context, RECORDS["person"], params)
    return f"Caught up with {person.name} today"


def _caught(context, params) -> str:
    """Does "caught up": sets the person's last contact to today and records it in the life-event history once it's approved, and says what happened."""
    from datetime import date as _date

    from core import life_events

    person = get(context, RECORDS["person"], params)
    context.relationships.update_person(person.person_id, last_contact=_date.today().isoformat())
    life_events.record(context.relationships, "caught_up", f"Caught up with {person.name}",
                       [f"person:{person.person_id}"], {"name": person.name})
    return f"Noted: you caught up with {person.name}."


def _memory(context, params):
    """The memory MIA keeps that the form names, or ActionError when it's gone."""
    store = getattr(context, "user_memories", None)
    memory = store.get_memory(str(params.get("memory_id") or "")) if store is not None else None
    if memory is None:
        raise ActionError("That memory isn't there anymore.")
    return memory


def _memory_fix_describe(context, params) -> str:
    """The sentence the approval card shows for correcting a memory to the new text (Propose); raises ActionError when it can't be done."""
    text = str(params.get("text") or "").strip()
    if not text:
        raise ActionError("Say what MIA should remember instead.")
    return f"Change what MIA remembers to: {text}"


def _memory_fix(context, params) -> str:
    """Does the correction once it's approved, and says what happened."""
    memory = _memory(context, params)
    context.user_memories.update_memory(memory.memory_id, str(params["text"]))
    return "Fixed. I'll remember it that way."


def _memory_add_describe(context, params) -> str:
    """The sentence the approval card shows for a new memory (Propose); raises ActionError when it can't be done."""
    text = str(params.get("text") or "").strip()
    if not text:
        raise ActionError("Say what MIA should remember.")
    return f"Remember: {text}"


def _memory_add(context, params) -> str:
    """Does adding the memory (one MIA already has is said so, not repeated) once it's approved, and says what happened."""
    made = _need(context, "user_memories").add_memory(str(params["text"]), str(params.get("category") or "Other"))
    return "I'll remember that." if made is not None else "I already remember that."


def _memory_forget(context, params) -> str:
    """Does forgetting the memory once it's approved, and says what happened."""
    memory = _memory(context, params)
    context.user_memories.delete_memory(memory.memory_id)
    return "Forgotten."


def _say(text: str):
    """A describe that always says the same text."""
    return lambda context, params: text


def _register() -> None:
    """Adds every action kind this module defines to ACTION_TYPES: the record kinds from the shared table
    (core/record_actions.py), the adjust kinds (parts, materials, products, the inventory), and the hand-written ones
    above (listings among them). Runs once, when
    this module is imported (core/actions.py imports it).
    """
    kinds = []
    for record in RECORDS.values():
        kinds += record_kinds(record)
    kinds += [k for k in record_kinds(TRIP) if not k.kind.endswith(".add")]
    for key, store, getter, adjust, attr, unit, whole in (
            ("component", "components", "get_component", "adjust_quantity", "quantity", "", True),
            ("material", "materials", "get_material", "adjust_quantity", "quantity_on_hand", "unit", False),
            ("product", "products", "get_product", "adjust_stock", "quantity_in_stock", "", False),
            ("inventory", "inventory", "get_item", "adjust_quantity", "quantity", "", True)):
        id_param = RECORDS[key].id_param if key in RECORDS else f"{key}_id"
        describe, execute = _adjuster(key, store, getter, adjust, attr, unit, whole, id_param)
        kinds.append(ActionType(f"{key}.adjust", "Adjust", {id_param: f"the {key}", "delta": "+ or - how many"},
                                describe, execute))
    sale_delete = _ledger_delete(SALE, "get_revenue", "delete_revenue")
    cost_delete = _ledger_delete(SHOP_EXPENSE, "get_expense", "delete_expense")
    kinds += [
        ActionType("journal.add", "Add", {**{f.name: f.label for f in JOURNAL_FIELDS}, "trip_id": "a trip (optional)"},
                   _journal_add_describe, _journal_add),
        ActionType("journal.edit", "Edit", {"entry_id": "the entry", **{f.name: f.label for f in JOURNAL_FIELDS}},
                   _journal_edit_describe, _journal_edit),
        ActionType("journal.delete", "Delete", {"entry_id": "the entry"}, _journal_delete_describe, _journal_delete),
        ActionType("job.use", "Used Material", {"job_id": "the job", "material_id": "the material", "quantity": "how much"},
                   _job_use_describe, _job_use),
        ActionType("job.make", "Made Product", {"job_id": "the job", "product_id": "the product", "quantity": "how many"},
                   _job_make_describe, _job_make),
        ActionType("sale.add", "Add Sale", {f.name: f.label for f in SALE.fields}, _money_record_describe(SALE),
                   _money_record_add(SALE, "add_revenue")),
        ActionType("sale.delete", "Delete", {"entry_id": "the sale"}, *sale_delete),
        ActionType("listing.add", "Add Listing", {"product_id": "the product", "platform": "where it's listed",
                                                  "price": "its price there", "status": "Active, Inactive or Sold Out",
                                                  "url": "a link (optional)"}, _listing_add_describe, _listing_add),
        ActionType("listing.remove", "Remove", {"product_id": "the product", "listing_id": "the listing"},
                   _listing_remove_describe, _listing_remove),
        ActionType("product.sell", "Sell", {"product_id": "the product", "quantity": "how many", "amount": "total paid",
                                            "date": "optional"}, _sell_describe, _sell),
        ActionType("shop_expense.add", "Add Cost", {f.name: f.label for f in SHOP_EXPENSE.fields},
                   _money_record_describe(SHOP_EXPENSE), _money_record_add(SHOP_EXPENSE, "add_expense")),
        ActionType("shop_expense.delete", "Delete", {"entry_id": "the cost"}, *cost_delete),
        ActionType("trip.add", "Add Trip", {"expedition_id": "the expedition", **{f.name: f.label for f in TRIP.fields}},
                   _trip_add_describe, _trip_add),
        ActionType("trip.status", "Status", {"trip_id": "the trip", "status": "planned, active or completed"},
                   _trip_status_describe, _trip_status),
        ActionType("gear.add", "Add", {"trip_id": "the trip", "label": "the item"}, _gear_add_describe, _gear_add),
        ActionType("gear.toggle", "Packed", {"trip_id": "the trip", "index": "which item"}, _gear_toggle_describe, _gear_toggle),
        ActionType("gear.remove", "Remove", {"trip_id": "the trip", "index": "which item"}, _gear_remove_describe, _gear_remove),
        ActionType("playlist.add", "New Playlist", {"name": "its name"},
                   lambda c, p: f"Make a playlist called {_name(p)}", _playlist_add),
        ActionType("playlist.rename", "Rename", {"playlist_id": "the playlist", "name": "new name"},
                   lambda c, p: f"Rename {_playlist(c, p).name} to {_name(p)}", _playlist_rename),
        ActionType("playlist.delete", "Delete", {"playlist_id": "the playlist"},
                   lambda c, p: f"Delete the playlist {_playlist(c, p).name} (the songs stay)", _playlist_delete),
        ActionType("playlist.add_track", "Add To Playlist", {"playlist_id": "the playlist", "track_id": "the song"},
                   _playlist_add_track_describe, _playlist_add_track),
        ActionType("playlist.remove_track", "Remove", {"playlist_id": "the playlist", "track_id": "the song"},
                   lambda c, p: f"Take {_track(c, p).title} off {_playlist(c, p).name}", _playlist_remove_track),
        ActionType("music.scan", "Scan Library", {}, _say("Look for new music in the music folder"), _scan),
        ActionType("person.caught_up", "Caught Up", {"person_id": "the person"}, _caught_describe, _caught),
        # What I Used (DEC-0029): fix or forget a memory MIA used.
        ActionType("memory.add", "Remember", {"text": "what to remember", "category": "optional"},
                   _memory_add_describe, _memory_add, True),
        ActionType("memory.fix", "Fix", {"memory_id": "the memory", "text": "what to remember instead"},
                   _memory_fix_describe, _memory_fix),
        ActionType("memory.forget", "Forget", {"memory_id": "the memory"},
                   lambda c, p: f"Forget: {_memory(c, p).text}", _memory_forget),
        ActionType("track.delete", "Delete", {"track_id": "an uploaded song"}, _song_describe, _song_delete),
        ActionType("expedition.media_delete", "Delete", {"expedition_id": "the expedition", "ref": "the photo or file"},
                   _media_describe, _media_delete),
        ActionType("myfile.folder", "New Folder", {"path": "where", "name": "its name"}, _folder_describe, _folder),
        ActionType("myfile.rename", "Rename", {"path": "the file", "name": "new name"}, _rename_describe, _rename),
        ActionType("myfile.delete", "Delete", {"path": "the file or folder"}, _delete_describe, _delete),
    ]
    # Children have the Journal and Music (core/child_accounts.CHILD_APPS).
    from dataclasses import replace

    for kind in kinds:
        if kind.kind.split(".")[0] in ("journal", "playlist", "person", "pet", "memory"):
            kind = replace(kind, child_ok=True)
        ACTION_TYPES[kind.kind] = kind


_register()
