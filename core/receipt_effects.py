"""
core.receipt_effects
======================

What a receipt means beyond its total (Zac, 2026-11-07: "she should be
able to see my receipt and know I got my oil changed or bought groceries
and stock my pantry with what's on the receipt, and same for Lowe's
receipts and materials"). When the inbox reads a receipt
(core/inbox_manager.py), `propose()` works out, in code, what it says
happened:

- **Groceries** (a grocery store, or food lines at a general store): each
  line stocks the pantry, added to a pantry item it matches or as a new one
  with its receipt name made readable; a grocery-list item it matches is
  ticked off as bought.
- **Car service** (an oil change, tire rotation, brakes, inspection...): the
  vehicle's matching maintenance task is marked done on the receipt's date,
  with the odometer when the receipt shows it; a service with no task yet
  starts one, done today.
- **Building supplies** (Lowe's, Home Depot, a lumber yard, or lumber and
  hardware lines): each line adds to the workshop's materials at the price
  paid, to a material it matches or as a new one.

Each is an **effect**: a sentence and whether it's ticked. Nothing happens
until the person files the receipt (`inbox.file`), when `apply()` does the
ticked ones. Matching uses core/receipt_match.py's store-receipt word
matching; nothing is guessed when nothing fits. Receipt text is data read
by code, never instructions to MIA.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from core.logger import get_logger
from core.receipt_match import match

log = get_logger(__name__)

GROCERY, AUTO, BUILDING = "groceries", "car service", "building supplies"

_GROCERY_STORES = re.compile(
    r"\b(kroger|aldi|publix|safeway|food lion|h-?e-?b|meijer|whole foods|trader joe|sprouts|wegmans|harris teeter|"
    r"ingles|winco|piggly|hy-?vee|giant|stop ?& ?shop|albertsons|ralphs|fred meyer|smith'?s|save[- ]a[- ]lot|"
    r"lidl|food city|market basket|instacart|grocery|groceries|supermarket)\b", re.I)
_GENERAL_STORES = re.compile(r"\b(walmart|wal-mart|target|costco|sam'?s club|bj'?s|dollar general|family dollar)\b",
                             re.I)
_AUTO_SHOPS = re.compile(
    r"\b(jiffy lube|valvoline|firestone|pep boys|midas|take 5|grease monkey|discount tire|goodyear|meineke|"
    r"monro|ntb|les schwab|express oil|quick lube|auto ?(care|service|repair)|tire|lube|dealership|service center)\b",
    re.I)
_BUILDING_STORES = re.compile(
    r"\b(lowe'?s|home depot|menards|ace hardware|true value|tractor supply|84 lumber|lumber|hardware|"
    r"builders? supply|do it best)\b", re.I)
_BUILDING_WORDS = re.compile(
    r"\b(\d+x\d+|stud|lumber|plywd|plywood|osb|drywall|screws?|nails?|bolts?|lag|joist|hanger|concrete|quikrete|"
    r"sakrete|mortar|pt|treated|deck|board|sheathing|shingles?|caulk|pvc|conduit|romex|wire|hinge|lag)\b", re.I)

# A service named on a receipt -> the words a maintenance task for it would have.
SERVICES = (
    ("Oil change", ("oil change", "lube oil", "oil & filter", "oil and filter", "synthetic oil", "full synthetic",
                    "conventional oil", "oil filter"), ("oil",)),
    ("Tire rotation", ("tire rotation", "rotate tires", "rotation"), ("rotat", "tire")),
    ("Brakes", ("brake pad", "brake service", "brakes", "rotors"), ("brake",)),
    ("Inspection", ("state inspection", "inspection", "emissions"), ("inspect",)),
    ("Alignment", ("alignment",), ("align",)),
    ("Engine air filter", ("engine air filter", "air filter"), ("air filter",)),
    ("Cabin air filter", ("cabin filter", "cabin air"), ("cabin",)),
    ("Transmission service", ("transmission fluid", "transmission service", "trans flush"), ("transmission",)),
    ("Coolant flush", ("coolant", "antifreeze"), ("coolant",)),
    ("Battery", ("battery",), ("battery",)),
    ("Wiper blades", ("wiper",), ("wiper",)),
)
_ODOMETER = re.compile(r"\b(?:odometer|odo|mileage|miles\s*in|mi\s*in|miles)\s*(?:in|out)?\s*[:#=]?\s*([\d,]{3,7})\b",
                       re.I)

# Store abbreviations on grocery receipts, and brand prefixes that say nothing about the food.
_ABBREV = {
    "whl": "whole", "wht": "white", "mlk": "milk", "org": "organic", "chkn": "chicken", "chk": "chicken",
    "bnls": "boneless", "sknls": "skinless", "brst": "breast", "grd": "ground", "bf": "beef", "brd": "bread",
    "chs": "cheese", "shrd": "shredded", "ygt": "yogurt", "yog": "yogurt", "btr": "butter", "lg": "large",
    "sm": "small", "fz": "frozen", "frz": "frozen", "veg": "vegetables", "veggie": "vegetables", "tom": "tomatoes",
    "pot": "potatoes", "bnna": "bananas", "ban": "bananas", "app": "apples", "crm": "cream", "sr": "sour",
    "pnt": "peanut", "btr.": "butter", "bev": "beverage", "jce": "juice", "oj": "orange juice", "pb": "peanut butter",
    "cof": "coffee", "grnd": "ground", "rst": "roast", "sau": "sauce", "pst": "pasta", "spag": "spaghetti",
    "flr": "flour", "sug": "sugar", "brn": "brown", "ric": "rice", "bns": "beans", "blk": "black", "ckn": "chicken",
    "trky": "turkey", "bcn": "bacon", "saus": "sausage", "hmbgr": "hamburger", "bun": "buns", "tort": "tortillas",
    "lett": "lettuce", "rom": "romaine", "onn": "onions", "pep": "peppers", "grn": "green", "red": "red",
    # building-store receipts
    "plywd": "plywood", "plywd.": "plywood", "ply": "plywood", "scrw": "screws", "scrws": "screws", "galv": "galvanized",
    "trtd": "treated", "prs": "pressure", "hdwr": "hardware", "brkt": "bracket", "hngr": "hanger", "cncrt": "concrete",
    "dryw": "drywall", "shtg": "sheathing", "constr": "construction", "adh": "adhesive",
}
_BRANDS = {"gv", "ks", "mm", "ht", "kro", "pl", "pp", "sig", "gg", "365", "cv", "fm", "great", "value"}
_CATEGORY_WORDS = (
    ("Produce", ("apple", "banana", "lettuce", "romaine", "tomato", "onion", "potato", "carrot", "pepper", "celery",
                 "spinach", "broccoli", "avocado", "lemon", "lime", "orange", "grape", "berry", "berries", "garlic",
                 "cucumber", "squash", "corn", "produce", "fruit")),
    ("Dairy", ("milk", "cheese", "yogurt", "butter", "egg", "eggs", "cream", "creamer", "cottage")),
    ("Meat", ("chicken", "beef", "pork", "bacon", "sausage", "turkey", "ham", "steak", "hamburger", "fish", "salmon",
              "tuna", "shrimp", "meat")),
    ("Frozen", ("frozen", "ice cream", "pizza")),
    ("Beverages", ("coffee", "tea", "soda", "juice", "water", "beverage", "drink", "cola")),
    ("Spices", ("salt", "pepper", "spice", "cinnamon", "paprika", "cumin", "oregano")),
    ("Condiments", ("ketchup", "mustard", "mayo", "mayonnaise", "sauce", "dressing", "syrup", "salsa", "jam", "jelly")),
    ("Pantry/Dry Goods", ("bread", "pasta", "spaghetti", "rice", "beans", "flour", "sugar", "cereal", "oats",
                          "crackers", "chips", "soup", "peanut butter", "tortillas", "buns", "oil")),
)


def readable_name(description: str) -> str:
    """Pure logic. A receipt line's description as a person would write it: codes, sizes and store brands dropped,
    abbreviations spelled out ("GV WHL MLK GAL 0078742" -> "Whole milk")."""
    words = []
    for raw in re.findall(r"[A-Za-z0-9'&.]+", description or ""):
        word = raw.lower().strip(".")
        if re.fullmatch(r"\d{4,}", word) or word in _BRANDS:
            continue
        if re.fullmatch(r"\d+(\.\d+)?(oz|lb|lbs|ct|pk|gal|qt|l|ml|g|kg)?", word) or word in ("oz", "lb", "lbs", "ct",
                                                                                         "pk", "gal", "qt", "ea"):
            continue
        words.append(_ABBREV.get(word, word))
    name = " ".join(words).strip()
    return name[:1].upper() + name[1:] if name else (description or "").strip()


def pantry_category(name: str) -> str:
    """Pure logic. Which pantry shelf a food goes on, from its words; "" when it doesn't look like food."""
    text = f" {name.lower()} "
    for category, words in _CATEGORY_WORDS:
        if any(re.search(rf"\b{re.escape(w)}s?\b", text) for w in words):
            return category
    return ""


def kind_of(vendor: str, text: str, items: list[dict]) -> str:
    """Pure logic. What a receipt is for: groceries, car service, building supplies, or "" (only an expense)."""
    where = f"{vendor}\n{text[:400]}"
    lines = " ".join(i.get("description", "") for i in items)
    if _AUTO_SHOPS.search(where) or any(any(w in text.lower() for w in said) for _n, said, _t in SERVICES[:1]):
        return AUTO
    if _BUILDING_STORES.search(where) or len(_BUILDING_WORDS.findall(lines)) >= max(2, len(items) // 2):
        return BUILDING
    if _GROCERY_STORES.search(where):
        return GROCERY
    if _GENERAL_STORES.search(where) and any(pantry_category(readable_name(i.get("description", ""))) for i in items):
        return GROCERY
    return ""


def services_in(text: str) -> list[str]:
    """Pure logic. The car services a receipt names, once each, in SERVICES order."""
    lowered = (text or "").lower()
    return [name for name, said, _task_words in SERVICES if any(s in lowered for s in said)]


def odometer_in(text: str) -> Optional[float]:
    """Pure logic. The odometer reading a service receipt shows, or None."""
    found = _ODOMETER.search(text or "")
    if not found:
        return None
    value = float(found.group(1).replace(",", ""))
    return value if 100 <= value <= 999_999 else None


# ------------------------------------------------------------------ proposing


def _effect(kind: str, label: str, on: bool = True, **params) -> dict:
    """One proposed effect: its kind, the sentence the person sees, whether it's ticked, and what to do."""
    return {"kind": kind, "label": label, "on": on, **params}


def _qty(line: dict) -> float:
    """A receipt line's quantity (1 when it doesn't say)."""
    try:
        return float(line.get("quantity") or 1)
    except (TypeError, ValueError):
        return 1.0


def _plain(value: float) -> str:
    """Pure logic. A number without a needless .0."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _groceries(context, items: list[dict]) -> list[dict]:
    """Pantry and grocery-list effects for a grocery receipt's lines."""
    kitchen = getattr(context, "kitchen", None)
    if kitchen is None:
        return []
    effects = []
    pantry = kitchen.all_pantry_items()
    found = match([p.name for p in pantry], items)["pairs"]
    by_line = {line: pantry[index] for index, line in found.items()}
    for j, line in enumerate(items):
        qty = _qty(line)
        name = readable_name(line.get("description", ""))
        category = pantry_category(name)
        if j in by_line:
            item = by_line[j]
            effects.append(_effect("pantry_add", f"Add {_plain(qty)} to {item.name} in the pantry", True,
                                   pantry_id=item.item_id, quantity=qty))
        elif category:
            effects.append(_effect("pantry_new", f"Put {name} in the pantry ({category})", True, name=name,
                                   quantity=qty, category=category))
    grocery = [g for g in kitchen.all_grocery_items() if not g.checked]
    for index, line in match([g.name for g in grocery], items)["pairs"].items():
        effects.append(_effect("grocery_check", f"Tick {grocery[index].name} off the grocery list", True,
                               grocery_id=grocery[index].item_id))
    return effects


def _vehicle(context, asset_id: str):
    """The vehicle a service receipt is for: the one the inbox matched, else the household's only vehicle."""
    maintenance = getattr(context, "maintenance", None)
    if maintenance is None:
        return None
    asset = maintenance.get_asset(asset_id) if asset_id else None
    if asset is not None:
        return asset
    vehicles = [a for a in maintenance.all_assets() if a.category == "Vehicle"]
    return vehicles[0] if len(vehicles) == 1 else None


def _car_service(context, text: str, asset_id: str, when: str) -> list[dict]:
    """Maintenance effects for a service receipt: each service marked done on the vehicle (a new task when it has
    none), with the odometer when shown."""
    vehicle = _vehicle(context, asset_id)
    services = services_in(text)
    if vehicle is None or not services:
        if services:
            return [_effect("note", f"{', '.join(services)}: which vehicle? Pick it before filing.", False)]
        return []
    maintenance = context.maintenance
    miles = odometer_in(text)
    effects = []
    for name in services:
        task_words = next(t for n, _s, t in SERVICES if n == name)
        task = next((t for t in maintenance.tasks_for_asset(vehicle.asset_id)
                     if any(w in t.title.lower() for w in task_words)), None)
        at = f" at {_plain(miles)} miles" if miles else ""
        if task is not None:
            effects.append(_effect("maintenance_done", f"Mark \"{task.title}\" done on the {vehicle.name}, {when}{at}",
                                   True, task_id=task.task_id, date=when, miles=miles))
        else:
            effects.append(_effect("maintenance_new", f"Start tracking \"{name}\" on the {vehicle.name}, done {when}"
                                   f"{at}", True, asset_id=vehicle.asset_id, title=name, date=when, miles=miles))
    return effects


def _building(context, items: list[dict]) -> list[dict]:
    """Workshop-materials effects for a building-supply receipt's lines, at the price paid."""
    materials = getattr(context, "materials", None)
    if materials is None:
        return []
    stock = materials.all_materials()
    found = match([m.name for m in stock], items)["pairs"]
    by_line = {line: stock[index] for index, line in found.items()}
    effects = []
    for j, line in enumerate(items):
        qty = _qty(line)
        price = line.get("unit_price") or (round(float(line.get("amount") or 0) / qty, 2) if qty else 0)
        if j in by_line:
            material = by_line[j]
            effects.append(_effect("material_add", f"Add {_plain(qty)} to {material.name} in your materials", True,
                                   material_id=material.material_id, quantity=qty, unit_cost=price))
        else:
            name = readable_name(line.get("description", ""))
            effects.append(_effect("material_new", f"Add {_plain(qty)} {name} to your materials", True, name=name,
                                   quantity=qty, unit_cost=price))
    return effects


def propose(context, item, text: str = "") -> tuple[str, list[dict]]:
    """What an inbox receipt means, from its whole text: (its kind, the effects to offer). Nothing for a receipt
    that's only an expense."""
    text = f"{item.subject}\n{text or item.excerpt}"
    kind = kind_of(item.vendor, text, item.items)
    when = item.doc_date or date.today().isoformat()
    if kind == GROCERY:
        return kind, _groceries(context, item.items)
    if kind == AUTO:
        return kind, _car_service(context, text, item.asset_id, when)
    if kind == BUILDING:
        return kind, _building(context, item.items)
    return "", []


# ------------------------------------------------------------------ applying


def apply(context, effects: list[dict], chosen: Optional[list[int]] = None) -> list[str]:
    """Does the chosen effects (the ticked ones when `chosen` is None); returns what was done, a phrase each kind.
    One that can't be done any more (a pantry item deleted since) is skipped, not raised."""
    picked = [e for i, e in enumerate(effects) if (e.get("on") if chosen is None else i in chosen)]
    counts: dict[str, int] = {}
    for effect in picked:
        try:
            if _do(context, effect):
                counts[effect["kind"]] = counts.get(effect["kind"], 0) + 1
        except (ValueError, KeyError, AttributeError) as problem:
            log.warning("A receipt effect couldn't be done (%s): %s", effect.get("kind"), problem)
    words = {"pantry_add": ("pantry item topped up", "pantry items topped up"),
             "pantry_new": ("new item in the pantry", "new items in the pantry"),
             "grocery_check": ("grocery item ticked off", "grocery items ticked off"),
             "maintenance_done": ("service marked done", "services marked done"),
             "maintenance_new": ("service now tracked", "services now tracked"),
             "material_add": ("material topped up", "materials topped up"),
             "material_new": ("new material", "new materials")}
    return [f"{n} {words[k][0 if n == 1 else 1]}" for k, n in counts.items() if k in words]


def _do(context, effect: dict) -> bool:
    """One effect, through the store that owns it."""
    kind = effect["kind"]
    if kind == "pantry_add":
        kitchen = context.kitchen
        item = kitchen.get_pantry_item(effect["pantry_id"])
        if item is None:
            return False
        kitchen.update_pantry_item(item.item_id, quantity=item.quantity + float(effect["quantity"]))
    elif kind == "pantry_new":
        context.kitchen.add_pantry_item(effect["name"], quantity=float(effect["quantity"]),
                                        category=effect.get("category") or "Other", notes="From a receipt")
    elif kind == "grocery_check":
        if context.kitchen.get_grocery_item(effect["grocery_id"]) is None:
            return False
        context.kitchen.set_grocery_item_checked(effect["grocery_id"], True)
    elif kind == "maintenance_done":
        maintenance = context.maintenance
        task = maintenance.get_task(effect["task_id"])
        if task is None:
            return False
        miles = effect.get("miles")
        if miles and task.is_meter_task:
            maintenance.log_reading(task.task_id, float(miles), task.meter_unit or "miles", "From a service receipt")
        maintenance.mark_complete(task.task_id, effect.get("date"), float(miles) if miles and task.is_meter_task
                                  else None)
    elif kind == "maintenance_new":
        maintenance = context.maintenance
        if maintenance.get_asset(effect["asset_id"]) is None:
            return False
        task = maintenance.add_task(effect["asset_id"], effect["title"], interval_days=182,
                                    notes="Started from a service receipt; change how often in Garage.")
        maintenance.mark_complete(task.task_id, effect.get("date"))
    elif kind == "material_add":
        materials = context.materials
        material = materials.get_material(effect["material_id"])
        if material is None:
            return False
        materials.adjust_quantity(material.material_id, float(effect["quantity"]))
        if effect.get("unit_cost"):
            materials.update_material(material.material_id, unit_cost=float(effect["unit_cost"]))
    elif kind == "material_new":
        context.materials.add_material(name=effect["name"], unit="each", unit_cost=float(effect.get("unit_cost") or 0),
                                       quantity_on_hand=float(effect["quantity"]), notes="From a receipt")
    else:
        return False
    return True
