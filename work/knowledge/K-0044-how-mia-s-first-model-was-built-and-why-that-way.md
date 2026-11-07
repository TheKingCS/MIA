---
id: K-0044
kind: method
title: How MIA's first model was built and why that way
status: confirmed
by: claude
created: 2026-11-07T05:17:37+00:00
concerns: core/model_forge.py, tools/model_forge.py
from: dec:DEC-0106, file:core/model_forge.py
---
What: the tool router in core/model_forge.py, the first model of her own (DEC-0106 stage 1).
How: softmax regression (one weight per word feature per tool) over word stems and neighbouring word pairs, trained by plain gradient descent in numpy. The training set is each tool's own name, description, trigger phrases and subjects, about 2,000 examples of 222 tools; nothing a person said. It is scored on the routing corpus, real requests it never trained on.
Why this way: it needs no library MIA doesn't already have, runs in milliseconds on any of her devices, and is simple enough to understand completely: every number in it is a word's pull toward a tool. No randomness, so the same data always makes the same model and a result can be checked by running it again. A neural network would come later, when there's enough data for one to beat this.
Run it: python -m tools.model_forge router; see every model: python -m tools.model_forge list.
