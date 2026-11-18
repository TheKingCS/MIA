# MIA OS: what depends on what (Prompt 16)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18.*

```mermaid
flowchart LR
  USB["USB stick (Zac)"] --> M1["M1 GPU on Linux"]
  CF["Containerfile (built)"] --> M2["M2 image boots in VM"]
  M2 --> M3["M3 MIA's session (KWin)"]
  M2 --> M4["M4 updates, rollback, helper, TPM"]
  KEY["phone signing key (Zac)"] --> M5["M5 signed releases"]
  M4 --> M5
  DRIVE["4 TB drive + enclosure (Zac)"] --> M6["M6 installed, data moved"]
  M1 --> M6
  M3 --> M6
  M4 --> M6
  M6 --> M7["M7 the MVP (a week)"]
  M7 --> M8["M8 R1"]
  PI["Pi on the TV"] --> M8
  LAP["the laptop"] --> M8
  M0["M0 backlog on Windows"] -.carries over.-> M6
```

Every arrow from a box marked Zac is his hands-on step; nothing else on the critical path needs buying.
