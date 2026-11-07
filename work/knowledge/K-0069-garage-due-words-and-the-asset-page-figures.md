---
id: K-0069
kind: implementation
title: Garage due words and the asset page figures
status: confirmed
by: claude
created: 2026-11-07T15:32:01+00:00
concerns: core/web_equipment.py, web/equipment.js, web/asset.js
from: commit:90c571c, dec:DEC-0113
---
The canvas's Garage card says when each task is due in plain words, so core/web_equipment.due_words works them out in code from the same due-date functions as the old status text (which stays for the rows and chips): Past due N days / Due today / Due tomorrow / Due in N days up to a month, then the month name (with the year when it isn't this year); a meter task says what's left (Due in 188 mi, Past due 20 h). Never scolding (DEC-0014). meter_reading gives the card the asset's latest meter reading across its meter tasks. The asset page adds costs.this_year (upkeep expenses tagged to it this calendar year, the purchase never counted) and costs.recent (its last five upkeep expenses). Needs-you outlines are amber everywhere; red stays for real errors.
