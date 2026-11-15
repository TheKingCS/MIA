# The Universal Action Layer: how it fits MIA, and the build plan

*Claude, 2026-11-15, from Zac's handoff (`docs/specs/UNIVERSAL_ACTION_LAYER.md`,
DEC-0165). The handoff asks for this plan before substantial
implementation (its §12). Nothing here is built yet.*

## 1. The most important finding: the engine already exists

The handoff's centre is one **action registry and execution path that
every interface shares**. MIA already has that path. It is the action
contract, and the screens, voice, the phone, the glasses and undo all use
it today:

| The handoff asks for | What MIA already has | Gap |
|---|---|---|
| Action registry: id, name, inputs, permissions, outputs, errors, reversibility, local/cloud | `core/actions.py` `ACTION_TYPES` (kind, label, params, describe, execute, child_ok); `core/assistant_actions.py` (~388 tools, with domains and trigger phrases); `core/capabilities.py` (what MIA can do, built from code) | No **input types** (text, file, image, code, URL). No declared **output type**, **reversibility**, **local/cloud** or **permission tier** fields. Those are the UAL's additions |
| Orchestration engine | `core/assistant_turn.py` (turn routing), `core/workflows.py` (DEC-0092), `core/council*.py`, `core/work_agents.py` | No planner for "do X with this selection" across several actions. That is a Prompt 08 item, and the UAL is its first customer |
| Permission and approval | propose → approve → execute → record → undo; `core/browser_safety.py` gates commits; email is only ever drafted | **Capability tiers and grants** (DEC-0156, proposed). Reading and summarising must not need the approval that sending needs |
| Untrusted content | `browser_safety.untrusted()` wraps page text before the model sees it | Has to wrap **every** captured selection, file and OCR text |
| Context capture | the phone's **"Share to MIA"** (`Share.kt`: any app's text or file into MIA's inbox); the inbox (`core/inbox_manager.py`, classify, OCR); the browser (DEC-0117) | No **text-selection menu** entry (Android PROCESS_TEXT). No desktop hotkey or context menu. No browser extension. No accessibility capture |
| Command palette | **Search (Ctrl+K, "/")** in `web/shell.js` and Talk, from every web page | It searches and asks, but doesn't take the current selection or show "actions for this". Super+Space works only on MIA OS (or as a global Windows hotkey) |
| Skill creation | learning paths (`core/paths.py`) for **the person's** skills; taught procedures (DEC-0123, proposed, not built); the development lab (worktree, tests, review; DEC-0058) for **MIA's** capabilities | "Build a skill" must say which it means (§4). Nothing yet turns a selection into a lab task |
| Knowledge | memories, notes, `core/dev_knowledge.py`, the reference library, links | A "save to knowledge" action with source provenance (the URL or app it came from) |
| Results anywhere | the web shell, notifications, the communication gate, glasses cards | — |

**So the UAL is mostly new front doors plus richer action metadata, on top
of the engine that exists.** That is exactly the handoff's rule: "Do not
duplicate existing MIA functionality."

## 2. Architecture (mapped)

```mermaid
flowchart TB
  subgraph Capture["Context capture (new adapters, one contract)"]
    A1[Android: text-selection menu PROCESS_TEXT + Share]
    A2[Windows: global hotkey + Explorer/clipboard]
    A3[Browser extension: selection, URL, page]
    A4[MIA OS: context-menu service + AT-SPI accessibility + Super+Space]
    A5[Glasses: camera frame + what you said]
  end
  Capture --> C[core/ual_context.py: Capture record\ntext/file/image/code/url, source app, url, untrusted=True]
  C --> R[core/ual.py: offer(context) → ranked actions\nfrom ACTION_TYPES + tools tagged with input types]
  R --> P[Palette / menu shows the offer]
  P -->|person picks| PR[core.actions propose → describe sentence]
  PR --> G{tier: read / prepare / act}
  G -->|read, prepare| X[execute → result card]
  G -->|act| AP[approval, as today] --> X
  X --> L[life events, undo, Fix-It Log]
  X --> D[result to where it was asked: phone card, palette, notification, glasses]
```

## 3. Service boundaries and contracts

**`Capture`** (new, `core/ual_context.py`) is what any front door sends.
- Fields: `kind` (text, file, image, code, url, mixed), `text`, `files` (paths or upload ids), `source_app`, `url`, `title`, `surrounding` (optional), `device`, `captured_at`.
- It is **always untrusted**, and it records what could *not* be captured: "no surrounding text, the app didn't expose it". MIA never claims access she didn't get (handoff §4).

**`ActionSpec`** (new metadata alongside each action kind and tool, in one table `core/ual_registry.py`) has these fields:
- `inputs`: the kinds it accepts;
- `needs`: capabilities and services, for example the model, online access, the lab;
- `tier`: read, prepare or act (§5);
- `output`: text, draft, file, mission, skill proposal or knowledge entry;
- `reversible`;
- `where`: local, PC or cloud;
- `group`: research, transform, create, organise or learn.

Existing actions are tagged **without changing their behaviour**. A test fails on a UAL-offered action without a spec (the parity and loop-coverage pattern).

**`offer(capture)`** returns the ranked actions for a capture. It is code-ranked by:
- input kind;
- source app (code in a terminal or IDE, a product page, a document);
- the person's recent picks.

The model is consulted only to phrase the reasons. Each front door calls the same endpoint, `POST /api/ual/offer`. A pick goes through the existing `/api/actions` propose and approve path.

## 4. "Build a skill" means two different things

| The person means | MIA's existing home | UAL action |
|---|---|---|
| "**I** want to learn this" | learning paths (`core/paths.py`, DEC-0112): stages, practice, homework | `ual.learn_path`: drafts a path from the selection; it starts only on the person's yes |
| "**MIA** should be able to do this" | a taught procedure (DEC-0123, still proposed) for steps she can already do; a **development task** in the lab (DEC-0058) for new code | `ual.skill_proposal`: researches the selection and writes a proposal (what's needed, existing implementations, tests). For code, it files a lab task; the lab builds it in a worktree with tests; Zac approves the merge. Nothing is registered until it has been tested and approved (handoff §6: read vs verified vs tested) |

**DEC-0123 (taught procedures) is a prerequisite** for the "MIA can do this"
path without code. It should be decided before UAL phase 3.

## 5. Permission model (fits DEC-0156)

| Tier | Examples | Approval |
|---|---|---|
| read | explain, summarise, translate, OCR, compare against knowledge, find what I know | none: runs, shows the result; nothing stored |
| prepare | draft an email (never sent), convert to a file, a spreadsheet or deck, a research report, a skill proposal, a mission draft | none to make it; **saving** it is an action with undo |
| act | save to knowledge, create a mission or project, file a lab task, run code, change a file, anything outward | the existing approval; outward or destructive actions always need a person (sending, buying, deleting, settings) |

**Cloud rule:**
- A capture is sent to a cloud model only when the action's `where` allows it **and** the person has allowed cloud for that kind of content (DEC-0053's "online when asked", extended).
- By default everything runs on the PC's or the phone's model.
- **Development council actions are owner-only and say they use cloud accounts.**

## 6. Linux (MIA OS) integration requirements, for Prompt 05

- **Global shortcut:** Super+Space through the compositor or desktop's global-shortcut portal (`org.freedesktop.portal.GlobalShortcuts`). In the cage MIA session, MIA owns the key directly.
- **Selection:**
  - read the primary selection and the clipboard through Wayland data-control, with the person's grant;
  - read focused-app context through **AT-SPI** (the accessibility bus), where apps expose it;
  - fall back to OCR of a screenshot only on request, never continuously.
- **Context menus:**
  - file managers through service menus (KDE Dolphin `.desktop` service menus, Nautilus scripts);
  - text in any app through the palette with the selection pre-filled. There is no universal right-click hook on Wayland, by design.
- **Browser:** a WebExtension (Chromium and Firefox) talking to the local runtime over native messaging.
- **Terminal:** a shell function or plugin sending the last command and output to the palette.
- **Every adapter runs as the person, not root**, and can only *send* captures. It never executes anything itself.

## 7. Phases (each ends on a test gate; Zac approves each)

| Phase | Builds | Depends on | Done when (acceptance) |
|---|---|---|---|
| **U1: Registry and offer** | `Capture`, `ActionSpec` tags for ~20 first actions, `offer()`, `/api/ual/offer`; Ctrl+K palette shows "actions for this" when given text | none (today's code) | every offered action has a spec (test); the same capture gives the same offer from web, phone and voice; untrusted wrapping tested with an injection text ("ignore previous instructions…") that never becomes an instruction |
| **U2: Phone front door** | Android text-selection menu entry "MIA" (PROCESS_TEXT) and an upgraded share sheet → the offer card → result | U1 | select text in any Android app → MIA → pick "Explain" gives a result without leaving the app; "Draft an email" gives a draft only; works offline on the phone's model for read actions |
| **U3: First action set** | explain, summarise, translate, verify claims (with sources, marked unverified), research (online only when allowed), convert (to note, spreadsheet, deck via existing exporters), draft email, save to knowledge (with provenance), make a mission, learn path, skill proposal → lab task | U1; DEC-0156 tiers for act | each action has unit tests and a turn-harness test; nothing outward without approval; "verify" never says verified without a cited source |
| **U4: Windows front door** | global hotkey → palette with the clipboard or selection; an Explorer "Send to MIA" entry for files | U1, the runtime (DEC-0155) helps | hotkey works with the MIA window closed (needs the runtime) |
| **U5: Browser extension** | selection, URL and title; right-click "MIA ›" submenu built from `offer()` | U1 | a malicious page's text can't trigger an action; a test page proves it |
| **U6: MIA OS** | portal shortcut, AT-SPI capture, file-manager service menus, terminal hook | MIA OS image (DEC-0157) | in a VM: select text in a KDE app → Super+Space → summarise |
| **U7: Glasses and proactive** | glasses "what is this?" → the same offer; proactive suggestions through the communication gate, off by default | U1–U3 | suggestions respect the 5-a-day limit and quiet hours |

U1–U3 are useful now, on the PC and phone, with no MIA OS. They also test
DEC-0156 (grants) on real actions before system actions exist.

## 8. Testing requirements

- **Contract tests:** every offered action has a complete `ActionSpec`; every tier is honoured by the gate.
- **Injection tests:** captured text that contains instructions, URLs or fake tool calls never changes which action runs or what it may do.
- **Honesty tests:** a capture missing context makes MIA say so; "verify" without a source returns "couldn't verify".
- **Cross-surface tests:** the same capture gives the same offer and the same result from web, phone and voice.
- **Device tests:** the Android selection entry runs on the CI emulator (the phone workflow already boots one).
- **Privacy tests:** no capture text reaches logs (the existing no-secrets-in-logs test is extended), and none is sent to the cloud without the allow.

## 9. Decisions needed from Zac

- **Q-11:** Start with U1–U3 on the phone and PC now, or wait for MIA OS? Recommend now: it's useful immediately and tests the design.
- **Q-12:** Which cloud use is allowed for UAL actions (research online, council review)? Recommend: online *lookup* on request only; council for owner-only development tasks.
- **Q-13:** Decide DEC-0123 (taught procedures) before U3's "MIA can do this" path?
- **Q-14:** Which apps matter most for deep integration (browser, file manager, IDE, terminal, Office)? This orders U4–U6.
