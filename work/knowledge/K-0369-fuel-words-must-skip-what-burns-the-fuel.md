---
id: K-0369
kind: debugging
title: Fuel words must skip what burns the fuel
status: confirmed
by: claude
created: 2026-11-24T05:58:25+00:00
concerns: core/power_ready.py, core/assistant_today_actions.py
from: commit:e751255c
---
A tenth fresh review of core/power_ready.py found: a gas generator, propane torch or heater, diesel exhaust fluid and gas line antifreeze were counted as fuel (a generator tank size read as gallons on hand); a pantry unit of lb, quarts or liters was not read; a used-up can was told to give a size; half a gallon said no fuel; fuel it could not measure was said as no fuel; and gas or LP were refused as the generator fuel, with propane rates usually in pounds an hour. Fixed with _NOT_FUEL, unit tables, a skip for none left, a less-than-a-day line in hours, SAID_AS for fuel words, and generator_lb_per_hour turned to gallons.
