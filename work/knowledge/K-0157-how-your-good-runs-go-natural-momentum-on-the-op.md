---
id: K-0157
kind: implementation
title: How Your Good Runs Go: Natural Momentum on the Operating Journal and the glasses
status: confirmed
by: claude
created: 2026-11-09T08:06:40+00:00
concerns: core/momentum.py, core/operating_journal.py, web/operating.js, core/glasses_cards.py
from: dec:DEC-0148
---
core/momentum.picture() gives a screen the findings (counts), how many runs she's seen, how many she waits for (MIN_RUNS) and whether the person is in flow; picture_words() says what to show before there are findings. The Operating Journal screen (core/operating_journal.screen) carries it as `momentum`, shown under the lines as How Your Good Runs Go: a list of counts, never a meter, so it can't read as a score; while in flow it says only that she's holding what can wait. The glasses' Operating Journal card gained Good Runs. Glasses lines with no dash or comma near the start were cut off with an ellipsis, so _split now falls back to the last word that fits (every card benefits). The glasses card tests now stub core.inspection.inspect: the PC Health card had been writing inspection reports into the real data folder.
