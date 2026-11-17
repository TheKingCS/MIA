# MIA OS: the desktop and primary interface (Prompt 10)

*Claude (Opus), 2026-11-17, on Zac's go ("continue"). Planning only: no shell, navigation, desktop environment or
configuration was changed. The prompt is `prompts/10_MIA_DESKTOP_PRIMARY_INTERFACE.md`. Twenty-four documents sit
beside this one (section 9).*

## 1. The headline

1. **MIA's desktop already exists, as her web front end**: 109 screens on one shared frame (`web/shell.js`), a
   sidebar of 19 areas, each area its own dashboard (built 2026-11-17), Talk everywhere behind the orb, Ctrl+K
   search, one way to change anything (`MIAShell.act`: a card with Approve Once or Approve From Now On, then Undo),
   live re-reads, and themes that change the look without changing behaviour. On Windows today it fills the window
   of her Qt host (DEC-0124). **The plan keeps all of it** and gives it a Linux home.
2. **On MIA OS, her shell is that front end in its own full-screen window under KWin** in MIA's session, with
   ordinary Linux windows beside it and KDE Plasma one click away at login and from the shell (DEC-0227, settling
   DEC-0191's lean; proof of concept 3 confirms).
3. **One navigation everywhere**: areas → each area's dashboard → apps; Talk from anywhere; a status strip; the same
   on the phone and glasses, shown differently (DEC-0228, DEC-0125).
4. **Search finds and opens; it never changes anything by itself.** Every result says what it is (open, find, ask,
   start, do), and a "do" becomes an approval card (DEC-0229).
5. **MIA sees only what he shares**: a window, a selection, a file or a project, shown as chips in Talk and taken
   back with one press. An open panel reads nothing (DEC-0230). Wayland enforces this (one app can't read another's
   window).
6. **Ambient, Workspace and Immersive are three states of one shell**, never three programs (DEC-0231).
7. **Workspaces are MIA's records restored through KWin's own virtual desktops and session restore**: no app needs a
   MIA integration to be part of one (DEC-0230).
8. **Notifications go through one pipeline**: hers through her gate, apps' and the OS's through the standard
   notification service, all in one history with "why it came" (DEC-0232).
9. **Apps stay where they work**: MIA's in the web frame, conventional Linux apps native (Flatpak); no framework is
   forced on anyone (DEC-0233).

## 2. The audit (verified in the code, 2026-11-17)

| Surface | Exists | State |
|---|---|---|
| Web front end | `web/` (109 pages), `web/shell.js` frame, `web/mia.js` the only engine client | **Working**; the PC's main window since DEC-0124 |
| Navigation | `/api/shell` sidebar (person's apps, child-safe, tucked-away hidden); 19 areas (`core/web_areas.py`), each a dashboard of its apps (`dashboardView`, `&room=1` for the old room) | **Working**; crowding fixed 2026-11-17 |
| Launcher | the Modules screen (`module_browser`, can't be disabled), area dashboards, `apps.html` | **Working** |
| Search | Ctrl+K and "/" (`openSearch`), providers in `core/search_manager.py`, results by `action_type` | **Working** for MIA's records; no files or Linux apps yet |
| Talk | the orb's panel on every page; typed or spoken; her presence from `core/orb_state.py` | **Working** |
| Changes | `MIAShell.act`: propose → card (Approve Once / From Now On) → undo toast (`core/actions.py`) | **Working** |
| Notifications | `core/notification_manager.py`, the gate (`core/communication_gate.py`), `notifications.html`, "why" (`get_message_reason`) | **Working** inside MIA; not the OS's |
| Appearance | themes, colour schemes, layouts (`core/themes.py`, `core/appearance.py`), tokens only (`web/tokens.css`) | **Working** |
| Missions and projects | `missions.html`, `projects.html`, `plan.html`, `steps.html`, the Dungeon (`dungeon.html`), Living Worlds (`worlds.html`, `nexus.html`) | **Working**, separate screens |
| Settings | `settings.html`, Diagnostics, the self-care panels (2026-11-17) | **Working** for MIA; OS settings not reachable |
| Phone | the Android app showing the same web screens, with its own engine for offline | **Working** |
| Glasses | `core/glasses.py` cards with menus | **Working** (view) |
| Classic Qt screens | Ctrl+Shift+C; PC-only apps opened with `/desktop-open/<id>` | **Working**; being retired by parity (`docs/WEB_PARITY.md`) |
| Window and workspace management | none (Windows' own) | **Missing** |
| Context sharing | the Universal Action Layer's selection (`core/ual.py`), the browser's page text | **Partial**; no chips, no revoke |

**Worth preserving:** the frame, the one change path, the area dashboards, Talk-anywhere, the theme split, live
re-reads, parity per device. **Inconsistencies:** Qt and web screens for the same apps; some apps still PC-only;
search doesn't reach files or Linux apps; no workspaces; context isn't shown. **Limits:** one browser-hosted window
can't manage other windows; on Wayland it can't read them either, by design.

## 3. Who does what

| Element | Owner |
|---|---|
| Display, input, windows, virtual desktops, lock screen, portals, accessibility bus, notification server | **Linux and KDE** (KWin, Plasma's services, xdg-desktop-portal-kde, AT-SPI) |
| MIA's shell: sidebar, dashboards, Talk, search, status strip, workspace switcher, modes | **MIA's shell** (`web/` in its host window) |
| Each app's screen | **the app** (a web page on the frame; or a native Linux app) |
| Records, actions, search providers, gate, appearance | **shared MIA services** (the runtime) |
| Understanding a request, answering, routing | **the intelligence infrastructure** (Prompt 07) |
| Plans, runs, approvals, the stop | **the autonomy infrastructure** (Prompt 08) |
| What's working, what she changed | **self-awareness** (Prompt 09) |

## 4. Decisions (records in `MIA_OS_DESKTOP_TECHNOLOGY_EVALUATION.md` §3)

| DEC | Decision | Status |
|---|---|---|
| DEC-0227 | The shell is MIA's web front end in a full-screen window under KWin; Plasma one click away | PROPOSED |
| DEC-0228 | One navigation model: areas, their dashboards, apps; Talk everywhere; a status strip | PROPOSED |
| DEC-0229 | Unified search with typed results; search never executes a change | PROPOSED |
| DEC-0230 | Context only by explicit share, shown and revocable; workspaces as records restored through KWin | PROPOSED |
| DEC-0231 | Ambient, Workspace, Immersive as states of one shell | PROPOSED |
| DEC-0232 | One notification pipeline: her gate for hers, the freedesktop service for the rest, one history | PROPOSED |
| DEC-0233 | Apps stay in the framework that suits them: MIA's on the web frame, Linux apps native | PROPOSED |

## 5. Questions for Zac

`MIA_OS_DESKTOP_OPEN_QUESTIONS.md`: Q-79 (her own window switcher instead of Plasma's taskbar in her session), Q-80
(the second monitor as an always-on ambient display), Q-81 (push-to-talk first, wake word later), Q-82 (a kitchen or
household display: plan only, given DEC-0119).

## 6. Boundaries

Prompt 11 the look; Prompt 12 every device; Prompt 13 permissions in full; Prompt 14 boot and recovery; Prompt 16 the
order of building.

## 7. Sources

The repository, read 2026-11-17; DEC-0013, 0017, 0018, 0023, 0124, 0125, 0183, 0184, 0189, 0191, 0192, 0215, 0217,
0225; Prompt 05's graphical and session architecture. Technology sources in the technology evaluation.

## 8. What it means for him

He logs in, MIA's screen is there, the same one he knows from the PC today. Ordinary apps open in their own windows
beside it, and Plasma is a click away. She sees only what he shows her.

## 9. The documents

`MIA_OS_PRIMARY_DESKTOP_EXPERIENCE.md`, `MIA_OS_DESKTOP_LAYOUT_SPECIFICATION.md`, `MIA_OS_DASHBOARD_ARCHITECTURE.md`,
`MIA_OS_APPLICATION_LAUNCHER_AND_DISCOVERY.md`, `MIA_OS_UNIFIED_SEARCH_ARCHITECTURE.md`,
`MIA_OS_CONVERSATIONAL_INTERFACE.md`, `MIA_OS_AMBIENT_WORKSPACE_IMMERSIVE_MODES.md`,
`MIA_OS_WORKSPACE_AND_CONTEXT_MANAGEMENT.md`, `MIA_OS_WINDOW_MANAGEMENT_INTEGRATION.md`,
`MIA_OS_NOTIFICATION_AND_ATTENTION_SYSTEM.md`, `MIA_OS_MISSIONS_AND_ACTIVITY_INTERFACE.md`,
`MIA_OS_SETTINGS_AND_ADMINISTRATION.md`, `MIA_OS_FILE_AND_INFORMATION_INTERFACE.md`,
`MIA_OS_DESKTOP_VOICE_AND_MULTIMODAL_INTERACTION.md`, `MIA_OS_DESKTOP_ACCESSIBILITY.md`,
`MIA_OS_DESKTOP_DISPLAY_AND_RESPONSIVE_STRATEGY.md`, `MIA_OS_SHARED_HOUSEHOLD_DESKTOP_EXPERIENCE.md`,
`MIA_OS_DESKTOP_VISUAL_COMPONENT_ARCHITECTURE.md`, `MIA_OS_APPLICATION_DESKTOP_INTEGRATION.md`,
`MIA_OS_DESKTOP_FAILURE_AND_FALLBACK.md`, `MIA_OS_DESKTOP_TECHNOLOGY_EVALUATION.md`,
`MIA_OS_DESKTOP_ARCHITECTURE_DIAGRAMS.md`, `MIA_OS_DESKTOP_ACCEPTANCE_CRITERIA.md`, `MIA_OS_DESKTOP_OPEN_QUESTIONS.md`.

## Its look (Prompt 11, 2026-11-17)

Each region's surface tier, accent use and states are in `MIA_OS_DESKTOP_VISUAL_LANGUAGE.md`; the orb's
fourteen states in `MIA_OS_ORB_VISUAL_AND_BEHAVIOR_SPECIFICATION.md` (DEC-0237).

## Across devices (Prompt 12, 2026-11-18)

The desktop is the hub's interface; a conversation started there continues on the phone (`MIA_OS_CROSS_DEVICE_SESSION_CONTINUITY.md`).
