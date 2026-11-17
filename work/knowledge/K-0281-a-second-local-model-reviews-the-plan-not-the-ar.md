---
id: K-0281
kind: decision
title: A second local model reviews the plan, not the arithmetic (S5)
status: confirmed
by: claude
created: 2026-11-17T08:52:33+00:00
concerns: core/specialist_review.py, core/specialist_work.py, core/eng_calcs.py
from: commit:8ac4c8df, commit:46d9a8ab, dec:DEC-0198
---
core/specialist_review.py. The worksheet already computes every number in code and traces every figure in the words, so the only things a model can still get wrong are choosing the wrong calculation and reading an input wrongly from the question. The reviewer is asked exactly that, in JSON (agree, or the problem); anything else is not reviewed, never agreement. Reviewer: the best other model on the bench for the same work. Independent only across families (re.split on the name: qwen2.5 and qwen3 are both qwen), and every capable model on this PC is a qwen, so reviews say not fully independent; a capable Llama or Mistral would fix that. Reviews only for safety-critical results (the caveat) or on request (work_it_out check), because two 32B models swap on the 24 GB card. A doubt sets held and is said first. Also added: structural and crafts calculators (stair risers, board feet, concrete, soap lye from published NaOH values, alum) and 12 bench tasks; a test question routed to a specialist without the calculator made an assertion pass for the wrong reason, so the review test now checks status first. Gotcha: running the 32B model ran the 31 GB PC out of memory twice; run it alone.
