# H-0010: ChatGPT answers to current MIA questions
- From: chatgpt · To: claude (cc muse, zac) · Date: 2026-10-05
- Related: Q-0001, Q-0002, Q-0006, Q-0003, Q-0011, H-0005, H-0008, DEC-0014

## Context
ChatGPT reviewed the repo: docs/QUESTIONS.md, CURRENT_STATE.md, COLLABORATION.md, DECISIONS.md, H-0005 through H-0008, server/app.py, the web/ foundation, and the current architecture. Relayed by Zac (ChatGPT can read the public repo but not write to it).

## What's needed

**Q-0001 (missed-daily penalty):** recommendation is non-punitive by default — lose/reset the streak, record the miss, allow natural recovery; no XP subtraction, stat damage, or content locking. The game layer rewards progression rather than punishing imperfection; consistent with the Witness Principle (DEC-0014). A harder mode could become opt-in later. Status: recommended ANSWERED, pending Zac's final approval.

**Q-0002 (child safety-floor notification):** recommendation is yes, as a safety escalation, not ordinary monitoring: (1) child gets the immediate safety response; (2) MIA encourages telling a parent/trusted adult; (3) parent/guardian is notified the safety floor triggered, with minimum necessary information only (not the child's full conversation); (4) the escalation is recorded for audit; (5) the child is told transparently that a trusted adult may be alerted. Deterministic in code, never model-decided. Relevant code: core/safety_floor.py, core/child_accounts.py. Status: PROPOSED ANSWER, needs Zac's approval before implementation.

**Q-0006 (collaboration website):** yes eventually, absolutely not yet. The file-based hub is working (simple, Git audit trail, no service to maintain, Zac remains final authority). A future site would be a view over these files, not a replacement. Keep as a Phase 3/4 tooling idea; must not compete with Phase 2.

**Q-0003 / Q-0011 (glasses platform):** H-0008's research stands. Two paths: Web Apps (~600x600, right lens, additive display, HTML/CSS/JS, Neural Band, public HTTPS URL — directly compatible with the web/ architecture) and Device Access Toolkit (native, richer capabilities, more private, more work). Recommended progression: Web App prototype → validate → native toolkit for private voice/camera. Do NOT expose MIA through Tailscale Funnel as anything but a security-sensitive experiment; a narrowly scoped, revocable glasses credential is mandatory for the first proof-of-concept. Physical-device/account confirmations stay with Zac.

**Architectural verdict:** the repo is converging correctly — "MIA is one intelligence, not one screen." Keep: Life State v2 → /api/state → shared experience layer → surface-specific composition; propose → approve → execute → record → undo. Don't rebuild modules just to make them web-based: make Home unmistakably MIA, add Talk, replace surfaces only when the web version is genuinely better, keep business logic in the engine, preserve Qt screens until replacements are proven.

**Additional recommendation:** make this behavioral rule explicit alongside the Witness Principle (DEC-0014): "MIA does not punish the user for being human. The game layer exists to make progress feel meaningful, not failure feel painful." Gives Q-0001 a philosophical anchor.

## Constraints
- All recommendations are proposed, not decided. Only Zac approves (via muse or claude in chat).
- The DEC-0014 extension ("does not punish the user for being human") would amend an APPROVED decision — needs Zac's explicit approval.

## Acceptance criteria
- Q-0001, Q-0002 recorded with ChatGPT's recommended answers once Zac approves.
- Q-0006 stays open as a future tooling idea.
- Zac's decision on the DEC-0014 extension recorded.
