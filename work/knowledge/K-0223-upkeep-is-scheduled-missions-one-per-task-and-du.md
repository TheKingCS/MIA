---
id: K-0223
kind: implementation
title: Upkeep is scheduled missions, one per task and due date
status: confirmed
by: claude
created: 2026-11-11T08:31:43+00:00
concerns: core/upkeep_missions.py, core/actions.py, core/application.py, core/maintenance_manager.py, core/mission_manager.py
from: dec:DEC-0153, file:core/upkeep_missions.py
---
DEC-0153 (Zac, 2026-11-11). The maintenance schedule stays the record; core/upkeep_missions.py makes one mission per task occurrence due within 7 days (or overdue), keyed upkeep:<task>:<date> in Mission.occurrence_key, attached through maintenance_task_id and maintenance_asset_id (so the asset's page lists it, and a property through its maintenance asset), type SCHEDULED MISSION, by MIA, one 'Done' tally, home_maintenance XP. It runs in the daily recurring-missions check (settle, then ensure). Both directions without doing anything twice: the maintenance.done action calls settle(), which completes the open mission when the task's last_completed is on or after the mission's creation day; a mission completed in Missions fires mission.completed and _on_completed marks the task done unless it already was since. A mission set aside isn't remade for the same date; a deleted task sets its mission aside. The Calendar and Your Week already showed the same occurrence from the schedule, with Done, so neither keeps a copy.
