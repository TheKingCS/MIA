# MIA OS: the independent technical review (Prompt 17 §6)

*Version 1.0, 2026-11-18. The review was performed by **Codex** (OpenAI's coding agent, `codex-cli` 0.166.0, signed in
with ChatGPT), which did not write any of the plan. Claude (Opus) wrote Prompts 01 to 16 and this response.*

## 1. How it was done

| Step | What happened |
|---|---|
| Package | A clean copy of the repository at commit 683defa0 plus Zac's answers (the content of 5461798a). It held only tracked files: none of his data, no `audit/` folder, no local config |
| Access | Codex ran read-only (`codex exec -s read-only`, Windows sandbox "unelevated") with the **actual** documents and code, not a summary. The brief (kept with Prompt 17's work) pointed it at the master plan, the decision records, the matrix, the MVP, each prompt's main document, and `core/`, `server/`, `web/`, `os/`, `deploy/`, `.github/workflows/` and `tests/`. It told Codex to check claims against the code, to look for every item in Prompt 17 §6's list, and that it may disagree with anything |
| First attempt | Failed: the plain read-only sandbox blocked every command on Windows, and Codex said it could not review rather than inventing findings. The second run used the unelevated sandbox, which allowed reads only |
| Findings | 8 findings (6 High, 2 Medium), quoted in full in §4 |
| Response | Each finding accepted, partly accepted or rejected, with reasons (§2). Corrections were made in this commit |
| Final verification | Codex re-read the corrected documents and the code and reported per finding (§5); its new points were accepted and applied |

**Limits.** One reviewer, one pass, and a second pass on the corrections only. Codex checked the GPU claim against
AMD's documentation itself. It did not run the image or the suite. It wasn't told about the VM run, which only shows in
GitHub's run history, and it judged "a working bootc image" from the build and lint alone. That's partly my documents'
fault: they said the boot test hadn't run (C-09). ChatGPT's own planning review, which the supplemental directive
proposes, has not been done.

## 2. Responses to each finding

| Finding | Severity | Response | What changed |
|---|---|---|---|
| F-01 the source of truth is unclear | High | **Accepted** | DEC-0275: a document hierarchy (`MIA_OS_ARCHITECTURE_DOCUMENT_INDEX.md`). `docs/DECISIONS.md` governs status. The master plan, the decision index and `docs/mia_os/README.md` are corrected. Prompts 17b and 18 to 26 are classified |
| F-02 the session is boot-critical and unresolved; the runtime isn't enabled | High | **Accepted** | DEC-0278: Plasma Login Manager entries, the runtime enabled at first sign-in, a recovery page after 30 s, the Plasma fallback. FW-03 proves it in the VM before the image counts as MVP-capable, including ordinary windows and keyboard use. Accessibility (Orca) is proven in FW-11 |
| F-03 the MVP is too broad to audit; Exists isn't verified on the image | High | **Accepted** | DEC-0276: 67 of 97 open Must · MVP requirements stay at the MVP gate, and each has a work package. Three evidence levels: in code, on Linux, on the image. The suite runs inside the image (FW-02) |
| F-04 the build isn't reproducible; the PoC workflow isn't a release pipeline | High | **Accepted** | DEC-0279 and FW-01: digest-pinned base, hash-locked Python, two-build comparison. FW-08 is the real signed release pipeline; the PoC workflow is described as a PoC |
| F-05 migration and recovery with one slot | High | **Accepted, and extended** | REQ-IMP-009 adds content hashes. FW-07 rehearses the move on synthetic data in the VM. HW-02 tests Windows from the enclosure before anything is installed. If Windows won't boot from USB (Windows often refuses), the fallback is putting the drive back in the slot, about ten minutes (Q-107). The move is a gated procedure, not a one-day estimate |
| F-06 security controls described ahead of implementation | High | **Accepted** | Every control is listed with its real state (`MIA_OS_FINAL_SECURITY_AND_RELIABILITY_REVIEW.md` §1). The move is gated on FW-05 (encryption, TPM, recovery key) and FW-06 (the helper) |
| F-07 Fedora's GPU support is local, not AMD's | Medium | **Accepted** | Wording corrected (C-16). Fedora is conditional on PoC 1, which now records model, quantization, backend, tokens a second, memory and a one-hour stability run. The Ubuntu fallback is to be compared on update and rollback design if PoC 1 fails |
| F-08 lost-device revocation overstated | Medium | **Accepted** | Revocation is immediate on the hub and refuses the key at once. Erase is best effort on reconnect. Scoped keys with a lifetime; the phone's stores sealed by its Keystore (WP-10) |

**Codex's "likely disagreements", answered:**

| Codex expected the author to say | Response |
|---|---|
| "Most of MIA already exists and runs on Linux" | **Partly kept.** The engine, the runtime as a user service, and an install, boot, update and rollback in a VM have run on Linux (VM run 43872077107, CI's Linux suite). Codex is right that the session, GPU, encryption, migration and recovery haven't been proven together; the roadmap now says so |
| "The MVP is only packaging, sessions, updates and data" | **Withdrawn.** Those are the high-risk integration tasks, and the roadmap now treats them as the critical path (Prompt 16's headline overstated it) |
| "Fedora packages the stack we need" | **Corrected:** Fedora packages it; AMD doesn't support Fedora. PoC 1 decides |
| "A bootc image proves the foundation" | **Agreed with Codex.** Build and lint, plus a headless boot, update and rollback, are not the foundation. FW-01 to FW-06 are |

## 3. Unresolved disagreements

| Topic | Codex | Author | Status |
|---|---|---|---|
| Readiness | "Not ready to begin implementation of the MVP as described" | Agreed for the MVP. Disagree only that this blocks **all** implementation: the foundation packages (FW-01 to FW-12) are themselves the bounded spikes and cleanup Codex says are ready | Recorded; Zac decides (Q-109) |
| One-day migration | Treat as a gated procedure | Agreed. The effort estimate now says "at least two sessions with Zac, after FW-07's rehearsal passes" | Resolved |

## 4. Codex's report, verbatim

*Paths shortened from the review copy's absolute paths to repository-relative ones; nothing else changed.*

### Findings

#### F-01 — High — Architecture governance and source of truth

**Documents:** [MIA_OS_MASTER_PLAN.md](MIA_OS_MASTER_PLAN.md:6), [MIA_OS_STATUS.md](MIA_OS_STATUS.md:3), [MIA_OS_DECISIONS.md](MIA_OS_DECISIONS.md:1), [MIA_OS_IMPLEMENTATION_MASTER_ROADMAP.md](MIA_OS_IMPLEMENTATION_MASTER_ROADMAP.md:35).

The documents disagree about what is authoritative and approved. The master plan calls itself “Version 0.3” and says “no MIA OS decision is approved,” but it also records numerous later approvals. The status is dated November 17 even though it describes work through November 18. Decision entries in the architecture documents still say `PROPOSED` after the status and open-question register say Zac approved them. The stated inventory is also stale: the master plan says the prompt library has 19 files and lists Prompts through 24, while the directory contains prompts through 26.

This makes it unclear which requirements, decisions, and scope an implementer should follow. It also obscures that Prompt 02 is still awaiting review, Prompt 17 is not yet a completed consolidation, and later prompts have expanded the scope.

**Do instead:** publish one dated baseline with a generated document inventory; reconcile approval state against `docs/DECISIONS.md`; identify the binding versions of requirements and roadmap; mark superseded material and explicitly classify Prompts 17b and 18–26 as in-scope, deferred, or out-of-scope.

---

#### F-02 — High — Linux session and boot dependencies

**Documents:** [MIA_OS_MVP_DEFINITION.md](MIA_OS_MVP_DEFINITION.md:26), [MIA_OS_LINUX_FOUNDATION.md](MIA_OS_LINUX_FOUNDATION.md:76), [MIA_OS_CORE_ARCHITECTURE.md](MIA_OS_CORE_ARCHITECTURE.md:192), [os/files/mia-runtime.service](../../os/files/mia-runtime.service:5).

The MVP requires MIA’s session “by default,” but the image’s runtime unit says it is **not enabled by default** and must be enabled by the user. The plan also treats the session compositor as unresolved: the core architecture discusses a cage kiosk session versus KDE’s compositor, while the roadmap schedules the session proof for later. Yet the MVP depends on this session, normal windows, accessibility, portals, and a Plasma fallback working together.

This is a boot-critical integration dependency, not a minor shell detail. The image can build while the advertised default experience remains unavailable.

**Do instead:** choose and implement the session model before calling the image MVP-capable. Specify the login manager session entry, how the runtime is started and ordered, how the browser shell launches, and how users reach Plasma if any MIA component fails. Make VM acceptance prove those paths, including accessibility and ordinary app windows.

---

#### F-03 — High — MVP scope and requirements traceability

**Documents:** [MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md](MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md:5), [MIA_OS_MVP_DEFINITION.md](MIA_OS_MVP_DEFINITION.md:58), [MIA_OS_IMPLEMENTATION_WORK_PACKAGES.md](MIA_OS_IMPLEMENTATION_WORK_PACKAGES.md:6).

The matrix claims 484 requirements, 262 MVP-tier, with 105 marked “New.” The roadmap has a small set of work packages, and completion requires every Must MVP requirement to pass. Those figures do not establish a credible mapping from each Must requirement to an owner, dependency, implementation task, and executable acceptance test. Some matrix rows use broad verification labels such as `T` or `D`, and “Exists” can describe a plan or a test rather than a feature verified on the target OS.

The practical effect is an MVP that is both broad and difficult to audit. “Every capability by screen and voice,” phone and glasses working “exactly as against Windows,” migration of every store, encryption, recovery, and a week of primary use are all bundled into one gate without a corresponding detailed acceptance plan for each.

**Do instead:** reduce MVP to a narrow, demonstrable desktop path. For every Must requirement, link a concrete work package and a repeatable test or named manual acceptance procedure; distinguish “exists in code,” “verified on Linux,” and “verified on the MIA OS image.” Resolve missing mappings before treating the matrix as a release gate.

---

#### F-04 — High — Build and release reproducibility

**Code and documents:** [os/Containerfile](../../os/Containerfile:24), [mia-os-poc.yml](../../.github/workflows/mia-os-poc.yml:1), [MIA_OS_IMPLEMENTATION_WORK_PACKAGES.md](MIA_OS_IMPLEMENTATION_WORK_PACKAGES.md:18), [MIA_OS_IMPLEMENTATION_MASTER_ROADMAP.md](MIA_OS_IMPLEMENTATION_MASTER_ROADMAP.md:9).

The roadmap describes a locked Python environment, signed releases, SBOMs, and a release process. The actual image build upgrades pip and installs from `requirements.txt`; it does not consume a hash-locked dependency file. The OS base is tagged `kinoite:45`, and packages are installed by name without a recorded repository snapshot or version lock. The visible image workflow is a manually dispatchable proof-of-concept build, not the described signed release pipeline. The image itself says it is a PoC, not a release.

As written, a rebuild may resolve different Python and OS packages while still passing the image lint. That conflicts with the plan’s reproducibility and supply-chain claims.

**Do instead:** define a real release build using pinned base-image digests, locked and hashed Python dependencies, controlled package repositories, pinned CI actions, and artifact signing/provenance. Require the released image to pass boot, update, rollback, and security checks; do not describe the PoC workflow as release infrastructure.

---

#### F-05 — High — Migration and recovery risk with one M.2 slot

**Documents:** [MIA_OS_MASTER_PLAN.md](MIA_OS_MASTER_PLAN.md:94), [MIA_OS_EXISTING_SYSTEM_MIGRATION_STRATEGY.md](MIA_OS_EXISTING_SYSTEM_MIGRATION_STRATEGY.md:1), [MIA_OS_IMPLEMENTATION_OPEN_QUESTIONS.md](MIA_OS_IMPLEMENTATION_OPEN_QUESTIONS.md:102).

The master plan still describes dual boot on a separate drive. The later migration plan correctly changes that to replacing the single M.2 drive and keeping Windows in a USB enclosure, but the older dual-boot assumption persists in other planning text, including the MVP completion conditions. The roadmap also treats the migration as a one-day task after a fresh backup and store-count comparison.

A USB enclosure is not equivalent to a tested bootable internal fallback, and matching record counts does not verify file contents, encryption, settings, permissions, or application behavior. The move also depends on a recovery key and a new disk-encryption setup that are not yet implemented in the image.

**Do instead:** make the replacement-drive plan authoritative everywhere. Before the move, rehearse a full backup and restore to a spare target, verify every store and a representative set of files, test the recovery key, and document how Windows is booted from the enclosure or restored internally. Keep migration as a gated procedure, not a one-day estimate.

---

#### F-06 — High — Security controls are specified ahead of their implementation

**Documents and code:** [MIA_OS_SECURITY_ARCHITECTURE.md](MIA_OS_SECURITY_ARCHITECTURE.md:1), [MIA_OS_MVP_DEFINITION.md](MIA_OS_MVP_DEFINITION.md:34), [os/files/mia-runtime.service](../../os/files/mia-runtime.service:12), [MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md](MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md:89).

The security architecture describes drive encryption, TPM-bound keys, signed images, a restricted privileged helper, OS-owned confirmation dialogs, and an append-only audit trail. The matrix still marks core encryption and helper requirements planned. The image’s runtime unit explicitly has no unlock credential and says files remain plain until one is created. The current unit’s `NoNewPrivileges` and `PrivateTmp` settings do not implement the broader sandboxing and helper boundary described in the architecture.

The documents sometimes present intended controls as if they are already properties of the system. That is especially consequential for the MVP’s claims about encrypted migration and safe system operations.

**Do instead:** treat each control as absent until code and end-to-end tests demonstrate it on the target image. Gate migration on tested LUKS/TPM recovery and helper authorization. Keep the security document’s “built” and “planned” inventories synchronized with the image and matrix.

---

#### F-07 — Medium — Linux GPU support is overstated as a Fedora advantage

**Documents:** [MIA_OS_LINUX_FOUNDATION.md](MIA_OS_LINUX_FOUNDATION.md:23), [MIA_OS_CORE_ARCHITECTURE.md](MIA_OS_CORE_ARCHITECTURE.md:271), [os/Containerfile](../../os/Containerfile:27).

The plan calls Fedora’s repository GPU stack a key reason Fedora is the preferred base, but also notes AMD’s support matrix names Ubuntu and enterprise distributions rather than Fedora. Current AMD documentation lists RX 7900 XTX support for specified Ubuntu and RHEL releases; Fedora is not among those supported distributions in the cited matrix. A Fedora-built package may work, but that is a local validation result, not vendor-supported compatibility. The plan itself says the decisive GPU test remains undone.

[AMD’s ROCm 7.2 system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/docs-7.2.0/reference/system-requirements.html) list supported distributions and GPU configurations. **Inference:** Fedora may still work through its packages, but the architecture cannot claim that support from AMD’s matrix.

**Do instead:** make the Fedora choice conditional on the real GPU proof, recording model, quantization, driver/backend, tokens per second, memory use, and stability. If Fedora fails, compare the documented Ubuntu fallback’s image-update and rollback design before committing to a substitute.

---

#### F-08 — Medium — Device revocation promises exceed offline reality

**Documents:** [MIA_OS_DISTRIBUTED_DEVICE_SECURITY.md](MIA_OS_DISTRIBUTED_DEVICE_SECURITY.md:1), [MIA_OS_DISTRIBUTED_ARCHITECTURE.md](MIA_OS_DISTRIBUTED_ARCHITECTURE.md:1), [MIA_OS_OPEN_QUESTIONS.md](MIA_OS_OPEN_QUESTIONS.md:1).

The design says a lost phone can be unlinked “from anywhere” and “erases itself on reconnecting.” Those are materially different guarantees. A compromised or stolen device that stays offline cannot receive revocation or remote-wipe instructions; meanwhile, its locally stored data and credentials may remain usable.

**Do instead:** define the offline compromise case explicitly. Use revocable, scoped credentials with bounded lifetime where practical, minimize sensitive local data, encrypt device storage with a device-bound key, and describe remote erase as best-effort upon reconnect—not immediate revocation.

---

### What seems sound

- Reusing the Linux kernel, systemd, KDE, and the existing MIA engine is a sensible direction.
- Keeping conventional desktop access and recovery independent of MIA is the right architectural principle.
- The PoC-first approach is appropriate for GPU support, bootc image behavior, the session, and privilege boundaries.
- The one-M.2 migration adjustment is safer than attempting an unsupported dual-boot assumption, once all documents and recovery procedures reflect it.
- Keeping intelligence, authorization, and deterministic action execution separate is a useful security boundary.

### Likely disagreements from the author

- **“Most of MIA already exists and runs on Linux.”** The engine’s Linux test run and a service-start PoC do not establish that the complete proposed desktop, session, GPU stack, migration, recovery, and security controls work together on the image.
- **“The MVP is only packaging, sessions, updates, and moving data.”** Those are high-risk integration tasks; the current plan includes broad desktop, model, voice, phone, glasses, encryption, and recovery requirements.
- **“Fedora packages the stack we need.”** That does not establish AMD-supported Fedora compatibility; the local PoC must decide this.
- **“A working bootc image proves the OS foundation.”** Build and lint are useful, but not proof of the default session, encrypted boot, recovery, update rollback, ordinary desktop use, or a safe migration.

### Overall readiness

**Not ready to begin implementation of the MVP as described.** It is ready for bounded technical spikes and foundational cleanup, but the architecture is not yet a coherent, testable implementation baseline.

The smallest blockers are:

1. Reconcile the authoritative documents, approval states, and current scope.
2. Prove the image boots into a usable MIA session and reliably falls back to Plasma.
3. Prove GPU/model performance on the actual hardware before locking the Linux base.
4. Implement and test disk encryption, recovery, system-action authorization, and reproducible release builds.
5. Rehearse the single-drive migration and Windows fallback, then replace the dual-boot language.
6. Map every Must MVP requirement to a work package and verifiable acceptance criterion.

## 5. Final verification of the critical corrections

Codex re-read the corrected documents, the notes on older ones, the decision records and the code (read-only, the
same sandbox), and reported per finding. Its verdict: **F-07 and F-08 resolved; F-01, F-02, F-03, F-05 and F-06
partly resolved; F-04 not resolved.** In each partly resolved case, the plan is corrected but the code isn't built
yet. F-04 stays open until FW-01 is built. Codex agreed with the readiness verdict: **ready to begin the foundation
work (FW-01) after Zac's approval, not ready for the install.**

**What Codex found new, and what was changed in response (in this commit):**

| Codex's point | Response |
|---|---|
| The blueprint calls itself governing while DEC-0275 is proposed | **Accepted.** The blueprint and the index now say they are the recommended baseline and bind once Zac approves DEC-0275; until then an approved decision always wins. Designs resting on DEC-0275 to 0279 are marked recommended |
| The requirement counts read inconsistently | **Accepted.** The 97 are the earlier open Must · MVP requirements; Prompt 17's own seven are counted separately (traceability §1, §5) |
| FW-01's two-build check would miss differences outside package lists | **Accepted.** It compares a manifest of the image's files too, and lists any difference |
| FW-03's GUI acceptance is thin and its estimate optimistic | **Accepted.** Keyboard-driven checks through QEMU, window behaviour, both sessions; the estimate is marked provisional and re-estimated after its first session |
| FW-04's test doesn't cover the automatic path, and its greenboot checks depend on the network | **Accepted.** The VM test now runs the night timer, idle check, snapshot and automatic rollback end to end. Required checks are local only (the login manager, `/var/home`, free disk); the network and the model server are advisory |
| FW-05 needs a VM setup the workflow doesn't have | **Accepted.** Building it (Secure Boot firmware and a software TPM) is now step 0 of FW-05, and the estimate rises |
| FW-07's estimate is optimistic | **Accepted.** Split into FW-07a (inventory, manifest) and FW-07b (restore, rehearsal), re-estimated after 07a. The total before the first install rises to about 30 to 35 sessions |
| F-04, F-02, F-06 are unresolved in code | **Agreed.** They are FW-01, FW-03 and FW-04 to FW-06. No document now claims otherwise |

**Codex's verification report, verbatim** (paths as Codex gave them, relative to the repository):

#### F-01 to F-08

- **F-01 — Partly resolved.** The new index sets a hierarchy and says decision status changes belong in `docs/DECISIONS.md` ([document index](docs/mia_os/MIA_OS_ARCHITECTURE_DOCUMENT_INDEX.md), §1). But the blueprint calls itself governing while DEC-0275, the decision establishing that hierarchy, is still **PROPOSED** ([DECISIONS.md](docs/DECISIONS.md), DEC-0275). The hierarchy is documented, but its authority has not been approved under its own rule. **Remaining:** Zac must approve DEC-0275 or the blueprint must avoid presenting the hierarchy as settled.

- **F-02 — Partly resolved.** DEC-0278 and FW-03 specify two login sessions, first-sign-in runtime enablement, a recovery page, and a Plasma fallback ([roadmap](docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md), §FW-03). The actual unit still says “Not enabled by default,” and the image still installs `cage` without a MIA session entry or launcher ([unit](os/files/mia-runtime.service); [Containerfile](os/Containerfile)). The VM workflow is headless, not a session test ([workflow](.github/workflows/mia-os-vm.yml)). **Remaining:** implement and demonstrate the login/session paths on the image.

- **F-03 — Partly resolved.** The final traceability document narrows the 97 open Must MVP requirements to 67 at MVP, 26 at Alpha, and 4 at Beta, assigns packages, and distinguishes code/Linux/image evidence ([traceability](docs/mia_os/MIA_OS_FINAL_REQUIREMENTS_TRACEABILITY.md), §§1–2). But the blueprint says there are 97 **earlier** open Must requirements plus Prompt 17’s additions, while the traceability intro calls 97 the full set; the stated totals and gates need reconciliation. “Exists” is still based on Windows or CI, with image verification deferred. **Remaining:** reconcile the requirement counts and make each listed acceptance executable on the target image.

- **F-04 — Not resolved.** FW-01 specifies digest pinning, hash-locked Python dependencies, and comparing two builds, but the current [Containerfile](os/Containerfile) uses the mutable `kinoite:45` tag, upgrades pip, and installs from `requirements.txt`. The config still selects `llama3.2` ([default_config.json](config/default_config.json)), and the PoC workflow is still manually dispatchable or triggered only by selected paths ([mia-os-poc.yml](.github/workflows/mia-os-poc.yml)). **Remaining:** implement the lock, pinned base, correct model default, and automated build checks before claiming reproducible builds.

- **F-05 — Partly resolved.** The index marks the older dual-boot passages superseded, and the final roadmap makes the move a gated procedure with an untouched Windows drive ([roadmap](docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md), FW-07 and MV-01). But migration tooling and the rehearsal are future work, and the README’s GPU procedure still describes the Windows disk as accessible in place. **Remaining:** complete the synthetic restore rehearsal, verify actual contents, and validate the enclosure fallback before moving the owner’s data.

- **F-06 — Partly resolved.** The readiness assessment admits OS-level security controls are not implemented and gates migration on FW-05/FW-06 ([readiness assessment](docs/mia_os/MIA_OS_IMPLEMENTATION_READINESS_ASSESSMENT.md), §1). The image unit still has only `NoNewPrivileges` and `PrivateTmp`, with plain files until credentials exist ([unit](os/files/mia-runtime.service)). **Remaining:** implement and test encryption, recovery, helper authorization, and the promised runtime sandbox before the MVP gate.

- **F-07 — Resolved as a planning correction.** The older Linux Foundation note now says ROCm comes from Fedora packaging, not AMD’s support matrix; the blueprint makes Fedora conditional on the GPU proof ([Linux Foundation](docs/mia_os/MIA_OS_LINUX_FOUNDATION.md), opening note; [roadmap](docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md), HW-01). **Remaining:** run the hardware test and record the specified measurements; Fedora compatibility is still unproven.

- **F-08 — Resolved in the design.** The device security note now says a lost key is refused on the hub immediately, while erase occurs only on reconnect and is best effort ([distributed device security](docs/mia_os/MIA_OS_DISTRIBUTED_DEVICE_SECURITY.md), opening note). **Remaining:** implement and verify scoped keys, device-bound storage protection, and the reconnect erase behavior.

#### New or remaining high issues

- **FW-01’s acceptance is not currently achievable as written.** Its two-build comparison is not implemented; the build still uses mutable inputs and the wrong default model. Comparing `rpm -qa` and `pip freeze` alone would also miss differences in image contents outside those package lists. **Fix:** implement the pins and lock first, then compare a defined image manifest or digest as well as package inventories.
- **FW-03 is a large, unproven desktop integration squeezed into two to four sessions.** It requires a custom KWin session, ordinary windows, shell restart, timed recovery UI, Plasma Login Manager defaults, and a usable Plasma fallback. The current image has no session entry and the VM workflow provides no graphical desktop. The roadmap’s screenshot-size/known-element check does not establish keyboard access, window behavior, or accessibility. **Fix:** treat the estimate as provisional and define repeatable GUI acceptance, including keyboard use and fallback.
- **FW-04’s rollback test does not cover the specified update design.** Its current VM workflow tests manual `bootc switch` and `bootc rollback`, not a night timer, idle check, pre-update `/var/home` snapshot, or automatic rollback after failed health checks. The proposed greenboot checks also include network/model availability, which can make boot success depend on services external to the base OS. **Fix:** test the automatic path and define which checks are required versus advisory.
- **FW-05 is gated on a VM setup the current workflow does not provide.** The roadmap requires OVMF Secure Boot and `swtpm`, then a TPM/PIN-encrypted install; the current VM workflow uses ordinary OVMF and installs without encrypted storage. **Fix:** add and run that VM path before accepting the package.
- **FW-07’s two-session estimate is optimistic.** It spans store discovery, canonical content hashes, representative file selection, restore, phone sync-base reset, Windows-only app inventory, and a full rehearsal. **Fix:** split and estimate after the store/file inventory is concrete.

The decisions DEC-0276–0279 are still marked **PROPOSED** in `docs/DECISIONS.md`, despite the blueprint describing several underlying choices as fixed. That status mismatch should be resolved before implementers treat those choices as binding.

**I agree the plan is ready to begin foundation work (FW-01) after Q-109 approval, but it is not ready for installation on the owner’s PC.**
