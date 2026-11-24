---
id: K-0422
kind: implementation
title: Harvests by voice, and what the garden produced
status: confirmed
by: claude
created: 2026-11-24T14:43:14+00:00
concerns: core/harvest_log.py, core/assistant_project_plan_actions.py
from: dec:DEC-0125
---
core/harvest_log.py: log_harvest finds his growing grow-lab batch of the crop (_same_crop: plurals alike, tomatoes/radishes/peas) and runs batch.harvest as the Greenhouse page does; none growing adds a batch first (two undoable actions); two growing asks which, by place. harvest_this_year totals this calendar year by crop and unit (unit_of: lbs and pounds alike) and values a crop only at a price he recorded for it in the same unit in the last year, each store latest, the cheapest; otherwise it is said as not valued. Before this the grow lab kept harvests only from its screen.
