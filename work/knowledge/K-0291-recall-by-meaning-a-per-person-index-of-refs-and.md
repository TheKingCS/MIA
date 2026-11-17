---
id: K-0291
kind: implementation
title: Recall by meaning: a per-person index of refs and vectors
status: confirmed
by: claude
created: 2026-11-17T13:21:56+00:00
concerns: core/recall_index.py, core/meaning.py, core/background_jobs.py
from: dec:DEC-0210
---
What: core/recall_index.py (DEC-0210, Q-71). SOURCES: user_memories, the plain journal, life_notes and projects (never the private journal; conversations a later slice). RecallIndex (recall_index.json in his folder, a personal store) keeps ref -> {text hash, vector, when} and the model that made them; the job recall_index refreshes every 10 minutes (BATCH at a time, held by stop everything), dropping refs whose records are gone and re-embedding changed text. search() embeds the question (nomic's search_query / search_document prefixes), ranks by cosine above MIN_SCORE, re-reads every hit from its store and forgets a ref whose record is gone; with no embedding model it matches words and says so. The tool recall answers "what do I have about...".
Why that way: the plan's rule that the index never holds a record (so an erase can't be undone by a stale vector) and Q-71's exclusions. It calls Ollama's /api/embed itself instead of core/meaning.embed, whose cache is device-wide (data/cache/meaning.json): his vectors stay in his folder. JSON instead of sqlite-vec for now: brute force is fine at his scale (12 memories took 1.4 s to embed).
