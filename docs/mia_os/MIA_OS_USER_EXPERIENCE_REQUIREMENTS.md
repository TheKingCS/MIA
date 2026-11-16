# MIA OS: user experience requirements (Prompt 04, deliverable 6, with §4 to §6 and §19)

*Claude (Opus), 2026-11-15. Planning only. Row format: [SYSTEM_REQUIREMENTS](MIA_OS_SYSTEM_REQUIREMENTS.md) §1. These
say what the experience must do; how it looks is Prompt 10 and 11's (and Muse's: the Stark interface, DEC-0023).*

## 1. Two ways in, one system (§4)

Every function is reachable **directly** (a screen, a menu, a file manager, a terminal) and **by intent** (asking MIA
by voice or text). Neither is the only way. Opening the Greenhouse page and reading the sensors, and asking "how's the
greenhouse?", read the same records through the same capabilities (DEC-0125, `core/parity.py`).

**Standardised across MIA OS:** the action contract's approval card and undo; the gate's notifications; the search
box; the status chips; the theme tokens; how outside text is marked. **Customisable:** sidebar apps and favourites,
focus presets, text size and contrast, the voice, answer style, the pace of her messages, which mode a device starts
in.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-UX-001 | Every capability shall be reachable both by a screen control and by asking MIA, or carry a recorded reason it isn't. | Must | MVP | All | Exists (`work/parity.json`) | T: `tests/test_parity.py` | DEC-0125, P1 → 10 |
| REQ-UX-002 | The essential functions (talk to MIA, search, Home, notifications, settings, the conventional desktop, power) shall each be one action away from anywhere in MIA's session. | Must | MVP | PC | Partial (web shell sidebar and Talk; desktop switch planned) | D | §4 → 10 |
| REQ-UX-003 | Apps shall be discoverable by life area, by search and by asking, each showing what MIA can do in it and its status. | Must | MVP | All | Exists (Apps page, M2, M5) | T | P1 → 10 |
| REQ-UX-004 | An interrupted task (a plan half-approved, a skill waiting on an answer, a draft) shall be found again where it was left, on any device. | Should | R1 | All | Partial (skill runs persist; drafts kept; plans New) | D: S-15 | P4 → 10, 12 |
| REQ-UX-005 | Information shall be shown with its source and age wherever a fact could be stale (readings, prices, finds). | Must | MVP | All | Partial | I | DEC-0173 → 10 |
| REQ-UX-006 | Customisation shall be per person and follow them across devices; the standardised parts above are not customisable. | Should | R1 | All | Partial (person settings) | T | P5 → 10 |

## 2. Ambient, Workspace and Immersive modes (§5)

They are three presentations of one runtime and one set of capabilities. Moving between them changes what's shown,
never what she knows or can do.

| Mode | What it's for | Default on | What it shows | Shares |
|---|---|---|---|---|
| Ambient | presence without demanding attention | glasses, phone lock screen, PC idle | the orb, a glance card, a spoken line, paced notifications | the gate, voice, glasses cards |
| Workspace | getting work done | PC | windows, files, apps, MIA's pages, Talk beside them | everything |
| Immersive | full-screen or spatial experiences | nowhere by default | Living Worlds, the Dungeon, spatial dashboards, AR later | the same stores and capabilities |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-UX-010 | Ambient mode shall never take focus, play sound or cover work except for an alarm, an urgent message or the person addressing MIA. | Must | MVP | All | Partial (gate urgency levels; PC ambient surface New) | T | P18 → 10 |
| REQ-UX-011 | Workspace mode shall work fully without MIA's intelligence: files, apps, settings and the terminal behave as on any Linux desktop. | Must | MVP | PC | Planned | D: S-13 | E2 → 10 |
| REQ-UX-012 | Immersive mode shall start only when the person asks, and one action shall return to where they were. | Must | Mature | PC, Gl | Partial (worlds exist as pages) | D | §5 → 11 |
| REQ-UX-013 | The person shall be able to move between modes on a device by one action and by voice; each device remembers its last mode. | Should | R1 | All | New | D | §5 → 10, 12 |

## 3. The MIA-first boot and session (§6)

**The sequence (target):**

1. Firmware → the image's bootloader → the kernel → the disk unlocked (TPM plus PIN).
2. The login screen (the OS's), offering MIA's session (default) and KDE Plasma; recovery and the previous deployment
   are bootloader entries.
3. On login to MIA's session: the user's systemd services start the MIA Runtime; the cage compositor shows MIA's shell
   (the web front end) as soon as the runtime answers; the everyday model loads in the background.
4. Home shows the day from records at once (it needs no model); Talk says "warming up" until the model answers.
5. Background jobs start on their own schedules; deferrable ones wait while the machine is busy starting.

**When things are missing:**

| Missing | What happens |
|---|---|
| The model (Ollama down, GPU driver failed) | Home, every page, search, actions and lookups work; Talk answers from lookups and says the model is unavailable (FR-C2) |
| The network | Everything local works; online lookups and feeds say they're offline; sync waits |
| The runtime fails to start | The session shows a plain recovery page (restart the runtime, open Plasma, view the log); Plasma is unaffected |
| MIA's session fails entirely | The login screen offers Plasma; the bootloader offers the previous deployment |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-UX-020 | MIA's session shall be the default at login on the PC, and the conventional session one choice away on the same screen. | Must | MVP | PC | Planned | D | E5, DEC-0157 → 10, 14 |
| REQ-UX-021 | Home shall show the day from records without waiting for the model; Talk shall say plainly while the model is loading or unavailable. | Must | MVP | All | Exists (Home is code-assembled; FR-C2) | T | E3 → 10 |
| REQ-UX-022 | If the runtime doesn't answer within 30 s of the session starting, the session shall show a recovery page with: restart MIA, open the conventional desktop, show what failed. *(provisional time)* | Must | MVP | PC | New | T: session with the runtime masked | E5 → 14 |
| REQ-UX-023 | From MIA's session, the conventional desktop, settings, a terminal and the system's troubleshooting tools shall be reachable without MIA answering. | Must | MVP | PC | New | D | E2 → 10 |
| REQ-UX-024 | Applications open at logout shall be offered back at the next login, not restored silently. | Could | R1 | PC | New | D | P18 → 10 |

## 4. Accessibility (ACC, §19)

The conventional desktop keeps the OS's accessibility (KDE Plasma's settings, the Orca screen reader over AT-SPI,
which works on Plasma under Wayland, with Plasma's System Settings able to turn Orca on: see the sources). MIA's own
surfaces are web pages, so they are held to WCAG 2.2 level AA (W3C Recommendation, 2023, updated 2024). MIA adds
voice and plain-words help; she never replaces a control.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-ACC-001 | MIA's web surfaces shall meet WCAG 2.2 level AA. | Must | R1 | All | Partial (text size, high contrast exist; no audit) | I: an automated check plus a manual pass | P14 → 10, 11 |
| REQ-ACC-002 | Every function in MIA's session shall be usable by keyboard alone, with visible focus. | Must | R1 | PC | Partial | T: keyboard walk of each page | P14 → 10 |
| REQ-ACC-003 | MIA's pages shall expose their controls to screen readers (semantic HTML, labels), so Orca reads them in the session. | Must | R1 | PC | Partial | I: Orca pass | P14 → 10 |
| REQ-ACC-004 | Text size, high contrast and reduced motion shall be per-person settings applied everywhere, honouring the OS's settings by default. | Must | MVP | All | Partial: text size and contrast exist (`core/accessibility.py`); reduced motion New | T | P14 → 10, 11 |
| REQ-ACC-005 | Everything MIA says aloud shall also be shown as text, and spoken input shall be shown as transcribed. | Must | MVP | All | Exists (Talk) | D | P14 → 10 |
| REQ-ACC-006 | MIA shall be able to read the current page aloud and explain any control on request. | Should | R1 | All | Partial (read aloud exists) | D | P14 → 10 |
| REQ-ACC-007 | Cognitive load: an approval shall state one action in one plain sentence; a page leads with what needs the person. | Must | MVP | All | Exists as practice (approval sentences in code) | I | P14, P18 → 10 |

## Sources

- WCAG 2.2, W3C Recommendation: https://www.w3.org/TR/WCAG22/ (and https://www.w3.org/TR/2023/REC-WCAG22-20231005/)
- Orca on Plasma Wayland: KDE's System Settings change enabling Orca configuration on Wayland,
  https://commits.kde.org/plasma-desktop/923e797209a3799cb600f9b39abff3558fa8f959 ; the fixed Xwayland AT-SPI bug,
  https://bugs.kde.org/show_bug.cgi?id=493054 ; Orca's own help, https://help.gnome.org/users/orca/stable/introduction.html
- Measuring boot: `systemd-analyze` (blame, critical-chain), https://www.man7.org/linux/man-pages/man1/systemd-analyze.1.html
