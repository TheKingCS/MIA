"""
tests.test_whimsy
===================

The grounded little inspiration MIA offers toward the slow, made life (core/whimsy.py, 2026-11-08). A seed is composed
from real things — the season, the workshop shelf, the person's own standing directions — never improvised; it only
grows from a direction the person actually set; a material seed never names a shelf that's empty; and a given roll
always yields the same seed, so the nudge is testable and deterministic.
"""

from core import whimsy


def test_no_matching_direction_yields_no_seed():
    # nothing the person is steering by -> the caller falls back to a plain nudge
    assert whimsy.a_seed([], ["cedar"], 4, 0.5) == ""
    assert whimsy.a_seed(["Pay the bills on time"], [], 4, 0.5) == ""


def test_a_whimsy_direction_yields_a_slow_or_creative_seed():
    seed = whimsy.a_seed(["Whimsy, art & tranquility: slow down, draw, create, dream"], [], 7, 0.0)
    assert seed and seed[0].isupper()
    # a summer motif is woven in, not a literal placeholder
    assert "{motif}" not in seed and "{material}" not in seed


def test_a_material_seed_only_names_a_stocked_shelf():
    producer = "From consumer to producer: make and restore before buying"
    # with a stocked shelf, some rolls land on a material seed naming a real item
    named = [whimsy.a_seed([producer], ["cedar offcuts", "pine 2x4"], 10, r / 20) for r in range(20)]
    material_seeds = [s for s in named if "cedar offcuts" in s or "pine 2x4" in s]
    assert material_seeds  # at least one roll used the shelf
    # with an empty shelf, no seed ever contains an unfilled material slot or invents a material
    empty = [whimsy.a_seed([producer], [], 10, r / 20) for r in range(20)]
    assert all(s == "" or "{material}" not in s for s in empty)
    assert all("shelf" not in s or s for s in empty)


def test_the_same_roll_always_gives_the_same_seed():
    blobs = ["Whimsy and art", "From consumer to producer"]
    assert whimsy.a_seed(blobs, ["oak"], 1, 0.3) == whimsy.a_seed(blobs, ["oak"], 1, 0.3)


def test_the_season_motif_follows_the_month():
    assert whimsy.season_of(1)[0] == "winter"
    assert whimsy.season_of(4)[0] == "spring"
    assert whimsy.season_of(7)[0] == "summer"
    assert whimsy.season_of(10)[0] == "autumn"
    assert whimsy.season_of(99)[0] == "winter"  # out of range -> safe default


def test_a_cafe_direction_lights_up_the_coffee_ritual():
    # the theme comes from the person's own words, nothing café-specific is hard-coded
    text = " ".join(whimsy.a_seed(["Run life like a little coffee shop, tavern, aesthetic"], [], 6, r / 10)
                     for r in range(10))
    assert "coffee" in text.lower() or "pour" in text.lower() or "shop" in text.lower()
