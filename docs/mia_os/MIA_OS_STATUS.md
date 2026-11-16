# MIA OS status

*Updated 2026-11-15 (evening) by Claude.*

**Phase:** planning.

**Where we are:**
- Prompt 01 is done and reviewed.
- Prompt 02 (the feature ecosystem) is done.
- Prompt 03 (the application framework) is done: `MIA_OS_APPLICATION_FRAMEWORK.md` and sixteen supporting documents.
- Prompt 03 reviewed (DEC-0175 to 0177 approved). Prompt 22 (the runtime-owned app ecosystem) is planned in
  `MIA_OS_APPLICATION_REGISTRY.md`; DEC-0178 approved, and M1 is built: every app has a manifest in `apps/<id>/`,
  and a test checks they claim everything in the code exactly once. M2 is built: she answers questions about her
  apps by voice and on the Apps page. M3 is built: the app list is read from the manifests. M4 is built (DEC-0156 approved): every tool and action has a tier, the
  grant check is on, and her grants are listed and taken back in one place.
- **Prompt 04 (requirements and system philosophy) is done** (Opus, 2026-11-15): `MIA_OS_SYSTEM_REQUIREMENTS.md`
  and fifteen supporting documents; 194 requirements, traced and tested; DEC-0179 to DEC-0182 proposed.
- **Next:** Zac's review of Prompt 04 (Q-32 to Q-36); then Prompt 05 on his go. Prompt 23's review is the next
  Fable session's.
- Prompts 18–20 (World Intelligence, Procurement, the Living System) are approved and being built; Prompt 21 waits for 17.

**Changes outside the planning documents, on Zac's say-so:**
- The Companion app was retired (DEC-0160).
- The phone app's signing key now comes from the repository's secrets when they're set (DEC-0160).
- Smart Closet is being built (DEC-0162).

**Last verified test result:** the Linux run on 2026-11-15 (see `MIA_OS_TESTING_AND_QUALITY_AUDIT.md`).

**Waiting on Zac:**
- Q-32 to Q-36 (Prompt 04's review), then the go for Prompt 05;
- add the two signing secrets (steps in the hub);
- Q-08 and Q-09 in `MIA_OS_OPEN_QUESTIONS.md`.
