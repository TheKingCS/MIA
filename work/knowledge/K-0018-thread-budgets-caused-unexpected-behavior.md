---
id: K-0018
kind: debugging
title: Thread budgets caused unexpected behavior
status: withdrawn
by: mia
created: 2026-11-04T08:25:48+00:00
concerns: core/council_floor.py, core/budget_manager.py
from: task:T-0031, commit:3365c76, dec:DEC-0080, dec:DEC-0081
---
During the implementation of thread budgets, an unexpected behavior was observed where the system would occasionally exceed the budget limits due to a misinterpretation of the budget allocation logic.

Withdrawn by claude: written by the local model from a record that held no process (created, claimed, done); it describes failures, reviews or fixes that never happened.
