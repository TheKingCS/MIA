"""
core.food_table
=================

MIA's built-in food table (DEC-0020): nutrition facts for about 7,800
everyday foods from the USDA's FoodData Central (public domain), per
100 g, in data/foods.tsv (tools/make_food_table.py builds it). Offline.

What it's for: working out a recipe's nutrition from its ingredients
("2 cups rice", "1 lb chicken breast") so nobody has to type it. Each
ingredient is matched to a food by its words, its amount turned into
grams (by weight, by the food's own household measures, or by common
kitchen measures), and the nutrients added up. Anything MIA can't match
is reported, never guessed silently; a value the person typed into the
recipe always wins (core/kitchen_manager.py keeps those).

Pure logic over a read-only file; loaded once, on first use.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

TABLE = Path(__file__).resolve().parent.parent / "data" / "foods.tsv"
NUTRIENTS = ("kcal", "protein_g", "fat_g", "carbs_g", "fiber_g", "sugar_g", "sodium_mg")


@dataclass(frozen=True)
class Food:
    fdc_id: str
    name: str
    category: str
    per_100g: dict  # nutrient -> amount (missing = unknown)
    portions: dict = field(default_factory=dict)  # "cup" -> grams for one
    words: frozenset = frozenset()


# Weights and volumes everyone uses. Volumes are for water-like foods; a
# food's own measures (a cup of rice weighs 185 g) win when the table has them.
_GRAMS = {"g": 1, "gram": 1, "kg": 1000, "kilogram": 1000, "oz": 28.35, "ounce": 28.35, "lb": 453.6, "pound": 453.6}
_MILLILITRES = {"ml": 1, "millilitre": 1, "milliliter": 1, "l": 1000, "litre": 1000, "liter": 1000,
                "cup": 240, "tbsp": 15, "tablespoon": 15, "tsp": 5, "teaspoon": 5, "fl oz": 29.6, "pint": 473,
                "quart": 946, "gallon": 3785}
_UNIT_WORDS = {"tbs": "tbsp", "tbl": "tbsp", "t": "tsp", "c": "cup", "lbs": "lb", "#": "lb", "ozs": "oz"}
_VOLUMES = {"cup", "cups", "tbsp", "tsp", "tablespoon", "teaspoon", "fl", "oz", "ml", "liter", "quart", "pint", "gallon"}
SCOOP_G = 30  # a protein-powder scoop as nutrition labels give it (most are 25 to 35 g)
CAN_CUPS, CAN_G = 1.5, 425  # a standard 15 oz can: about 1.5 cups drained, 425 g in all
_PIECES = ("", "each", "piece", "whole", "large", "medium", "small", "clove", "slice", "can", "breast", "fillet")

# Words that describe how something is cut or bought, not what it is.
_IGNORE = {"fresh", "chopped", "diced", "minced", "sliced", "large", "small", "medium", "boneless", "skinless",
           "organic", "lean", "extra", "virgin", "of", "and", "or", "a", "to", "taste", "for", "the", "finely",
           "roughly", "about", "plus", "more", "peeled", "trimmed", "cubed", "shredded", "grated", "packed",
           "cut", "into", "pieces", "piece", "whole", "halved", "optional", "divided", "frozen", "thawed"}
_COOKED = {"cooked", "boiled", "roasted", "grilled", "fried", "baked", "steamed", "canned", "drained"}
_UNWANTED = ("babyfood", "baby food", "infant formula", "fast foods", "restaurant", "school lunch")

COMMON = {  # what a home cook means -> the words its USDA entry has ("!word": not that word)
 "chicken breast": "chicken breast meat only raw skinless",
 "chicken thigh": "chicken thigh meat only raw",
 "chicken": "chicken breast meat only raw skinless",
 "egg": "egg whole raw fresh",
 "egg white": "egg white raw fresh",
 "olive oil": "oil olive salad cooking",
 "vegetable oil": "oil canola",
 "canola oil": "oil canola",
 "coconut oil": "oil coconut",
 "rice": "rice white long grain regular raw enriched",
 "white rice": "rice white long grain regular raw enriched",
 "cooked rice": "rice white long grain regular enriched cooked",
 "cooked chicken breast": "chicken breast skinless boneless meat only cooked grilled !solution",
 "cooked chicken": "chicken breast skinless boneless meat only cooked grilled !solution",
 "brown rice": "rice brown long grain raw",
 "oat": "cereal oat regular quick not fortified dry",
 "rolled oat": "cereal oat regular quick not fortified dry",
 "oatmeal": "cereal oat regular quick not fortified dry",
 "sugar": "sugar granulated",
 "brown sugar": "sugar brown",
 "flour": "wheat flour white all purpose enriched bleached",
 "all purpose flour": "wheat flour white all purpose enriched bleached",
 "bread": "bread white commercially prepared !toasted",
 "whole wheat bread": "bread whole wheat commercially prepared",
 "ground beef": "beef ground 85 lean meat 15 fat raw",
 "beef": "beef ground 85 lean meat 15 fat raw",
 "steak": "beef top sirloin steak separable lean fat raw",
 "ground turkey": "turkey ground raw",
 "turkey": "turkey ground raw",
 "pork chop": "pork loin chop raw",
 "bacon": "pork cured bacon unprepared",
 "salmon": "fish salmon atlantic farmed raw",
 "tuna": "fish tuna light canned water drained",
 "canned tuna": "fish tuna light canned water drained",
 "shrimp": "crustacean shrimp raw",
 "tilapia": "fish tilapia raw",
 "venison": "game meat deer raw",
 "tofu": "tofu raw firm calcium sulfate",
 "milk": "milk reduced fat fluid 2 milkfat",
 "whole milk": "milk whole 3 25 milkfat",
 "butter": "butter salted",
 "cheddar cheese": "cheese cheddar distribution",
 "cheese": "cheese cheddar distribution",
 "shredded cheese": "cheese cheddar distribution",
 "pinto bean": "bean pinto mature seed canned drained solid",
 "cooked brown rice": "rice brown long grain cooked !parboiled",
 "beef broth": "soup beef broth bouillon canned ready serve",
 "cheddar": "cheese cheddar distribution",
 "mozzarella": "cheese mozzarella whole milk",
 "parmesan": "cheese parmesan grated",
 "cream cheese": "cheese cream",
 "cottage cheese": "cheese cottage lowfat 2 milkfat",
 "greek yogurt": "yogurt greek plain nonfat !chobani",
 "yogurt": "yogurt plain low fat",
 "sour cream": "cream sour cultured !reduced",
 "heavy cream": "cream fluid heavy whipping",
 "peanut butter": "peanut butter smooth style !without",
 "almond": "nut almond",
 "walnut": "nut walnut english",
 "peanut": "peanut all type raw",
 "chia seed": "seed chia dried",
 "whey protein": "beverage protein powder whey based",
 "protein powder": "beverage protein powder whey based",
 "pasta": "pasta dry enriched",
 "spaghetti": "pasta dry enriched",
 "quinoa": "quinoa uncooked",
 "tortilla": "tortilla flour ready bake fry refrigerated",
 "flour tortilla": "tortilla flour ready bake fry refrigerated",
 "corn tortilla": "tortilla ready bake fry corn",
 "potato": "potato flesh skin raw",
 "sweet potato": "sweet potato raw unprepared",
 "onion": "onion raw",
 "garlic": "garlic raw",
 "tomato": "tomato red ripe raw year round average",
 "bell pepper": "pepper sweet red raw",
 "red pepper": "pepper sweet red raw",
 "green pepper": "pepper sweet green raw",
 "spinach": "spinach raw",
 "broccoli": "broccoli raw",
 "carrot": "carrot raw",
 "lettuce": "lettuce cos romaine raw",
 "avocado": "avocado raw all commercial variety",
 "banana": "banana raw",
 "apple": "apple raw skin !without",
 "strawberry": "strawberry raw",
 "blueberry": "blueberry raw",
 "orange": "orange raw all commercial variety",
 "lemon juice": "lemon juice raw",
 "lime juice": "lime juice raw",
 "black bean": "bean black mature seed canned low sodium",
 "kidney bean": "bean kidney red mature seed canned drained solid",
 "chickpea": "chickpea garbanzo mature seed canned drained solid",
 "tomato sauce": "tomato product canned sauce",
 "crushed tomato": "tomato crushed canned",
 "tomato paste": "tomato product canned paste",
 "chili": "pepper hot chili green raw",  # as an ingredient: the pepper (the dish is "chili con carne")
 "chile": "pepper hot chili green raw",
 "green chile": "pepper hot chili green raw",
 "green chili": "pepper hot chili green raw",
 "red chile": "pepper hot chili red raw",
 "red chili": "pepper hot chili red raw",
 "chili pepper": "pepper hot chili red raw",
 "chile pepper": "pepper hot chili red raw",
 "jalapeno": "pepper jalapeno raw",
 "chili flake": "spice pepper red cayenne",
 "red chili flake": "spice pepper red cayenne",
 "red pepper flake": "spice pepper red cayenne",
 "crushed red pepper": "spice pepper red cayenne",
 "cayenne": "spice pepper red cayenne",
 "rotel": "tomato canned green chili",  # the canned tomatoes with green chiles most US recipes name
 "ro tel": "tomato canned green chili",
 "tomato green chile": "tomato canned green chili",
 "tomato green chili": "tomato canned green chili",
 "tomato with green chile": "tomato canned green chili",
 "tomato with green chili": "tomato canned green chili",
 "salt pepper": "salt table",  # "salt and pepper to taste": the salt; neither adds calories
 "chicken broth": "soup stock chicken home prepared",
 "chicken stock": "soup stock chicken home prepared",
 "salt": "salt table",
 "black pepper": "spice pepper black",
 "pepper": "spice pepper black",
 "chili powder": "spice chili powder",
 "cumin": "spice cumin seed",
 "paprika": "spice paprika",
 "garlic powder": "spice garlic powder",
 "onion powder": "spice onion powder",
 "cinnamon": "spice cinnamon ground",
 "baking soda": "leavening agent baking soda",
 "baking powder": "leavening agent baking powder double acting",
 "honey": "honey",
 "maple syrup": "syrup maple",
 "soy sauce": "soy sauce made from soy tamari",
 "mustard": "mustard prepared yellow",
 "ketchup": "catsup",
 "mayonnaise": "mayonnaise regular",
 "mushroom": "mushroom white raw",
 "celery": "celery raw",
 "cucumber": "cucumber peel raw",
 "zucchini": "squash summer zucchini skin raw",
 "kale": "kale raw",
 "cabbage": "cabbage raw",
 "cauliflower": "cauliflower raw",
 "corn": "corn sweet yellow raw",
 "pea": "pea green raw",
 "ginger": "ginger root raw",
 "cilantro": "coriander cilantro leaves raw",
 "parsley": "parsley fresh",
 "basil": "basil fresh",
 "raisin": "raisin seedless",
 "water": "beverage water tap drinking",
}


_cache: Optional[list[Food]] = None
_common: dict = {}


_SINGULAR = {"chilies": "chili", "chillies": "chili", "chilis": "chili", "chiles": "chile", "cookies": "cookie", "pies": "pie"}


def _singular(word: str) -> str:
    if word in _SINGULAR:
        return _SINGULAR[word]
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("oes"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def words_of(text: str) -> list[str]:
    """Pure logic. Lowercase singular words, accents dropped ("jalapeños" is "jalapeno")."""
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [_singular(w) for w in re.findall(r"[a-z]+", plain)]


def load(path: Optional[Path] = None) -> list[Food]:
    """The table (loaded once). Empty when MIA has no table yet."""
    global _cache
    if path is None and _cache is not None:
        return _cache
    foods: list[Food] = []
    table = Path(path or TABLE)
    if table.exists():
        with table.open(encoding="utf-8", newline="") as f:
            rows = csv.DictReader((line for line in f if not line.startswith("#")), delimiter="\t")
            for row in rows:
                per = {n: float(row[n]) for n in NUTRIENTS if row.get(n) not in (None, "")}
                portions = {}
                for part in (row.get("portions") or "").split("|"):
                    if ":" in part:
                        name, grams = part.rsplit(":", 1)
                        try:
                            portions[name.strip()] = float(grams)
                        except ValueError:
                            pass
                foods.append(Food(row["fdc_id"], row["name"], row.get("category", ""), per, portions,
                                  frozenset(words_of(row["name"]))))
    if path is None:
        _cache = foods
    return foods


def available() -> bool:
    return bool(load())


def _score(query: list[str], food: Food, wants_cooked: bool) -> float:
    if not query or not set(query) <= food.words:
        return -1.0
    name = food.name.lower()
    if any(u in name for u in _UNWANTED):
        return -1.0
    head = set(words_of(name.split(",")[0]))
    score = 1.0 - 0.03 * (len(food.words) - len(query))  # fewer extra words: closer to what was asked
    if head <= set(query):
        score += 0.6  # the food's own name is what was asked: "Sugars, ..." for "sugar", not "Sugar-apples"
    elif head & set(query):
        score += 0.3  # "Chicken, ..." for "chicken breast"; not "Soup, chicken ..."
    if re.search(r"\b[A-Z]{3,}\b", food.name) or food.words & {"imitation", "dried", "dehydrated", "leave", "reduced"}:
        score -= 0.3  # brands, and the less usual forms
    cooked = bool(food.words & _COOKED)
    if wants_cooked:
        score += 0.3 if cooked else -0.2
    else:
        if "raw" in food.words:
            score += 0.3
        if cooked:
            score -= 0.2
    return score


def _resolve(spec: str, foods: list[Food]) -> Optional[Food]:
    """The shortest-named food with every word of `spec` and none of its !words."""
    need = set(words_of(" ".join(w for w in spec.split() if not w.startswith("!"))))
    avoid = {w[1:] for w in spec.split() if w.startswith("!")} | {"imitation"}
    found = [f for f in foods if need <= f.words and not (avoid & f.words)
             and not any(u in f.name.lower() for u in _UNWANTED)]
    return min(found, key=lambda f: (len(f.words), len(f.name))) if found else None


def common(phrase: str, foods: list[Food]) -> Optional[Food]:
    """A common ingredient's usual food ("eggs" -> whole eggs), or None."""
    key = " ".join(words_of(phrase))
    if key not in COMMON:
        return None
    cache = _common.setdefault(id(foods), {})
    if key not in cache:
        cache[key] = _resolve(COMMON[key], foods)
    return cache[key]


def find(text: str, foods: Optional[list[Food]] = None) -> Optional[Food]:
    """The best food for an ingredient's name, or None: a common
    ingredient's usual food first, then the closest name in the table."""
    foods = load() if foods is None else foods
    all_words = words_of(text)
    query = [w for w in all_words if w not in _IGNORE and w not in _COOKED and w not in ("raw",)]
    wants_cooked = any(w in _COOKED for w in all_words)
    whole = common(" ".join(all_words_kept(all_words)), foods)
    if whole is not None:
        return whole  # "cooked rice", "chicken breast": the usual food for exactly this
    best = max(foods, key=lambda f: _score(query, f, wants_cooked), default=None)
    if best is not None and _score(query, best, wants_cooked) > 0:
        return best  # every word found in one food's name: "beef broth"
    for size in range(len(query) - 1, 0, -1):  # part of it is a common ingredient: "venison steak" -> venison
        for start in range(0, len(query) - size + 1):
            found = common(" ".join(query[start:start + size]), foods)
            if found is not None:
                return found
    return None  # never a guess: MIA says it couldn't find it


def all_words_kept(words: list[str]) -> list[str]:
    """Pure logic. The words that say what a food is, keeping "cooked"."""
    return [w for w in words if w not in _IGNORE and w != "raw"]


def by_id(fdc_id: str, foods: Optional[list[Food]] = None) -> Optional[Food]:
    return next((f for f in (load() if foods is None else foods) if f.fdc_id == str(fdc_id)), None)


def grams(food: Food, quantity: float, unit: str) -> Optional[float]:
    """Pure logic. How many grams `quantity unit` of this food is, or None."""
    unit = (unit or "").strip().lower().rstrip(".")
    unit = _UNIT_WORDS.get(unit, unit)
    unit = _singular(unit) if unit not in ("lbs", "ozs") else unit
    unit = _UNIT_WORDS.get(unit, unit)
    if quantity is None or quantity <= 0:
        quantity = 1.0
    if unit in _GRAMS:
        return quantity * _GRAMS[unit]
    if unit in ("dash", "pinch") and unit not in food.portions:
        return quantity * {"dash": 0.6, "pinch": 0.3}[unit]  # 1/8 and 1/16 teaspoon
    if unit == "scoop" and "scoop" not in food.portions:
        return quantity * SCOOP_G
    if unit == "can" and not any(name.split()[0] == "can" for name in food.portions):
        cup = food.portions.get("cup")  # a standard 15 oz can is about 1.5 cups drained
        return quantity * (CAN_CUPS * cup if cup else CAN_G)
    for name, weight in food.portions.items():  # the food's own measures win
        if unit and (name == unit or name.split()[0] == unit):
            return quantity * weight
    if unit in _MILLILITRES:
        return quantity * _MILLILITRES[unit]
    if unit in _PIECES:
        for wanted in ([unit] if unit else []) + ["medium", "large", "each", "piece", "whole", "small"]:
            for name, weight in food.portions.items():
                if wanted and wanted in name.split():
                    return quantity * weight
        whole = [w for name, w in food.portions.items() if name.split()[0] not in _VOLUMES]
        if whole:  # a food's one-piece measure; never a cup of it for "1 whey protein" (2026-10-14)
            return quantity * whole[0]
    return None


def nutrients(food: Food, weight_g: float) -> dict:
    """Pure logic. The nutrients in `weight_g` grams of this food."""
    return {n: v * weight_g / 100 for n, v in food.per_100g.items()}


def recipe_nutrition(ingredients: list, servings: int, foods: Optional[list[Food]] = None) -> dict:
    """Pure logic over the table. A recipe's nutrition per serving from its
    ingredients ([{name, quantity, unit, fdc_id?}]), with what matched and
    what didn't. `complete` is False when anything couldn't be counted."""
    foods = load() if foods is None else foods
    total = {n: 0.0 for n in NUTRIENTS}
    matched, missing, not_found, no_amount, to_taste = [], [], [], [], []
    for ingredient in ingredients or []:
        name = str(ingredient.get("name", "")).strip()
        if not name:
            continue
        food = by_id(ingredient["fdc_id"], foods) if ingredient.get("fdc_id") else find(name, foods)
        quantity, unit = float(ingredient.get("quantity") or 0), str(ingredient.get("unit") or "").strip()
        sized = _SIZED_NAME.match(name) if not unit else None
        if sized:  # saved before "1 (10 oz) can Rotel" was read as 10 oz: the size is still in the name
            quantity, unit, name = (quantity or 1) * float(sized.group(1)), sized.group(2).lower(), sized.group(3).strip()
        weight = grams(food, quantity, unit) if food else None
        if food is not None and _seasoning(food) and (weight is None or (not quantity and not unit)):
            to_taste.append(name)  # "red wine vinegar", "salt to taste": a dash, next to nothing (2026-10-14)
            matched.append({"name": name, "food": food.name, "fdc_id": food.fdc_id, "grams": 0})
            continue
        if food is None or weight is None:
            missing.append(name)
            (no_amount if food is not None else not_found).append(name)
            continue
        for n, v in nutrients(food, weight).items():
            total[n] += v
        matched.append({"name": name, "food": food.name, "fdc_id": food.fdc_id, "grams": round(weight)})
    servings = max(1, int(servings or 1))
    per_serving = {n: round(v / servings, 1) for n, v in total.items()}
    return {"per_serving": per_serving, "matched": matched, "missing": missing, "not_found": not_found, "no_amount": no_amount,
            "to_taste": to_taste, "complete": not missing and bool(matched)}


_SIZED_NAME = re.compile(r"^\(\s*(\d+(?:\.\d+)?)\s*-?\s*(oz|ounces?|g|grams?|lbs?|ml)\.?\s*\)\s*"
                         r"(?:cans?|jars?|packages?|pkgs?|bags?|boxes?|bottles?|cartons?|containers?)?\.?\s+(.+)$", re.IGNORECASE)


def _seasoning(food: Food) -> bool:
    """Pure logic. Spices, herbs, vinegar, salt, water: with no amount it's a dash."""
    return food.category == "Spices and Herbs" or food.per_100g.get("kcal") == 0
