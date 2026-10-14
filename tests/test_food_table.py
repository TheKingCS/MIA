"""
MIA's built-in food table (core/food_table.py, DEC-0020): matching an
ingredient to a food, turning amounts into grams, and a recipe's
nutrition per serving. Uses a small table in the real file's format
(real USDA names and values for these foods).
"""

from __future__ import annotations

import pytest

from core import food_table

ROWS = """# test table
fdc_id	name	category	kcal	protein_g	fat_g	carbs_g	fiber_g	sugar_g	sodium_mg	portions
171077	Chicken, broilers or fryers, breast, meat only, raw	Poultry Products	120	22.5	2.6	0				breast:174
171477	Chicken, broilers or fryers, breast, meat only, cooked, roasted	Poultry Products	165	31	3.6	0			74	cup:140
169756	Rice, white, long-grain, regular, raw, enriched	Cereal Grains and Pasta	365	7.1	0.7	80	1.3	0.1	5	cup:185|tbsp:11.6
168878	Rice, white, long-grain, regular, enriched, cooked	Cereal Grains and Pasta	130	2.7	0.3	28.2	0.4	0.1	1	cup:158
171287	Egg, whole, raw, fresh	Dairy and Egg Products	143	12.6	9.5	0.7	0	0.4	142	large:50|medium:44
171413	Oil, olive, salad or cooking	Fats and Oils	884	0	100	0			2	tbsp:13.5|cup:216
170000	Soup, chicken noodle, canned	Soups, Sauces, and Gravies	25	1.3	0.8	3.2			343	cup:241
170001	Babyfood, chicken, strained	Baby Foods	90	13	4	0
170393	Beef, ground, 85% lean meat / 15% fat, raw	Beef Products	215	18.6	15	0			66
"""


@pytest.fixture
def foods(tmp_path):
    table = tmp_path / "foods.tsv"
    table.write_text(ROWS)
    return food_table.load(table)


@pytest.mark.parametrize("said, expected", [
    ("chicken breast", "171077"),
    ("boneless skinless chicken breasts", "171077"),
    ("cooked chicken breast", "171477"),
    ("white rice", "169756"),
    ("eggs", "171287"),
    ("extra virgin olive oil", "171413"),
    ("lean ground beef", "170393"),
])
def test_ingredients_find_the_food_a_cook_means(foods, said, expected):
    assert food_table.find(said, foods).fdc_id == expected


def test_nothing_is_guessed_for_an_unknown_food(foods):
    assert food_table.find("dragon fruit", foods) is None


def test_amounts_become_grams(foods):
    rice, egg, oil, beef = (food_table.by_id(i, foods) for i in ("169756", "171287", "171413", "170393"))
    assert food_table.grams(rice, 2, "cups") == 370  # the food's own cup, not water's
    assert food_table.grams(oil, 1, "Tbsp.") == 13.5
    assert food_table.grams(egg, 3, "") == 132  # medium eggs
    assert food_table.grams(egg, 2, "large") == 100
    assert food_table.grams(beef, 1, "lb") == pytest.approx(453.6)
    assert food_table.grams(beef, 8, "oz") == pytest.approx(226.8)
    assert food_table.grams(beef, 1, "cup") == 240  # no measure of its own: a cup of water's weight
    assert food_table.grams(beef, 1, "handful") is None


def test_a_recipes_nutrition_per_serving(foods):
    ingredients = [
        {"name": "chicken breast", "quantity": 1, "unit": "lb"},
        {"name": "white rice", "quantity": 1, "unit": "cup"},
        {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
        {"name": "a pinch of love", "quantity": 1, "unit": ""},
    ]
    result = food_table.recipe_nutrition(ingredients, 2, foods)
    per = result["per_serving"]
    # 453.6 g chicken (544 kcal, 102 g protein) + 185 g rice (675 kcal) + 13.5 g oil (119 kcal), over 2
    assert per["kcal"] == pytest.approx((544.3 + 675.25 + 119.3) / 2, abs=1)
    assert per["protein_g"] == pytest.approx((102.06 + 13.1) / 2, abs=0.5)
    assert result["missing"] == ["a pinch of love"] and result["complete"] is False
    assert [m["fdc_id"] for m in result["matched"]] == ["171077", "169756", "171413"]


def test_a_chosen_food_wins_over_matching(foods):
    result = food_table.recipe_nutrition([{"name": "chicken", "quantity": 100, "unit": "g", "fdc_id": "171477"}], 1, foods)
    assert result["per_serving"]["kcal"] == 165 and result["complete"]


def test_the_real_table_knows_the_common_ingredients():
    """data/foods.tsv (the Food table workflow builds it from the USDA's data)."""
    foods = food_table.load()
    assert len(foods) > 7000
    unresolved = [k for k in food_table.COMMON if food_table.common(k, foods) is None]
    assert unresolved == []
    assert food_table.find("2 large eggs").name == "Egg, whole, raw, fresh"
    assert food_table.find("beef broth").name.startswith("Soup, beef broth")
    assert food_table.find("dragon fruit") is None  # never a guess
    prep = food_table.recipe_nutrition([
        {"name": "chicken breast", "quantity": 2, "unit": "lb"}, {"name": "white rice", "quantity": 2, "unit": "cups"},
        {"name": "broccoli", "quantity": 4, "unit": "cups"}, {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
    ], 6)
    assert prep["complete"] and 400 < prep["per_serving"]["kcal"] < 520 and 38 < prep["per_serving"]["protein_g"] < 45


def test_a_scoop_and_never_a_cup_for_one_of_something():
    """2026-10-14: "1 scoop whey protein" was read as a cup of whey (96 g protein in a bowl of oats)."""
    from core.kitchen_actions import parse_ingredients

    whey = food_table.Food("1", "Beverages, Protein powder whey based", "Beverages", {"protein_g": 78.0}, {"cup": 97.0})
    banana = food_table.Food("2", "Bananas, raw", "Fruits", {"kcal": 89.0}, {"cup": 225.0, "medium": 118.0})
    assert food_table.grams(whey, 1, "scoop") == food_table.SCOOP_G
    assert food_table.grams(whey, 1, "") is None  # "1 whey protein": unknown, not a guess
    assert food_table.grams(banana, 2, "") == 236
    assert parse_ingredients("1 scoop whey protein")[0]["unit"] == "scoop"
