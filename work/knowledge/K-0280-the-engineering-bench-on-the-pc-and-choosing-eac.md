---
id: K-0280
kind: lesson
title: The engineering bench on the PC, and choosing each specialist model from it
status: confirmed
by: claude
created: 2026-11-17T08:38:24+00:00
concerns: core/eng_bench.py, core/specialist_models.py, tools/eng_bench.py, core/eng_calcs.py
from: commit:0f6ea014, commit:fb42af56, dec:DEC-0197
---
First full run of core/eng_bench.py on the 24 GB card (2026-11-17), four models, alone and with calculators. With calculators qwen2.5:32b was right on all electrical and greenhouse tasks and never guessed (about 4 s a task); qwen3:14b best on embedded, never guessed, 10 s; qwen3-coder:30b fastest (0.4 s) but guessed a missing input in every discipline; alone, all were far worse on greenhouse and crafts. What the run taught: (1) a thinking model thinks without end unless num_predict is capped (an hour on 36 tasks); strip <think> before scoring. (2) A hint in an input description (about 1.15) is copied as a value instead of asking: descriptions never offer values, and a test holds that. (3) A placeholder for the missing input (unknown mAh) is a form slip, not a guess; only a readable value is. (4) Rank fewest guesses before the share right: a guessed input is invisible in the answer. (5) Rank discipline coverage first, or a model benched on less wins. (6) Killing the python of a bash for-loop only moves the loop to the next model: kill the loop. (7) Run the suite and the bench apart; together they ran the 31 GB PC out of memory. A discipline with three tasks (crafts) can neither pass nor fail honestly: grow it.
