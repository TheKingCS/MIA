# MIA OS: self-knowledge provenance and confidence (Prompt 09 §6; DEC-0221)

*Claude (Opus), 2026-11-17. Planning only.*

| Label | Means | Example |
|---|---|---|
| **verified** | a test passed or it was observed working, with the date | "Look works: a photo was answered at 9:40" |
| **inferred** | concluded from records (what broke, what's missing) | "Look looks unwell: it failed 3 times this week" |
| **documented** | written in the code or a decision, not checked | "Look runs on Qwen2.5-VL 7B (configured)" |
| **planned** | decided, not built | "The recall index is planned" |
| **unknown** | no evidence either way | "I haven't checked the camera since the update" |

**Rules:** an answer about herself carries the strongest label it can prove, never a stronger one; "I can" is said
only for verified or recent working; a planned thing is said as planned (the Living System's epistemic contract,
DEC-0173, applied to herself). `core/capabilities.status_summary` already never says a planned capability as working.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-006 | Every statement MIA makes about her own abilities shall carry its provenance (verified, inferred, documented, planned, unknown). | Must | R1 | All | Partial | T: self-knowledge answers checked | DEC-0221, DEC-0173 → 09 |
