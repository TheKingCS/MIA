---
id: K-0395
kind: implementation
title: Seed shelf life from a table and the year in his packet names
status: confirmed
by: claude
created: 2026-11-24T10:13:08+00:00
concerns: core/seed_life.py
from: commit:9057d040
---
core/seed_life.py: YEARS holds each kind's usual viability stored cool and dry (common extension figures: onion and parsnip 1, pepper and corn 2, tomato 4, cucumber and radish 5...). His packets are pantry or inventory items named as seeds; a year in the name (tomato seeds 2024) dates them: good inside the span, worth a germination test in its last year or one past, old beyond. No year is asked for, never guessed. seed_viability is read-only (observe).
