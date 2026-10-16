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
    """Every form these screens open (JSON-ready)."""
    out = {key: record_form(r) for key, r in RECORDS.items()}
    out["trip"] = record_form(TRIP)
    out["sale"] = record_form(SALE)
    out["shop_expense"] = record_form(SHOP_EXPENSE)
    out["journal"] = {"noun": "entry", "id_param": "entry_id", "fields": [field_dict(f) for f in JOURNAL_FIELDS]}
    out["product_sale"] = {"noun": "sale", "id_param": "product_id", "fields": [
        field_dict(Field("quantity", "How many", "amount", True, default=1)),
        field_dict(Field("amount", "Total paid", "money", True)),
        field_dict(Field("date", "Date", "date"))]}
    return out


# ------------------------------------------------------------------ helpers


def _number(params, name: str, label: str, allow_negative: bool = True) -> float:
    try:
        value = float(str(params.get(name, "")).replace(",", "").strip())
    except ValueError:
        raise ActionError(f"{label} has to be a number.") from None
    if not allow_negative and value <= 0:
        raise ActionError(f"{label} has to be more than 0.")
    return value


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as problem:
        raise ActionError(str(problem)) from None


def _qty(value: float) -> str:
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
    values = {}
    for f in JOURNAL_FIELDS:
        if only_given and f.name not in params:
            continue
        values[f.name] = tags_of(params.get("tags")) if f.name == "tags" else parse(f, params.get(f.name))
    return values


def _entry(context, params):
    entry = _need(context, "journal").get_entry(str(params.get("entry_id") or ""))
    if entry is None:
        raise ActionError("That entry isn't there anymore.")
    return entry


def _journal_add_describe(context, params) -> str:
    v = _journal_values(params, False)
    return f"Add the journal entry \"{v['title']}\"" + (f" (tagged {', '.join(v['tags'])})" if v["tags"] else "")


def _journal_add(context, params) -> str:
    v = _journal_values(params, False)
    _need(context, "journal").add_entry(**v)
    return f"Saved \"{v['title']}\" in your journal."


def _journal_changes(context, params):
    entry = _entry(context, params)
    found = [(k, getattr(entry, k), new) for k, new in _journal_values(params, True).items()
             if (getattr(entry, k) or "") != (new or "")]
    return entry, found


def _journal_edit_describe(context, params) -> str:
    entry, found = _journal_changes(context, params)
    if not found:
        raise ActionError("Nothing to change.")
    names = {"title": "title", "body": "the entry", "tags": "tags", "conditions": "conditions"}
    return f"Change \"{entry.title}\": " + ", ".join(names[k] for k, _o, _n in found)


def _journal_edit(context, params) -> str:
    entry, found = _journal_changes(context, params)
    context.journal.update_entry(entry.entry_id, **{k: new for k, _o, new in found})
    return f"\"{entry.title}\" is updated."


def _journal_delete_describe(context, params) -> str:
    return f"Delete the journal entry \"{_entry(context, params).title}\". Undo brings it back."


def _journal_delete(context, params) -> str:
    entry = _entry(context, params)
    context.journal.delete_entry(entry.entry_id)
    return f"Deleted \"{entry.title}\"."


# ------------------------------------------------------------------ stock up / down


def _adjuster(key: str, store: str, getter: str, adjust: str, attr: str, unit_attr: str = "", whole: bool = False):
    def item(context, params):
        found = getattr(_need(context, store), getter)(str(params.get(f"{key}_id") or ""))
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
        after = _call(getattr(getattr(context, store), adjust), getattr(it, f"{key}_id"), d)
        return f"{it.name}: {_qty(getattr(after, attr))} now."

    return describe, execute


# ------------------------------------------------------------------ jobs: use materials, make products


def _job(context, params):
    job = _need(context, "jobs").get_job(str(params.get("job_id") or ""))
    if job is None:
        raise ActionError("That job isn't there anymore.")
    return job


def _job_use_describe(context, params) -> str:
    job = _job(context, params)
    material = _need(context, "materials").get_material(str(params.get("material_id") or ""))
    if material is None:
        raise ActionError("Pick a material.")
    qty = _number(params, "quantity", "How much", allow_negative=False)
    unit = f" {material.unit}" if material.unit else ""
    return f"{job.name} used {_qty(qty)}{unit} of {material.name} (takes it off the shelf: {_qty(material.quantity_on_hand)} → {_qty(material.quantity_on_hand - qty)})"


def _job_use(context, params) -> str:
    job = _job(context, params)
    qty = _number(params, "quantity", "How much", allow_negative=False)
    _call(context.jobs.consume_material, job.job_id, str(params.get("material_id")), qty)
    return f"Logged on {job.name}."


def _job_make_describe(context, params) -> str:
    job = _job(context, params)
    product = _need(context, "products").get_product(str(params.get("product_id") or ""))
    if product is None:
        raise ActionError("Pick a product.")
    qty = _number(params, "quantity", "How many", allow_negative=False)
    return f"{job.name} made {_qty(qty)} {product.name} (stock {_qty(product.quantity_in_stock)} → {_qty(product.quantity_in_stock + qty)})"


def _job_make(context, params) -> str:
    job = _job(context, params)
    qty = _number(params, "quantity", "How many", allow_negative=False)
    _call(context.jobs.produce_product, job.job_id, str(params.get("product_id")), qty)
    return f"Logged on {job.name}."


# ------------------------------------------------------------------ sales and costs


def _money_record_describe(record: Record):
    def describe(context, params) -> str:
        values = {f.name: parse(f, params.get(f.name)) for f in record.fields}
        what = values.get("description") or values.get("category") or record.noun
        return f"Add the {record.noun} {show(record.fields[0], values['amount'])} ({what})"
    return describe


def _money_record_add(record: Record, method: str):
    def execute(context, params) -> str:
        values = {f.name: parse(f, params.get(f.name)) for f in record.fields}
        _call(getattr(_need(context, "ledger"), method), **values)
        return f"Added the {record.noun}."
    return execute


def _sell_describe(context, params) -> str:
    product = get(context, RECORDS["product"], params)
    qty = _number(params, "quantity", "How many", allow_negative=False)
    amount = parse(Field("amount", "Total paid", "money", True), params.get("amount"))
    return f"Sold {_qty(qty)} {product.name} for {show(SALE.fields[0], amount)} (stock {_qty(product.quantity_in_stock)} → {_qty(product.quantity_in_stock - qty)})"


def _sell(context, params) -> str:
    product = get(context, RECORDS["product"], params)
    qty = _number(params, "quantity", "How many", allow_negative=False)
    amount = parse(Field("amount", "Total paid", "money", True), params.get("amount"))
    day = parse(Field("date", "Date", "date"), params.get("date"))
    _call(_need(context, "ledger").record_sale, product.product_id, qty, amount,
          description=f"{_qty(qty)} × {product.name}", date=day)
    return f"Sale logged. {product.name}: {_qty(context.products.get_product(product.product_id).quantity_in_stock)} left."


def _ledger_delete(record: Record, getter: str, method: str):
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
    expedition = _need(context, "expeditions").get_expedition(str(params.get("expedition_id") or ""))
    if expedition is None:
        raise ActionError("Pick the expedition this trip belongs to.")
    return expedition


def _trip_values(params, only_given: bool) -> dict:
    return {f.name: parse(f, params.get(f.name)) for f in TRIP.fields if not only_given or f.name in params}


def _trip_add_describe(context, params) -> str:
    expedition = _expedition_of(context, params)
    v = _trip_values(params, False)
    bits = [v["activity_type"].lower() if v["activity_type"] else "", f"from {show(TRIP.fields[2], v['start_date'])}" if v["start_date"] else ""]
    return f"Add the trip {v['name']} to {expedition.name}" + (f": {', '.join(b for b in bits if b)}" if any(bits) else "")


def _trip_add(context, params) -> str:
    expedition = _expedition_of(context, params)
    v = _trip_values(params, False)
    _call(_need(context, "trips").add_trip, expedition.expedition_id, **v)
    return f"Added {v['name']} to {expedition.name}."


def _trip(context, params):
    return get(context, TRIP, params)


def _trip_status_describe(context, params) -> str:
    trip = _trip(context, params)
    new = str(params.get("status") or "")
    if new not in TRIP_STATUSES:
        raise ActionError("A trip is planned, active or completed.")
    if new == trip.status:
        raise ActionError(f"{trip.name} is already {new}.")
    said = {"active": "Start", "completed": "Finish", "planned": "Move back to planned:"}[new]
    return f"{said} {trip.name}"


def _trip_status(context, params) -> str:
    trip = _trip(context, params)
    new = str(params.get("status"))
    context.trips.update_trip(trip.trip_id, status=new)
    return f"{trip.name} is {new}."


def _gear_index(trip, params) -> int:
    try:
        index = int(params.get("index"))
    except (TypeError, ValueError):
        raise ActionError("Pick an item on the list.") from None
    if not 0 <= index < len(trip.gear):
        raise ActionError("That item isn't on the list anymore.")
    return index


def _gear_add_describe(context, params) -> str:
    trip = _trip(context, params)
    label = str(params.get("label") or "").strip()
    if not label:
        raise ActionError("What's the item?")
    return f"Add {label} to the packing list for {trip.name}"


def _gear_add(context, params) -> str:
    trip = _trip(context, params)
    label = str(params.get("label") or "").strip()
    context.trips.add_gear_item(trip.trip_id, label)
    return f"{label} is on the list."


def _gear_toggle_describe(context, params) -> str:
    trip = _trip(context, params)
    item = trip.gear[_gear_index(trip, params)]
    return f"{'Unpack' if item.packed else 'Pack'} {item.label}"


def _gear_toggle(context, params) -> str:
    trip = _trip(context, params)
    index = _gear_index(trip, params)
    after = context.trips.toggle_gear_packed(trip.trip_id, index)
    item = after.gear[index]
    return f"{item.label}: {'packed' if item.packed else 'not packed'}."


def _gear_remove_describe(context, params) -> str:
    trip = _trip(context, params)
    return f"Take {trip.gear[_gear_index(trip, params)].label} off the list"


def _gear_remove(context, params) -> str:
    trip = _trip(context, params)
    index = _gear_index(trip, params)
    label = trip.gear[index].label
    context.trips.remove_gear_item(trip.trip_id, index)
    return f"{label} is off the list."


# ------------------------------------------------------------------ music


def _playlist(context, params):
    playlist = _need(context, "music").get_playlist(str(params.get("playlist_id") or ""))
    if playlist is None:
        raise ActionError("That playlist isn't there anymore.")
    return playlist


def _track(context, params):
    track = _need(context, "music").get_track(str(params.get("track_id") or ""))
    if track is None:
        raise ActionError("That song isn't in the library anymore.")
    return track


def _name(params) -> str:
    name = str(params.get("name") or "").strip()
    if not name:
        raise ActionError("Give it a name.")
    return name


def _playlist_add(context, params) -> str:
    name = _name(params)
    _need(context, "music").create_playlist(name)
    return f"Made the playlist {name}."


def _playlist_rename(context, params) -> str:
    playlist, name = _playlist(context, params), _name(params)
    context.music.rename_playlist(playlist.playlist_id, name)
    return f"Renamed to {name}."


def _playlist_delete(context, params) -> str:
    playlist = _playlist(context, params)
    context.music.delete_playlist(playlist.playlist_id)
    return f"Deleted the playlist {playlist.name}. The songs stay in your library."


def _playlist_add_track_describe(context, params) -> str:
    playlist, track = _playlist(context, params), _track(context, params)
    if track.track_id in playlist.track_ids:
        raise ActionError(f"{track.title} is already on {playlist.name}.")
    return f"Add {track.title} to {playlist.name}"


def _playlist_add_track(context, params) -> str:
    _playlist_add_track_describe(context, params)
    playlist, track = _playlist(context, params), _track(context, params)
    context.music.add_track_to_playlist(playlist.playlist_id, track.track_id)
    return f"Added {track.title} to {playlist.name}."


def _playlist_remove_track(context, params) -> str:
    playlist, track = _playlist(context, params), _track(context, params)
    context.music.remove_track_from_playlist(playlist.playlist_id, track.track_id)
    return f"Took {track.title} off {playlist.name}."


def _scan(context, params) -> str:
    result = _need(context, "music").scan_library()
    if result.root_missing:
        return f"MIA couldn't find the music folder ({context.music.root_path}). Set it in Settings."
    return f"Library scanned: {result.added} new, {result.updated} updated, {result.removed} gone."


# ------------------------------------------------------------------ files


def _myfiles(context):
    from core.my_files import MyFiles

    return MyFiles.for_context(context)


def _folder_describe(context, params) -> str:
    name = _name(params)
    where = str(params.get("path") or "")
    return f"Make the folder {name}" + (f" in {where}" if where else "")


def _folder(context, params) -> str:
    try:
        made = _myfiles(context).make_folder(str(params.get("path") or ""), _name(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"Made {made}."


def _rename_describe(context, params) -> str:
    return f"Rename {str(params.get('path') or '')} to {_name(params)}"


def _rename(context, params) -> str:
    try:
        _myfiles(context).rename(str(params.get("path") or ""), _name(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return "Renamed."


def _delete_describe(context, params) -> str:
    path = str(params.get("path") or "")
    try:
        kind = "folder and everything in it" if _myfiles(context).is_folder(path) else "file"
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"Delete the {kind} {path}. This can't be undone."


def _delete(context, params) -> str:
    try:
        _myfiles(context).delete(str(params.get("path") or ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return "Deleted."


def _say(text: str):
    return lambda context, params: text


def _register() -> None:
    kinds = []
    for record in RECORDS.values():
        kinds += record_kinds(record)
    kinds += [k for k in record_kinds(TRIP) if not k.kind.endswith(".add")]
    for key, store, getter, adjust, attr, unit, whole in (
            ("component", "components", "get_component", "adjust_quantity", "quantity", "", True),
            ("material", "materials", "get_material", "adjust_quantity", "quantity_on_hand", "unit", False),
            ("product", "products", "get_product", "adjust_stock", "quantity_in_stock", "", False)):
        describe, execute = _adjuster(key, store, getter, adjust, attr, unit, whole)
        kinds.append(ActionType(f"{key}.adjust", "Adjust", {f"{key}_id": f"the {key}", "delta": "+ or - how many"},
                                describe, execute))
    sale_delete = _ledger_delete(SALE, "get_revenue", "delete_revenue")
    cost_delete = _ledger_delete(SHOP_EXPENSE, "get_expense", "delete_expense")
    kinds += [
        ActionType("journal.add", "Add", {f.name: f.label for f in JOURNAL_FIELDS}, _journal_add_describe, _journal_add),
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
        ActionType("myfile.folder", "New Folder", {"path": "where", "name": "its name"}, _folder_describe, _folder),
        ActionType("myfile.rename", "Rename", {"path": "the file", "name": "new name"}, _rename_describe, _rename),
        ActionType("myfile.delete", "Delete", {"path": "the file or folder"}, _delete_describe, _delete),
    ]
    # Children have the Journal and Music (core/child_accounts.CHILD_APPS).
    from dataclasses import replace

    for kind in kinds:
        if kind.kind.split(".")[0] in ("journal", "playlist"):
            kind = replace(kind, child_ok=True)
        ACTION_TYPES[kind.kind] = kind


_register()
