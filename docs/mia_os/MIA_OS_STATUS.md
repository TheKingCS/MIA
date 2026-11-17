# MIA OS status

*Updated 2026-11-17 by Claude (Opus).*

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
- Prompt 04 reviewed by Zac (DEC-0179 to DEC-0182 approved) and by Fable.
- **Prompt 23's architectural review is done** (Fable, 2026-11-16): `MIA_OS_UNIVERSAL_INTELLIGENCE_REVIEW.md`,
  DEC-0188 proposed; Opus's independent review is next.
- **Prompt 05 (the core operating system architecture) is done** (Fable, 2026-11-16):
  `MIA_OS_CORE_ARCHITECTURE.md` and fourteen supporting documents; DEC-0189 to DEC-0195 proposed; six proofs of
  concept described, none run. Nothing was installed, built or migrated.
- Prompt 05 reviewed by Zac (Q-47 to Q-51 answered); PoC 2, 4 and 6 passed, PoC 1 waits on a USB stick.
- **Prompt 06 (hardware and platform) is done** (Opus, 2026-11-17): `MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md` and
  twenty supporting documents; the PC's hardware read from the machine; DEC-0201 to 0205 proposed; REQ-HW-007 to
  031 added.
- Prompt 06 reviewed by Zac (Q-63 to Q-67 answered; DEC-0202 approved).
- **Prompt 07 (intelligence infrastructure) is done** (Opus, 2026-11-17): `MIA_OS_INTELLIGENCE_ARCHITECTURE.md` and
  twenty supporting documents; DEC-0206 to 0212 proposed; REQ-INT-001 to 036 added.
- Prompt 07 reviewed by Zac (Q-68 to Q-72 yes; DEC-0206 to 0212 approved; knowing who's talking not planned).
- **Prompt 08 (autonomy, agents and execution) is done** (Opus, 2026-11-17): `MIA_OS_AUTONOMY_ARCHITECTURE.md` and
  twenty-three supporting documents; DEC-0213 to 0219 proposed; REQ-AGT-001 to 034 added.
- Prompt 08 reviewed by Zac (DEC-0215 amended: Approve Once or Approve From Now On on every card; DEC-0217 approved;
  no quiet hours).
- **Next:** Prompt 09 on his go; build Approve From Now On on the cards.
- Prompts 18–20 (World Intelligence, Procurement, the Living System) are approved and being built; Prompt 21 waits for 17.

**Changes outside the planning documents, on Zac's say-so:**
- The Companion app was retired (DEC-0160).
- The phone app's signing key now comes from the repository's secrets when they're set (DEC-0160).
- Smart Closet is being built (DEC-0162).

**Last verified test result:** the Linux run on 2026-11-15 (see `MIA_OS_TESTING_AND_QUALITY_AUDIT.md`).

**Waiting on Zac:**
- Q-47 to Q-51 (Prompt 05's review), above all Q-49: the proofs of concept, one of which needs him at the PC
  with a USB stick; then the go for Prompt 06;
- Q-43 to Q-46 (prompt 23's review);
- add the two signing secrets (steps in the hub);
- Q-08 and Q-09 in `MIA_OS_OPEN_QUESTIONS.md`.
