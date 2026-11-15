# MIA OS master plan

*The authoritative consolidated description of the MIA OS initiative
(Master Directive §13). Claude maintains it; Zac approves.*

*Version 0.2, 2026-11-15, after Prompt 01. Status: planning. Nothing is
built and no MIA OS decision is approved.*

## 1. What we're doing

Zac's prompt library is in [`prompts/`](prompts/), kept verbatim. It has
19 files:
- the Master Directive;
- Prompts 01–17;
- a supplemental directive for 17.

It turns MIA from an application family into a Linux-based, AI-native operating environment. Claude works through it **one prompt at a time and stops for Zac's review after each one**.

Five decisions are established by Zac (Master Directive §3) and are requirements, not options:
1. The foundation is Linux.
2. The experience is MIA-first, with a conventional desktop available.
3. The intelligence is hybrid and local-first.
4. MIA is proactive, and consequential actions need approval.
5. MIA boots by default, with a conventional desktop, a recovery environment, safe mode and a no-AI mode.

## 2. Progress

| Prompt | Subject | Status | Documents |
|---|---|---|---|
| 00 | Master Directive | received | `prompts/00_MASTER_DIRECTIVE.md` |
| first pass | 10-document plan (2026-11-13, before the library) | done; **superseded**, kept in `preliminary/` | `preliminary/*` |
| **01** | **Existing system audit** | **done; waiting for Zac's review** | listed below |
| 02 | Feature ecosystem | not started | |
| 03–17 | (see `prompts/`) | not started | |

## 3. Prompt 01 in brief

The full audit is [MIA_OS_EXISTING_SYSTEM_AUDIT.md](MIA_OS_EXISTING_SYSTEM_AUDIT.md).

**What exists:**
- **Structure.** A modular monolith with satellite apps, of about 300k lines:
  - the engine (`core/`, 521 files);
  - one API server (265 routes);
  - one web front end (102 pages);
  - a Qt classic view;
  - two Android apps;
  - a glasses relay;
  - the self-contained homestead subproject.
- **Tests.** 6,284 tests pass on Linux. 8 fail: 6 are test-isolation or environment problems, and 2 have causes not yet isolated.
- **Already independent of the OS:**
  - the engine (headless and on Android);
  - the action contract with undo;
  - the stores;
  - the web front end;
  - the grounding of facts in code.
- **Not yet independent of the OS:**
  - the runtime (scheduler, server host, store owner), which lives in the PC's Qt process (R-01);
  - encryption at rest, which works only on Windows (R-02).
- **Missing for an OS:**
  - capability grants (R-05);
  - Linux CI (R-07);
  - reproducible builds (R-08);
  - sandboxing (R-04);
  - device identity beyond tokens.
- **Zac's named features:**
  - built: Workout, Memory Vault, finances, businesses, homestead, the Inspect skill, Game Master and the Dungeon;
  - phase 1 only: Living Worlds;
  - not built: Smart Closet, Life Enrichment Protocol, Shared Conversation, the Convergence.
- **Could not be checked here:** the PC, the phone, the glasses, the Pi, the model's answer quality.

## 4. Documents

**Central:**
- this plan;
- [Vision](MIA_OS_VISION.md);
- [Status](MIA_OS_STATUS.md);
- [Decisions](MIA_OS_DECISIONS.md);
- [Open questions](MIA_OS_OPEN_QUESTIONS.md);
- [Risk register](MIA_OS_RISK_REGISTER.md).

The Master Directive also lists REQUIREMENTS, ARCHITECTURE and later central documents. Each is created by its own prompt; none exists yet.

**Prompt 01:**
- [Existing system audit](MIA_OS_EXISTING_SYSTEM_AUDIT.md)
- [Feature inventory](MIA_OS_FEATURE_INVENTORY.md)
- [Technology stack](MIA_OS_TECHNOLOGY_STACK.md)
- [Data architecture](MIA_OS_DATA_ARCHITECTURE_AUDIT.md)
- [Security assessment](MIA_OS_EXISTING_SECURITY_ASSESSMENT.md)
- [Testing and quality](MIA_OS_TESTING_AND_QUALITY_AUDIT.md)
- [Technical debt and risks](MIA_OS_TECHNICAL_DEBT_AND_RISK_REGISTER.md)
- [Dependency and data-flow map](MIA_OS_DEPENDENCY_AND_DATA_FLOW_MAP.md)
- [Migration readiness](MIA_OS_MIGRATION_READINESS.md)

**History:** `preliminary/`, the 2026-11-13 first pass. It is input for Prompts 05, 13, 14 and 16, not authoritative.

## 5. Which document wins

1. This master plan.
2. Approved decisions in `docs/DECISIONS.md`.
3. The prompt's own reports.
4. `preliminary/`.

The code beats every document when they disagree about what exists.
