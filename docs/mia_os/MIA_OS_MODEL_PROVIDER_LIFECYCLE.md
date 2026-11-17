# MIA OS: model and provider lifecycle (Prompt 07 §16)

*Claude (Opus), 2026-11-17. Planning only.*

| Stage | What happens | Gate |
|---|---|---|
| **Candidate** | a model is named (by Zac, a specialist's need, a reviewer from another family) | — |
| **Pulled** | downloaded to the device that will run it | disk room (REQ-HW-013) |
| **Measured** | the evaluation sets for its intended classes run | REQ-INT-027 |
| **Inspected** | Claude reviews the results for each specialist it would serve | DEC-0200 |
| **In use** | the registry routes to it for the classes it passed | REQ-INT-007 |
| **Updated** | a new version is a new candidate; the old stays until the new passes | no silent upgrades |
| **Retired** | removed from routing; deleted when its disk is wanted | the registry keeps its record |

**Providers:** the same, one level up. Ollama's updates come with the image (Prompt 14) and are re-measured; a cloud
provider is added only with Zac's yes and only for the uses he names (DEC-0207).

**Known hazard:** a runner update can change behaviour silently (embedding inputs lowercased by one Ollama release,
per a 2026 guide), so every runner update re-runs the sets and re-embeds if the embedding output changed.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-031 | A new model or a new version shall be used only after it's measured and inspected; the old one stays until then. | Must | R1 | All | Partial (specialists) | T | DEC-0208, DEC-0200 → 07 |
| REQ-INT-032 | A runner update shall re-run the evaluation sets and re-embed the recall index when embeddings changed. | Must | R1 | PC | New | T | DEC-0210 → 07, 14 |
