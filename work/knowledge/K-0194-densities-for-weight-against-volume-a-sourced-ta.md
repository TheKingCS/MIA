---
id: K-0194
kind: implementation
title: Densities for weight against volume: a sourced table, never a guess
status: confirmed
by: claude
created: 2026-11-09T07:05:20+00:00
concerns: core/units.py, core/craft_recipes.py, tests/test_unit_converter.py, tests/test_homestead_goods.py
from: dec:DEC-0036
---
DEC-0036's rule kept, 2026-11-09: core/units.convert(quantity, from, to, material) converts weight to volume only when the material's name matches DENSITIES (grams per ml, from King Arthur Baking's Ingredient Weight Chart: grams a US cup over 236.6 ml; glycerin from its handbook density), the longest matching name first so 'brown sugar' isn't 'sugar'. Anything else still returns None and the Workshop says 'check' (beeswax pellets, lye: their bulk density depends on the form). craft_recipes._stock_amount passes the material's name. The homestead test that pinned flour's old mismatch now checks beeswax for that path and flour converting.
