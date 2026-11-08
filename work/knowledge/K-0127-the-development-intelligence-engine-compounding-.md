---
id: K-0127
kind: implementation
title: The Development Intelligence Engine: compounding value over a dependency graph
status: confirmed
by: claude
created: 2026-11-08T16:21:55+00:00
concerns: core/development_engine.py, core/web_grow.py, core/assistant_homestead_actions.py
from: dec:DEC-0144, commit:981b04eb, commit:2cc27cc0
---
core/development_engine.py decides what's worth doing next from what the person has. Each Candidate carries requires/provides capability tags and the ids it unlocks, so the dependency graph lives in the catalog itself. score() lets the gates dominate (unaffordable or blocked costs -1000, out of season -15) so an out-of-reach project always sinks below a doable one; among doable ones, monthly benefit plus compounding_value wins: the benefit of what it unlocks, discounted by half a hop, two hops deep, skipping anything already done. next_step() falls back in order: do it, wait for its season, save toward it, or clear the prerequisite. Two bugs found when wiring it to a screen: an unknown budget was 0.0, so everything read as unaffordable (now None means 'say the cost, don't judge it'), and it recommended what the person already had, so done_from_records() reads assets, finished projects, grow-lab systems and flocks against each candidate's evidence words. plan()/describe() are shared by the get_homestead_next_step tool and the Greenhouse's What's Next tab, so voice and screen can't drift. The handoffs' Zero-to-Something benchmark is tests/test_development_engine.py.
