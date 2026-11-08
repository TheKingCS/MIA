---
id: K-0140
kind: lesson
title: Compounding value must be a share of the work, and seasonal income averaged
status: confirmed
by: claude
created: 2026-11-08T18:21:15+00:00
concerns: core/development_engine.py, tests/test_development_engine.py
from: dec:DEC-0144
---
Deepening the homestead chains (a coop, a feed bin and a flock before selling eggs) broke the ranking three ways, each caught by walking realistic scenarios by hand, not by the tests. (1) compounding_value credited a step with the whole benefit of what it unlocks: a $25 feed bin got a $40/month flock and outranked selling seedling starts that were ready. Now a step earns its share of all the work still needed to reach the thing (its money and hours against the cheapest provider of each other need, plus the thing's own effort, _share_of_work). (2) selling starts was worth $60 every month, but it sells in spring only; averaged over the year it's $20, and with that a built coop in May rightly leads to hens. (3) inferring 'only one candidate provides this need, so it must exist' is wrong for a general need: a greenhouse needs water, but a hose isn't a rain barrel. Only needs that mean one thing (IMPLIED_TAGS: a coop, a feed bin) are inferred from a finished step. A slow provider (finished compost, months) is chosen on a path only when nothing quicker meets the need, or a spring batch would miss its season.
