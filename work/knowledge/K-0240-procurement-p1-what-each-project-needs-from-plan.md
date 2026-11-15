---
id: K-0240
kind: implementation
title: Procurement P1: what each project needs, from plans and his words
status: confirmed
by: claude
created: 2026-11-15T16:48:50+00:00
concerns: core/requirements.py, core/requirement_actions.py, core/assistant_requirement_actions.py, core/plan_actions.py, core/relevance.py, web/intel.js
from: dec:DEC-0172
---
What: core/requirements.py (Requirement: project, item, quantity, unit, specs, alternatives, fits, max_price, condition, priority, needed_by, status needed/partial/owned/found/ordered/acquired, have, origin, how; RequirementBook, a household store beside projects, under the epistemic contract), core/requirement_actions.py (requirement.add/update/got/remove/check), core/assistant_requirement_actions.py (project_needs, add_need, got_need, drop_need), the World page's Needs tab, and the hook in plan.project and start_plan_project: a project started from a plan gets the plan's materials as its needs, quantities computed in code (how="computed", origin plan:<id>).

How "on hand" works: refresh_owned matches each open line to the workshop's materials and the household inventory with the plan library's own _match (exact name, else all main words), adds what's on hand, and marks owned / partial / needed. Lines ordered, acquired or found are never re-marked by a check.

Linked to World Intelligence: every open line is a relevance anchor (weight 3, "what Greenhouse needs, polycarbonate panel") and so gets one of MIA's own watches; a find that fits a need ranks first.

Choices: requirements are a household store because projects are; trigger phrases for the voice tools are narrow on purpose ("I bought the..." belongs to the budget's tools); got_need only marks acquired: P5's "I bought it" adds the inventory, budget and price record. Projects started before this have their materials only as description text, so they have no needs until he adds them.
