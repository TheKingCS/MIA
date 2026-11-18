# MIA OS: desktop open questions and risks (Prompt 10)

> **Prompt 17 (2026-11-18):** the answers to this document's questions are in `MIA_OS_OPEN_QUESTIONS.md`, which governs; the decisions' statuses are in `docs/DECISIONS.md`.

*Claude (Opus), 2026-11-17. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

**Answered 2026-11-17.** Q-79, Q-80 and Q-81 yes. With Q-80: "MIA should be adaptable and understanding of available monitors so if I turn one off she flows with just 1" (REQ-DSK-033). Q-82 no: "the display is important and is for me and my wife to use"; the household display is planned for real (`MIA_OS_SHARED_HOUSEHOLD_DESKTOP_EXPERIENCE.md`).

| Q | Question | Recommended |
|---|---|---|
| **Q-79** | In MIA's session, should ordinary windows (Firefox, Krita, a terminal) be switched from a strip at the bottom of MIA's own screen, instead of KDE's usual taskbar? KDE's taskbar stays in the Plasma session. | Yes, her own strip |
| **Q-80** | Should your second monitor (the 1080p one) show MIA's ambient view all the time: the clock, your day, what's due, music and what she's working on? | Yes |
| **Q-81** | On the PC, talking to MIA starts with a press (the orb or a key held) for now, and a wake word ("MIA") is measured later for false triggers before it's offered. OK? | Yes |
| **Q-82** | A household display (the kitchen idea: calendar, kitchen, music, photos, no personal data) is planned on paper only, since MIA is for you alone. Keep it that way? | Yes, plan only |

## 2. Risks

| ID | Risk | Response |
|---|---|---|
| R-57 | KWin as a session for a single shell isn't a supported KDE path and breaks on an update | PoC 3; cage as the MVP fallback; pinned Fedora release |
| R-58 | The shell's web window uses memory the models need | measured idle limit (REQ-DSK-027); models unloaded before the shell |
| R-59 | Wayland's isolation leaves context sharing clumsy (a portal pick every time) | the chips; remembered picks only where the portal allows |
| R-60 | Modes, workspaces and dashboards add up to clutter | ranked Home; workspaces only on his yes; one navigation model |

## 3. Before Prompt 11

Prompt 11 styles this: the shell's regions, cards, panels, the approval card and the three modes, within the token
rules (DEC-0184). Q-79 and Q-80 change what it styles.
