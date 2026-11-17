# MIA OS: rendering and performance (Prompt 11 §20)

*Claude (Opus), 2026-11-17. Planning only. The GPU is shared with her models (DEC-0204).*

| Level | When | Blur | Particles | 3D room | Animation |
|---|---|---|---|---|---|
| Full | desktop, idle GPU | yes | yes | yes | all |
| Light | phone, battery, low-end GPU, models generating | no | no | paused | meaningful only |
| None | his choice, reduced transparency, safe mode | no | no | off | meaningful as fades |

**Automatic step-down:** "auto" effects pick full or light by device and by whether a model is generating (the GPU
queue's state, DEC-0204); the shell never competes with an answer. **Budgets:** shell idle < 600 MB (REQ-DSK-027),
no continuous GPU work at idle; a transition 60 fps; blur only on floating and primary tiers at full.
**Measured:** a page-performance test per theme (frame time while opening Talk and a dashboard) before release.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-026 | With effects on auto, the shell shall drop to light effects while a local model is generating and return when it ends. | Should | R1 | PC | New | T | DEC-0238, DEC-0204 → 11 |
