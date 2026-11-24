---
id: K-0393
kind: debugging
title: config.set doesn't save: an action that keeps a setting must save it inside the change
status: confirmed
by: claude
created: 2026-11-24T09:57:25+00:00
concerns: core/hatch_tracker.py, core/debt_missions.py, core/assistant_goods_actions.py
from: commit:0740e76c
---
An eighteenth fresh review of 0740e76c: hatch.start kept its hatch with config.set and never saved, so a restart lost it, and a later undo of any change that did save config would drop it. The debt payoff mission (debts.missions) had the same bug. Both save inside the change now, so undo takes the setting back with the mission. Also: the day set read looking back (day_of looks forward, so yesterday was refused and Sunday became next Sunday); a long-over hatch refused; the date always named so a card approved later keeps it; hatch_status no longer answers the business incubator, a school lockdown or a hatchback; muscovy (35 days) and bobwhite (23) have their own days.
