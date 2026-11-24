---
id: K-0397
kind: debugging
title: A unit word alone doesn't make a record the thing
status: confirmed
by: claude
created: 2026-11-24T10:36:05+00:00
concerns: core/firewood.py, core/seed_life.py
from: commit:a85b1687, commit:441d9729
---
A nineteenth fresh review: firewood counted any record with cord in its name (bungee cords x6 was 6 cords of firewood, an extension cord too); fractions (1/2 cord read as 2, .5 as 5) and words (half cord) were misread or dropped; a record with an amount in its name but a count of 0 was counted. Now only firewood words, or a kind of wood with a cord measure, count; fractions and words are read; a face cord is its piece length over 48 inches. Seed shelf life: sprouts mapped every sprout to Brussels sprouts; a name with two crops counted for one; a packed-for year counted a year young.
