# H-0006: Muse's review of H-0005 and the Phase 2 proposal
- From: muse · To: zac, claude, chatgpt · Date: 2026-10-05
- Related: H-0005, DEC-0012, DEC-0013, DEC-0014, Q-0007, Q-0009, Q-0003, Q-0008, DEC-0008

## Context
H-0005 asks for Muse's review before Zac decides DEC-0012/DEC-0013. This handoff records the review as a whole. My answers to Q-0007 and Q-0009 are filed in `docs/QUESTIONS.md`, the Witness Principle is proposed as DEC-0014, and the design half of Q-0003 is answered there too.

## Verdict
- **DEC-0012 option A: support.** It kills the artifact→Qt translation bottleneck, and the concept-art look (glowing, layered HUD) is out of reach in Qt stylesheets. Conditions: everything stays offline (no external dependencies — fonts, icons and libraries bundled locally); one design-token file owns the visual language across every surface; the Qt screens keep working until each web replacement is actually better (nothing strands Zac mid-session).
- **DEC-0013: support, including the ordering.** Foundation → Home/presence → Talk → domain screens → glasses cards. Each step is shippable and visible. My Q-0004 answer already gives Home's ordering contract against Life State v2, so the foundation has a spec to build toward.

## Constraints the plan must keep
1. **"Home" = presence, never the dashboard-overview.** Zac's standing veto holds (the chat handoff's Home section rebuilds what he already rejected): the overview is a briefing surface one tap/ask away. H-0005's step 3 ("Home and MIA's presence") is right only if "Home" stays the Q-0004 presence surface.
2. **DEC-0014 governs proactivity on every surface.** Web, Talk, glasses cards: loud about earned progression, quiet about everything else; celebration names the specific thing the person did (Q-0009).
3. **One component set, glasses included.** Q-0003's platform answer decides the renderer, but the card contract (one idea per card, answer-first, ~600×600 working assumption, voice for the rest) holds either way — no separate glasses card system.
4. DEC-0002, DEC-0005, DEC-0007 hold as written: placeholders only in the repo, surfaces consume `/api/state`, status taxonomy on everything.
5. Guardrail (DEC-0008) run for DEC-0012(A), in full: (1) the engine support exists — the local FastAPI server (`server/app.py`) already serves the phone app; (2) that's the layer it lives at; (3) the shared front end is genuinely missing, not just hidden — the engine side is REAL; (4) it belongs entirely in the UI, consuming `/api/state` and `/api/actions`, nothing engine-side; (5) it removes the artifact→Qt translation step rather than duplicating anything; (6) it reads Life State, doesn't extend it; (7) no new life events — actions go through the existing history/undo path; (8) no new links; (9) it consumes `/api/state`, doesn't need it extended; (10) the screens are REAL where the schema has the fields, marked PLANNED where it doesn't (DEC-0007). Passes.

## Design-side requirements for the foundation
- Starter `web/` layout with static serving and the desktop shell wiring, a dev-server command, and a mock `/api/state` from `docs/schema/life_state.example.json` — enough for me to start before the real endpoints exist (per my Q-0007 answer).
- The action API stays propose-then-approve with undo (DEC-0009); the UI never mutates silently.
- Nothing is built until Zac decides DEC-0012 — Claude's foundation first, my Home/presence slice on top of it.

## What's needed from each of us
- **Zac:** DEC-0012, DEC-0013, DEC-0014; Q-0003 (glasses platform/access); Q-0005 (public repo); Q-0001, Q-0002.
- **Claude:** the foundation (web/, the action API, live updates, the Pi check) once DEC-0012 is decided.
- **ChatGPT:** Q-0008, the vision review.

## Acceptance criteria (design additions to H-0005's)
- Home shows the presence and the one due item from `/api/state` with live updates, in the Q-0004 ordering, status-labeled per DEC-0007.
- The Pi check includes frame rate on the actual Pi 5 kiosk before Talk is built on it.
- Every old Qt screen stays reachable until its web replacement is better.
