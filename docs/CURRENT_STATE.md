# MIA: Current State

*The two-minute "where are we right now?" for every collaborator
(`docs/COLLABORATION.md`). Claude rewrites it at the end of each
session. Last updated: 2026-10-05 (Phase 2 foundation), by claude.*

## Phase

**Phase 2, "Experience" (DEC-0012, DEC-0013 approved).** The foundation
is built, and the vertical slice runs end to end in a browser and inside
the desktop app: engine → `/api/state` → web Home → an action
(Propose → Approve → Execute → Record → Undo) → live update. **Next:
Muse builds the real Home on it (H-0007); Zac runs the check on his new
computer and phone.** MIA's devices, in order (DEC-0015): the new
computer, the phone, the Meta Display glasses (soon), then Pi devices
(eventually).

## Where things stand

| Area | Status |
|---|---|
| Desktop app (PySide6, 37 apps) | REAL, in daily development |
| Phone web app (Talk, Today, Money) and Android app | REAL |
| Assistant (local model, ~185 tools, voice) | REAL |
| Life events (history), links, Life State v2 (now with assets, kitchen, workout), `/api/state`, schema | REAL / DERIVED, built 2026-10-05 |
| Web front end (`web/`, served at `/web/`; desktop "Home (preview)") | REAL foundation: engine client, tokens, a working Home scaffold. Muse's real Home next |
| Action API (`/api/actions`) and live updates (`/api/live`) | REAL, built 2026-10-05 |
| Muse's desktop design artifact | Design surface, SIMULATED. Superseded by `web/` for real screens |
| Meta Display glasses | PLANNED, priority 3 (DEC-0015). Platform researched (H-0008); waiting on DEC-0016 and Q-0011 |
| Raspberry Pi devices | Supported but parked: priority 4 (DEC-0015) |
| MIA's reasoning over Life State ("opportunities") | PLANNED (Phase 2) |
| Collaboration hub (these files) | REAL, started 2026-10-05 (DEC-0010) |

## Right now

**Zac is phone-only for now.** His PC (where MIA lives) is a Windows PC;
GitHub's Windows machines stand in for it (installer and full tests on
every push). Anything that needs the PC waits.

## Who's doing what

- **Zac (phone):** decide DEC-0014 and DEC-0016 (the glasses plan, H-0008),
  answer Q-0011 (phone type, glasses, is MIA running on the PC). When
  back at the PC: the checks in `docs/NEXT_SESSION.md` and paste the result into the hub. Enter real
  data through MIA. Decide DEC-0014 (Muse's Witness Principle). Open: Q-0001, Q-0002, Q-0003 (Muse listed what the glasses
  answer needs), Q-0005.
- **Muse:** H-0007, the real Home and presence in `web/` (guide:
  `web/README.md`), under DEC-0014; then the glasses composition (H-0008:
  600×600, additive display, Neural Band).
- **ChatGPT:** review H-0008's Option A (public exposure via Funnel)
  against MIA's local-first principle. Also: review H-0007's milestone against the vision when Muse's
  Home lands; think ahead on Phase 2 reasoning (MIA proposing missions).
- **Claude:** support Muse's Home (any missing Life State fields or
  action kinds, via `QUESTIONS.md`). Next engine work: Talk in the web
  front end (voice and chat endpoints for `web/`), then MIA's own
  proposals (`proposed_by: "mia"`, through the communication gate).

## Blocked

- Broad migration of screens: on the check on the new computer and the
  phone (DEC-0013, DEC-0015).
- The glasses client: on Q-0003 (platform and access).

## Recent changes (newest first)

- 2026-10-06 · claude · **Apps page on the web** (Zac: "so many modules and tools… kind of inaccessible"). `web/apps.html` + `/api/apps` (`core/web_surfaces.apps_page`): all 34 apps by life area, each with its own description, whether it's on the web yet, an example of what to say, and the Assistant tools that work in it (201 in the desktop app, in plain words); open it or "Ask MIA" (Talk, pre-filled), find, and show/hide per person through a new action kind `app.visibility` (confirm + undo). Tests keep the catalog in step with `modules/` and every tool domain.
- 2026-10-06 · claude · **DEC-0017 approved by Zac; first slice built.** `docs/WEB_PARITY.md` (59 screens to reach). The shared web frame (`web/shell.js`, `shell.css`): each person's own sidebar with level and XP, MIA's Talk panel on every page, and propose → confirm → approve → undo for every screen; Muse's seven module pages now use it. Home is the concept's dashboard (`index.html`, `dashboard.js`, engine `core/web_surfaces.py`, `/api/shell`, `/api/home`); Muse's orb Home moved to `presence.html`. Found and fixed two engine bugs while driving it: undo didn't take back XP (the config wasn't reloaded, worst on the phone/web view), and undone changes still showed as recent wins. H-0017 to Muse. Next: Money, full API and screen.
- 2026-10-06 · claude · Zac: the web front end is far behind the working MIA. Claude's diagnosis: the contract given to `web/` (one summary, five actions) was too narrow. Proposed DEC-0017 (H-0016): parity with every Qt screen, a full engine API per module, Claude builds working screens, Muse owns the shell and the concept look, Home becomes the concept dashboard. Waiting on Zac, reviews from Muse and ChatGPT.
- 2026-10-05 · claude · Zac approved DEC-0016 and the GitHub Pages preview; answered Q-0011 (Android, no glasses yet, MIA not on the PC yet); parked Q-0012. Pages workflow added (`.github/workflows/pages.yml`, placeholder data only: `mia.js` forces the demo on github.io); waits on Zac switching Pages on. H-0014 to Muse. Next for Claude: H-0013 (mission detail, skill XP, character level).
- 2026-10-05 · claude · Windows CI's last real failure fixed: Windows' PDF reader runs a chapter heading into its first sentence ("Chapter 3: Grounding The grounding conductor..."), so textbooks lost that chapter. `find_chapters` now keeps the heading part (real PDFs do this too). Temporary probe removed. **Windows is fully green:** the installer, the full test suite and the web device check all pass.
- 2026-10-05 · muse · **Built MIA's Home in `web/`** (presence orb, focus card, confirm, briefing, Talk on the same screen). Claude verified it against the real engine in a browser on desktop and phone sizes: an action proposed, confirmed, executed and live-updated, no page errors. Claude added `MIA.talk()` to the engine client (Muse's TODO).
- 2026-10-05 · muse · H-0012: design review of DEC-0016 (endorses A-then-B with ChatGPT's security posture; additive-display rules; two-gesture approve; a visible connection state). Claude replied: no conflicts; proposes a GitHub Pages mock prototype for the glasses (placeholder data only, nothing private exposed), waiting on Zac.
- 2026-10-05 · claude · Built Q-0002: a child's safety-floor trigger alerts their guardians directly (who and when only, never the words), tells the child plainly, and is recorded for audit in their own histories, never the household's (`core/safety_escalation.py`). Built Q-0001: a missed daily is recorded gently ("no points lost"). Q-0012 asks about cases where the guardian isn't safe. Windows CI: 6 failures left (chapter detection on Windows PDFs, being diagnosed; stopping shell scripts, a known issue).
- 2026-10-05 · zac (via muse) · Approved H-0011: Q-0001 (non-punitive), Q-0002 (notify the guardian, minimal), DEC-0014 extended ("MIA does not punish the user for being human").
- 2026-10-05 · claude · Windows CI found and fixed real Windows bugs (date formats that crashed muting and "what did you change?", WSL's bash stub, update paths); the web front end passes its check on Windows (266 ms, 209 MB, 60 fps). Replied on H-0009 (`person.child` already exists) and H-0010.
- 2026-10-05 · chatgpt (via zac) · H-0010: recommended answers to Q-0001 (non-punitive), Q-0002 (notify the guardian, minimal), Q-0006 (later), the glasses (Funnel only as a scoped experiment), and a proposed DEC-0014 extension ("MIA does not punish the user for being human"). All waiting on Zac.
- 2026-10-05 · muse · H-0009: accepted the Home build, with its plan and Life State mapping. DEC-0014 approved by Zac (via muse).
- 2026-10-05 · claude · Windows CI (installer and full test suite on GitHub's Windows machines). H-0008: the Meta Ray-Ban Display platform (Web Apps vs the native toolkit) and a glasses plan, DEC-0016 proposed. Q-0010 closed (a Windows PC), Q-0011 asked.
- 2026-10-05 · claude · Phone sign-in for `web/` (`MIA.signIn()`, the same email and password as the phone app), tested in a phone-sized browser: the same Home works on the phone.
- 2026-10-05 · zac · DEC-0011 done: the repo is public, so ChatGPT can read the hub directly. Q-0005's three small choices (placeholder names in tests, hiding the email, a license) are still open.
- 2026-10-05 · zac · DEC-0015: MIA runs on the new computer first, then the phone, the glasses (soon) and Pi devices (eventually). The Pi is not the main target; the docs are corrected.
- 2026-10-05 · muse · H-0006 review (supports DEC-0012/0013 with conditions), answered Q-0007 and Q-0009, proposed DEC-0014 (the Witness Principle), and the design half of Q-0003 (what the glasses answer must include).
- 2026-10-05 · claude · Phase 2 foundation: the action API, live updates, `web/` with the engine client and a working Home scaffold, desktop "Home (preview)", the Pi check tool. H-0007 to Muse.
- 2026-10-05 · chatgpt (via zac) · Approved DEC-0012/0013 with refinements (Q-0008).
- 2026-10-05 · claude · H-0005: where MIA is and the Phase 2 proposal (DEC-0012, DEC-0013, Q-0007 to Q-0009).
- 2026-10-05 · claude · H-0004 done: `assets`, `kitchen` and `workout` added to Life State v2, the schema and the example.
- 2026-10-05 · muse · First hub round-trip: answered Q-0004 (Home priorities), filed H-0004 (schema gaps).
- 2026-10-05 · claude · Collaboration hub files (this one,
  `COLLABORATION.md`, `DECISIONS.md`, `QUESTIONS.md`, `HANDOFFS/`).
- 2026-10-05 · claude · Handoff H-0003 to Muse; placeholder example
  Life State.
- 2026-10-05 · claude · Engine Phase 1: life events, links, Life State
  v2, `/api/state`, export command, schema (DEC-0005, DEC-0006,
  DEC-0007).
- 2026-10-01 · claude · Starter sets, child accounts, accessibility,
  ownership, private budget, quick capture, Today, accounts and
  households.

## Open decisions and questions

- DEC-0014 (PROPOSED by muse): the Witness Principle.
- DEC-0016 (PROPOSED): the glasses, a Web App first.
- Q-0011: phone type, the glasses, is MIA running on the PC.
- Q-0001, Q-0002, Q-0003, Q-0005, Q-0006: see `docs/QUESTIONS.md`.

## Constraints everyone works within

No real personal data in the repo (DEC-0002). Facts in code, the model
only phrases (DEC-0004). Surfaces consume `/api/state` and mark
anything else PLANNED (DEC-0005, DEC-0007). The guardrail before every
proposal (DEC-0008). Read, propose, approve (DEC-0009). Only Zac
approves decisions.
