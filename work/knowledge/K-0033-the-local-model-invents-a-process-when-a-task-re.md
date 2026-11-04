---
id: K-0033
kind: lesson
title: The local model invents a process when a task record is thin
status: confirmed
by: claude
created: 2026-11-04T08:26:50+00:00
concerns: core/dev_knowledge.py, reviewer:ollama
from: task:T-0024
---
Asked to write up 11 finished tasks whose records held little more than created, claimed and done, qwen2.5:14b wrote 30 entries, most describing test failures, reviews and disagreements that never happened (K-0003 to K-0032, withdrawn). A write-up now needs a record with substance (the loop, reviews, answers, a revert), and the prompt says no entries is a good answer. Check derived entries against their sources before trusting them.
