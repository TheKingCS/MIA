# MIA OS status

*Updated 2026-11-15 (evening) by Claude.*

**Phase:** planning.

**Where we are:**
- Prompt 01 is done and reviewed.
- Prompt 02 (the feature ecosystem) is done.
- Prompt 03 (the application framework) is done: `MIA_OS_APPLICATION_FRAMEWORK.md` and sixteen supporting documents.
- Prompt 03 reviewed (DEC-0175 to 0177 approved). Prompt 22 (the runtime-owned app ecosystem) is planned in
  `MIA_OS_APPLICATION_REGISTRY.md`; DEC-0178 (the manifest format) waits on Zac (Q-30).
- **Next:** Prompt 04, on Opus (DEC-0166 assigns it to Opus), once Zac says go.
- Prompts 18–20 (World Intelligence, Procurement, the Living System) are approved and being built; Prompt 21 waits for 17.

**Changes outside the planning documents, on Zac's say-so:**
- The Companion app was retired (DEC-0160).
- The phone app's signing key now comes from the repository's secrets when they're set (DEC-0160).
- Smart Closet is being built (DEC-0162).

**Last verified test result:** the Linux run on 2026-11-15 (see `MIA_OS_TESTING_AND_QUALITY_AUDIT.md`).

**Waiting on Zac:**
- Q-30 (DEC-0178: JSON manifests in apps/<id>/, code moved app by app later);
- add the two signing secrets (steps in the hub);
- Q-08 and Q-09 in `MIA_OS_OPEN_QUESTIONS.md`.
