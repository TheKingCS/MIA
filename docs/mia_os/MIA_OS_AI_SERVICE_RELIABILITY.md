# MIA OS: AI service reliability (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Failure | Response | Exists |
|---|---|---|
| Ollama stopped | self-repair starts it (on its own thread), reloads the model, tells him | yes (DEC-0222) |
| A model missing | the setup check says which and how to get it; another model routes in | partial |
| The GPU busy or hung | the queue; timeouts; the turn falls back to code or a smaller model | partial |
| A model answering badly after an update | the bench before use; the old one kept | partial |
| Voice models missing | the setup check; typing still works | yes |
| The everyday model slow | flash attention and the 8-bit cache (tuned 2026-11-18) | yes |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-032 | Every screen and every code-answered question shall work with the model server down. | Must | MVP | All | Exists (REQ-REL-001) | T | DEC-0255 → 14 |
