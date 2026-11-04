# Blueprints

What MIA builds her screens from (DEC-0090; ACAF, `docs/ACAF_REVIEW.md`). A
blueprint is a layout of blocks (`core/creation_spec.py` `BLOCKS`) with fields
named by **role**, not by name. `core/blueprints.py` fills the roles from a
record set's fields:

| Role | The field it takes |
|---|---|
| `$title` | the first text or choice field |
| `$date` | the first date field |
| `$group` | the first choice or yes/no field, else the second text field |
| `$number` | the first money or number field |
| `$all` | every field (a table's columns) |
| `$details` | every field but `$title`, up to three |

A block whose role has no field is left out, and so is a stat item. Text
mentioning a role (`"By $group"`) gets the field's label.

Blueprints are versioned here, in the repo, and changed through the lab and
review like code: they're what every screen is built from. A creation keeps
the version it was made with. MIA can also skip a blueprint and lay out her
own blocks, which the checker holds to the same rules.
