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

## 4. "Build a skill" extends the skills system MIA already has (DEC-0167)

There is one skills system: learning paths (DEC-0112), whose loop already
serves both a person and MIA learning to build herself. "Build a skill" from
a selection starts that loop. **Who is learning** decides where it ends:

| Learner | The path ends in | How it's verified | Who says yes |
|---|---|---|---|
| The person ("I want to learn this") | a learning path: stages, lessons, homework missions (as today) | checks heard, recorded, counted or said | the person starts the drafted path |
| MIA, using what she can already do | a **taught skill** (DEC-0123): a trigger plus steps from her tools, action kinds, browser routines, workflows and questions | practised with the person watching until two clean runs | the person, after the practice runs |
| MIA, needing something new | a **built skill**: code written in the lab's worktree (DEC-0058), with tests and a review by another model | tests pass in the lab, then a trial run | **Zac approves the merge** |

`ual.build_skill` does the following:
1. Researches the selection (cloud rules, §5).
2. Decides which row applies, by checking the needed steps against `core/capabilities.py`: it's a taught skill when every step already exists.
3. Drafts the path. Nothing becomes one of her skills until it's verified and approved.
4. Keeps the source as provenance.

Browser routines and workflows fold in as kinds of taught skill.

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

## 6d. U2 is built (2026-11-15)

The phone's front door:
- **"MIA" in Android's text-selection menu**, in every app (PROCESS_TEXT), and **"Do with MIA"** in the Share menu
  for text and links: `android-phone/.../SelectionActivity.kt`.
- A card opens over the app you're in (`web/selection.html`): what was selected, what MIA can do with it, and the
  pick. A read action shows its result in the card, with Copy; a change shows its sentence and waits for Yes, then
  offers Undo. Close returns to the app.
- The selection reaches the page through a bridge, never in an address. The other app's text is never replaced.
- A selection from an app whose name says it holds money, health or secrets (a bank, a pharmacy, a password
  manager) is sensitive, like MIA's own Money screen: nothing from it is ever offered online.

Of U2's acceptance line: the card works offline on the phone (every ready action runs on the device, no model).
"Explain" and "Draft an email" are U3's actions, so they appear under "Coming" until U3.
Not built: the old "MIA inbox" share target still saves shared files to the inbox, unchanged.

## 6c. The taught-skills engine is built (2026-11-15)

Phase 1 of DEC-0123, which "Build A Skill" (U3) will end in: `core/taught_skills.py`.

- **Steps:** a tool, an action kind, a question, a task of the person's, a sentence. Nothing else yet.
- **Taught** by "watch me" or by writing the steps as lines (`taught_skill.add`, which a UAL action can propose).
- **Gates:** each step runs through the gate it already has. A practising skill asks before every change; a learned
  one asks only for what always asks (pay, buy, send, publish, delete, profile).
- **Front doors:** the chat, ten voice tools, the Taught Skills screen, `/api/taught-skills/*`, a glasses card.
- **Not built:** triggers, browser/phone/desktop steps, unattended runs, lab-built skills (DEC-0167's second ending).

## 6b. U1 is built (2026-11-15)

`core/ual.py` holds the capture contract, the catalogue and its tiers, and
`offer()` and `run()`. It is one module, not the two named in §3.

**The front doors so far:**
- `/api/ual/offer`, `/api/ual/run` and `/api/ual/actions`;
- the Ctrl+K palette (`web/shell.js`), which lists actions when text is selected on a page or 80 or more characters are pasted in;
- two voice tools (`core/assistant_ual_actions.py`).

**Ready actions** (all on the device, no model):
- Find What I Know About This (read);
- Save To My Inbox, Make This A Mission, Start A Project From This and Remember This (act: each is a proposal the person approves, with undo).

The other 18 are in the catalogue as planned and are never offered.

**Tests** (`tests/test_ual.py` and one in `tests/test_server_app.py`):
- the catalogue's rules;
- an injection text that changes neither the offer nor what runs;
- sensitive screens and the online switch;
- the same offer from every front door.

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

## 9. Decisions (Zac, 2026-11-15)

- **Q-11, answered yes:** build U1–U3 now, on the PC and phone, before MIA OS.
- **Q-14, answered "over all apps, files, code, etc, system wide":** the UAL is not a list of chosen apps. Every app, file and piece of code is in scope. The integration levels in §6 are layers that together cover everything, not apps picked one by one:
  1. **Selection and clipboard** work in any app. This is the universal floor.
  2. **Accessibility** reads context from any app that exposes it: AT-SPI on Linux, UI Automation on Windows, the accessibility service on Android.
  3. **Files** come in through the file manager (any file type, through MIA's readers and converters).
  4. **Code and the terminal** go through the shell hook and the editor's selection.
  5. **On request only, OCR or the screen** for apps that expose nothing.

  Deep app-specific integrations are added on top only where these layers fall short.
- **Q-12, answered B + C:** web search with short queries for research and verify. Outside AI only after MIA shows what would be sent and to whom, and the person says yes. Finances, health, the journal and passwords never leave the device.
- **Q-13, answered yes, with more:** taught skills (DEC-0123) are approved, and so are built skills from the lab with Zac's approval. Both extend the one skills system (DEC-0167, §4).

## 9b. Questions still open

- **Q-11:** Start with U1–U3 on the phone and PC now, or wait for MIA OS? Recommend now: it's useful immediately and tests the design.
- **Q-12:** Which cloud use is allowed for UAL actions (research online, council review)? Recommend: online *lookup* on request only; council for owner-only development tasks.
- **Q-13:** Decide DEC-0123 (taught procedures) before U3's "MIA can do this" path?
- **Q-14:** Which apps matter most for deep integration (browser, file manager, IDE, terminal, Office)? This orders U4–U6.
