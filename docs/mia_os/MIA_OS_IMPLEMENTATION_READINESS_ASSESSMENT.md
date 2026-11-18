# MIA OS: implementation readiness (Prompt 17 §17)

*Claude (Opus), 2026-11-18. Version 1.0. No score: each domain is classified, with its blockers. Codex's view is in
`MIA_OS_FINAL_INDEPENDENT_TECHNICAL_REVIEW.md`; where we differ it's recorded there.*

## 1. By domain

| Domain | Classification | Why | Blockers | Smallest work to clear them |
|---|---|---|---|---|
| Architectural completeness | **Ready with conditions** | every domain has one authoritative design; the conflicts are resolved or recorded | 53 decisions proposed | Q-110 |
| Technical feasibility | **Requires investigation** (two points) | the base and the session rest on unproven facts | the GPU under Fedora; KWin as MIA's session | HW-01; FW-03 |
| Migration readiness | **Not ready** | no tooling, no rehearsal, the enclosure untested | FW-07; HW-02; the drive | FW-07, HW-02 (the drive is Zac's purchase) |
| Technology selection | **Ready with conditions** | checked against primary sources on 2026-11-18; ten corrections made | PoC 1 and PoC 3 can still change the base or the session | as above |
| Security | **Ready with conditions** | MIA's authority boundary is built and tested; the OS-level controls aren't | FW-05, FW-06 before the move; WP-02 to WP-04 before the MVP gate | those packages |
| Reliability | **Ready with conditions** | rollback proven headless | automatic rollback, the graphical fallback, USB recovery | FW-03, FW-04, FW-09 |
| Development infrastructure | **Ready with conditions** | 6,828 tests, CI on Windows, the VM test that passed | the build isn't reproducible; Linux CI only on `os/` changes | FW-01, FW-02 |
| MVP definition | **Ready** if Q-105 is approved | 67 requirements, each with a package and a place it's proven | Q-105 | his answer |
| Implementation sequencing | **Ready** | the critical path and its dependencies are explicit | — | — |
| Requirements traceability | **Ready with conditions** | every open Must · MVP requirement has a release and a package | "Exists" isn't yet verified on the image | FW-02 (the suite inside the image) |
| Independent review | **Done; final check recorded** | Codex reviewed the real documents and code; the corrections were re-checked | ChatGPT's planning review not done | optional |
| Outstanding decisions | **Ready with conditions** | the questions are explicit | Q-105 to Q-110 | his answers |

## 2. The overall answer

**MIA OS is not ready for the MVP to be built on his PC, and is ready for the foundation work to begin.** That is the
smallest honest claim. Codex reached the same view: "ready for bounded technical spikes and foundational cleanup". The
foundation packages FW-01 to FW-12 are exactly that, and all of them run in a VM without touching his PC, his data or
Windows.

The blockers to the **first install**: FW-01 to FW-07, FW-09, FW-10, HW-01, HW-02, the 4 TB drive and the enclosure,
WP-01 to WP-04 and WP-09, and Zac's answers to Q-105 to Q-107.

## 3. The first work package

**FW-01, a reproducible image build** (specified in `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md` §4). Why first:
- every later gate tests the image it produces;
- it needs no hardware and no purchase;
- it fixes the wrong default model a fresh image would start on;
- it is about one session's work;
- it can be undone by reverting a commit.

Zac said go on 2026-11-18 (Q-109), and approved the 53 proposed decisions (Q-110), so the blockers left for the
foundation are none; those for the install are unchanged.
