---
id: K-0290
kind: failed-experiment
title: qwen3:14b as the everyday model: not better on his questions
status: confirmed
by: claude
created: 2026-11-17T13:19:17+00:00
concerns: tools/intelligence_check.py, core/llm_manager.py
from: dec:DEC-0208
---
What: Q-68 (DEC-0208), measured 2026-11-17 with tools/intelligence_check --model on the 112 Intelligence Benchmark questions, qwen2.5:14b against qwen3:14b (thinking off, as Talk needs). Code grades: identical routes; one flag each (different questions, both in B's freedom plan); research median 2.7 s against 2.5 s; total model time 66 s against 84 s. Read side by side, the 15 open research questions ("what tools would make this project easier?", "is this information still accurate?") showed qwen3:14b inventing context three times where it should have asked what "this" was, qwen2.5:14b once.
Why it matters: most questions are answered by question plans in code, so the model mostly shows in open questions; asking beats inventing there. Keep qwen2.5:14b; measure again when a new family comes out, on the same questions.
