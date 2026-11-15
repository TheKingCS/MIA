# MIA OS: future capability opportunities (Prompt 02 §13)

*Claude, 2026-11-15.*

*Labels:*
- *Phase: OS-1 = first MIA OS release; later = after it; research = not planned.*
- *Diff: difficulty, rated H, M or L.*

| Opportunity | Problem it solves | Needs | Privacy | Diff | Phase |
|---|---|---|---|---|---|
| **Send to MIA on a selection** (Zac) | acting on what you're looking at without copying and pasting between apps | Android PROCESS_TEXT and share now; Windows hotkey; MIA OS selection service | selection is untrusted; nothing sent anywhere without a choice | L (phone), M (OS) | **phone now, OS-1** |
| Natural-language system control ("close what's frozen") | operating the PC by asking | System Manager, grants (DEC-0156/0158) | high | H | OS-1 (read-only first) |
| Semantic search across stores and files | finding by meaning | local embeddings (Prompt 07) | local only | M | OS-1 or later |
| Predictive workspace preparation | the right things open when you start | workspaces, rhythms (the Loop) | low | M | later |
| A personal knowledge graph | relationships across people, projects, files | `core/links.py` exists; derive more | medium | M | later |
| Discretionary-money service | "can we afford it?" answered honestly | finances | sensitive | L | **now (LEP)** |
| Closet try-on images (pieces shown together) | seeing an outfit before wearing it | photos; a local image model or a simple collage first | photos stay local | L (collage) – H (generated) | collage now, generated later |
| Predictive maintenance (house, vehicles, greenhouse) | fewer surprises | sensors, upkeep missions | low | M | later |
| Energy monitoring | lower bills | power sensors | low | M | later |
| Agent-made workflows | repeating multi-step jobs | taught procedures (DEC-0123), Prompt 08 | medium | H | later |
| Wearable and spatial experiences, Zeta Astralis | hands-free context | hardware | high | H | research |
| Neural input | — | hardware | very high | H | research |

**Not to inflate OS-1:** only the rows marked "now" or "OS-1" are candidates. The rest wait for their own decision.
