---
id: K-0405
kind: implementation
title: A batch of meat birds is a mission to processing day
status: confirmed
by: claude
created: 2026-11-24T11:57:00+00:00
concerns: core/broiler_batch.py, core/assistant_goods_actions.py
from: commit:5258c258
---
core/broiler_batch.py: broilers.start makes one mission from BREEDS (Cornish cross 8 weeks and about 15 lb of feed a bird, rangers 11 and 20, heritage 16 and 30): brooder, off the heat, a 12-on 12-off feeding schedule for Cornish cross from week 2, pasture, processing day with feed pulled the night before. Built like the hatch after its review: the batch saved inside the change, the day read looking back (hatch_tracker.set_day), a long-done batch refused, finished entries dropped.
