# Next Session: Where We Left Off

The running to-do list between Claude sessions. Claude's cloud sessions
start from a fresh copy of this repo with no memory of past chats, so
**anything not written here is forgotten.** Start a session with "read
docs/NEXT_SESSION.md". Update it at the end of each session.

*Last updated: 2026-11-18 (Opus on the PC: Prompts 12 to 17)*

**At the start of every session (FW-02):** `gh run list -L 8`, and read any failed run (`gh run view <id>
--log-failed`) before building anything: CI is the gate, and a red run is the first thing to fix.

**New 2026-11-20, WP-01 built (the lockdown)**: saying "lockdown" (the whole message), or Lockdown on Sign-ins
and Security, ends every session of his (this one too), unlinks his phones, locks the vaults and stops everything
of hers; only signing in with his password lifts it ("carry on" can't). **WP-02 built too**: each card carries a
binding (its kind, params and sentence); approve refuses a card changed since it was shown or another card's
binding, and execute gets a copy. **WP-03 built**: every lookup that brings outside text (mail, feeds,
a scanned receipt, a team's workspace) is framed like a web page before the model reads it; `tests/test_injection.py`
puts 20 poisoned inputs through each and checks a change asked for after them is held. A new tool that returns outside
text goes in `tool_loop.OUTSIDE_WHAT` and its manifest's `outside`. **WP-04 begun**: `tests/test_sealed_stores.py` holds every personal
file to sealed, public, or `at_rest.NOT_SEALED_YET` with why (56 left, a ceiling that only goes down; 88 sealed). Sealing one: move
its store's reader to `open_text` (catching ValueError and OSError), add its name to SEALED and its class to
`tests/test_at_rest.py`'s SEALED_STORES, take it off the list and lower `NOT_SEALED_YET_MOST`. The budget's seven wait
on the Plaid work; the eight appended logs need line sealing.

**New 2026-11-20, Fable reviewed Opus's work since 2026-11-18** (LS-01 to LS-10, FW-02 to FW-05) with three
independent reviewers: 38 findings, fixed in three commits (authority; data and sync; MIA OS); the list with each
one's status is in `audit/FABLE_REVIEW_2026-11-20.md` (not in the repository). **MIA OS no longer restarts by
itself** (Q-114 asks Zac), and disk enrolment is two steps (`mia-disk-enrol`, restart with the PIN,
`mia-disk-enrol finish`). Both VM runs of the review's last commit passed (74509e62: CI runs 44699128590 and
44699128448), and two builds of the image still match. **Next: FW-06** (the system helper); before building FW-06 to
FW-12, read their specs against each other (the worst finding was two packages that each passed alone). GitHub's
image builds took 40 minutes to 2.5 hours on the same commit: a watcher needs restarting. In a workflow step a bare
`! command` never fails the step (bash -e ignores it): use `if command; then exit 1; fi` or the `absent` helper.

**New 2026-11-19, FW-04 and FW-05 done.** FW-05 (CI run 44602462298): the PIN alone opens the encrypted disk, before
and after an update; Secure Boot off, the TPM refuses and the recovery key opens it. FW-04's snapshot before an
update was taken and held his file (run 44579393224). **Loose end:** prune `/var/mia-snapshots` (nothing does yet).
**Next: FW-06** (the system helper), per the roadmap. The VM workflows take 1.5 to 3 hours; a push touching `os/`
cancels the main one in progress, and so does the daily scheduled run.

**New 2026-11-19, FW-04 accepted in the VM** (CI run 44529591174): night update staged and applied by itself; two
broken updates rolled back by themselves. An install of MIA OS needs /boot as its own ext4 partition (GRUB can't
count boots on Btrfs). Still to see: the snapshot before an update (the VM's homes are a subvolume from the next
run). **FW-05 built and pushed**: `.github/workflows/mia-os-encryption.yml` is its acceptance; read its first run.

**New 2026-11-19, FW-04 part A built**: `core/sd_notify.py` (ready, status, watchdog), `core/self_test.py` (only ever
on an empty folder), greenboot checks in `os/files/greenboot/`, night updates (`os/files/mia-update-*`). Next: the
VM's automatic path and the two broken images that must roll back by themselves (task 7).

**New 2026-11-19, FW-03 done** (MIA's own session, accepted in the VM: login to her front end 3 to 4 s, Plasma 7 to
8 s, keyboard-only recovery, update and rollback). **Next: FW-04** (greenboot, readiness, sd_notify), per the
roadmap. Screenshots are the `mia-login-screenshots` artifact of CI run 44460432338.

**New 2026-11-18, LS-09 built** (`core/replay.py`): `replay(context, jobs, start)` runs a week of daily checks on
a held clock and returns what she said each day; the daily checks and the gate now read `core.clock`.

**New 2026-11-18, LS-10 built**: a habit MIA learns on her own goes in `core/learned.py`'s `habits()` with its
evidence and its own reset (never one that touches what he set). Her deferrable work has a daily time budget
(`homeostasis.daily_budget_minutes`, shown in the runtime's health).

**New 2026-11-18, LS-03 built** (DEC-0285, DEC-0286): a new data file goes in `core/retention.py` (its class,
how long it's kept, what happens at the end, whether it syncs) or `tests/test_retention.py` fails; sync reads
that table. A sync conflict keeps the losing copy in the change history and says one note.

**New 2026-11-18, LS-04 built** (DEC-0283): `tests/test_capability_check.py` reads each capability's tool, kind,
tier and effect as one. A failure is one of four kinds: raise `Refused` or `Unavailable` (core/actions.py) where
that's what it is, plain `ActionError` stays "invalid". A loop that waits on something outside MIA asks
`core.deadline.Deadline.why_not()` between steps.

**New 2026-11-18, LS-05 built** (done means read back, DEC-0218): every approved change is read back
(`core/read_back.py`): its files still hold what it wrote, the records its history names resolve. A new `kind:`
in a life event's refs goes in `core/record_types.py` (`TYPES`, readable) or `HISTORY_ONLY` (why not yet), or
`tests/test_record_types.py` fails. Still to do: titles and pages per type, and the other lists (recall, parity,
loops) reading the registry.

**New 2026-11-18, LS-06 built** (DEC-0224 in the lab): a lab change to code isn't ready without a test that
fails on the starting code and passes after; the merge's message names it ("Shown by: ..."). Night School and
the coder's shadow attempts now fail without one, as they should.

**New 2026-11-18, LS-08 built** (one model-server address): **code that talks to the model server asks
`core.llm_manager.local_server_url(context)`, never writes the address**; embeddings and vision go through
`OllamaBackend.embed` / `see`. A test fails on the port written outside `core/llm_manager.py`.

**New 2026-11-18, LS-07 built** (`core/clock.py`): **new code asks `clock.now()` / `clock.today()`, never
`datetime.now()`**, and tests hold time with `clock.frozen(moment)`. `clock.parse_day(text, said)` gives the day a
phrase means. Existing modules move to it as they're touched.

**New 2026-11-18, LS-01 built** (trace ids, `core/trace.py`): a turn, each scheduled job run and each press on a
screen start a cause; proposals (and their approval, even later), life events, changes kept for undo and in the
history, runs and the security log carry its id; the turn trace keeps it and `template` (the prompt code's version).
To see what one cause did, search those records for its `trace`. A tool that shows it is still to build.

**New 2026-11-18, FW-03 started** (MIA's own session): `core/desktop_session.py`, `gui/os_shell.py`,
`os/files/mia-session`, `mia-shell`, `mia.desktop`; the VM test's new step runs the session under `kwin_wayland
--virtual` and uploads two screenshots (artifact `mia-session-screenshots`). **Check that run first**: the KWin flags
(`--virtual`, `--no-lockscreen`, `--exit-with-session`) and Konsole being in Kinoite are untested assumptions. What's
left of FW-03 is on its entry in the roadmap.

**New 2026-11-18, Zac answered Q-111 to Q-113 yes** (DEC-0280 to 0286 approved). Built: the phone removes, once, the
PC's own copies that synced there (`core/sync.remove_pc_only_copies`, called from the phone's start; flag
`phone.pc_only_removed`), and LS-02's first part (his memories carry source, how, `confirmed_at`, `holds_from`/
`holds_until`; the history and links declare the epistemic contract; `tests/test_memory_provenance.py`). Life notes
followed (`LifeNote` names a note's stored fields; a test checks `add` writes only those): **LS-02 is done.** Next:
FW-03, then LS-01 (trace ids).

**New 2026-11-18, Prompt 21 done** (Opus; Zac scheduled it for Fable, so a fresh Fable reviewer and Codex reviewed
it independently, `docs/mia_os/MIA_LIVING_SYSTEM_REVIEW.md`). `MIA_LIVING_SYSTEM_GAP_ANALYSIS.md` and four more;
DEC-0280 to 0286 proposed; LS-01 to LS-10. **Fixed in it, with tests:** four device-only files no longer sync
(`activity.json`, `recall_index.json`, `runs.json`, `turn_traces.jsonl`); a failed change puts back what it had
written. **Waiting on Zac:** Q-111 to Q-113. **Next:** FW-03 (MIA's session in the VM), or LS-02 (small, at the MVP
gate).

**New 2026-11-18, FW-02 built** (CI as the gate): actions pinned by commit, least permissions, the glasses test's
date fixed, and the whole suite inside the booted image (`mia-os-vm.yml`). Check its first runs. Zac answered 0x
and 0y (keep the review's changes; MIA still restarts Ollama while everything is stopped). His USB stick comes
next week, so HW-01 waits; FW-03 (MIA's session in the VM) is next.

**New 2026-11-18, Fable's review of everything Opus built since 2026-11-17** (three fresh Fable reviewers, read-only,
one each for what MIA may do on her own, what she notes and recalls, and the specialists; Codex reviewed FW-01).
Fixed and pushed in three commits, each defect with a test: `tests/test_authority_review.py`,
`tests/test_observation_review.py`, `tests/test_specialist_review_fixes.py`. The full list with each item's status
is local only (`audit/FABLE_REVIEW_2026-11-18.md`; the repository is public). **What changed that Zac will
notice** is in `docs/WAITING_ON.md` 0x. **Still to do from the review** (in the audit file, marked open or
deferred): the rest of its low items, a Settings switch for a browser's page titles, and a per-kind manifest flag
to replace the rule in `core/kind_grants.always_asks`. After changing anything in `core/eng_calcs.py`, run
`tests/test_specialist_review_fixes.py`. The stop's mark for other processes is `core/stop.hold_file()`.

**New 2026-11-18, FW-01 built** (the first MIA OS work package): the image's base pinned by digest, her Python
packages hash-locked (`os/requirements.lock`, `os/requirements-build.lock`, written by `os/lock_requirements.py`;
**after changing requirements.txt run that script**, it needs uv), the reference PC's model set in the image, the
GPU bench on qwen2.5:14b (70.2 tokens a second on Windows, bar 63), a second no-cache build compared by
`os/image_manifest.py`, the build check on every push and the VM test on its inputs and daily (Codex reviewed FW-01:
two defects, both fixed). Six deviations, each with its reason, are
on FW-01 in `docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`. **Accepted in CI** (run 44297829546: the two builds matched, the VM test and the Linux suite passed). If the
two-build check ever names a file, either it's a package manager's own record (add it to `VOLATILE` with a reason) or
an input isn't pinned. Next: FW-02 (CI as the gate; its first task, the Linux suite on every push, is already on).

**New 2026-11-18, after Prompt 17.** Zac answered Q-105 to Q-110 **yes to all**: the narrower MVP and the release
ladder; the TPM plus a PIN; Windows tried from the enclosure first; the repository unlicensed for now (Piper not
bundled in the image); the 53 proposed decisions approved as a batch; **FW-01 begins** (`docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md` §4).

**New 2026-11-18, Prompt 17 (Claude on Opus; reviewed independently by Codex).**
- **Zac answered Q-102 to Q-104:** the Windows drive into a USB enclosure; the approved features built on Windows
  alongside; R1 does every PC piece first, then the household display, then the laptop.
- **Prompt 17 is done:** `docs/mia_os/MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs now, with sixteen
  final documents (index: `MIA_OS_ARCHITECTURE_DOCUMENT_INDEX.md`). Codex found 8 issues (6 High), all accepted.
  Verdict: ready for the foundation work in a VM, not for the install. **Waiting on Zac:** Q-105 (the narrower MVP
  and the release ladder), Q-106 (a PIN at each start), Q-107 (try Windows from the enclosure first), Q-108 (a
  licence), Q-109 (start FW-01), Q-110 (53 proposed decisions as a batch).
- **Found and not yet fixed in code (FW-01's tasks):** `config/default_config.json` still names llama3.2 at 16k, so
  a fresh image starts on the wrong model; `os/poc/gpu_bench.py` measures qwen3:14b, not the everyday qwen2.5:14b;
  the Containerfile's header still says the VM half hasn't run; `PySide6<7.0` can resolve to 6.12 without WebEngine.
- **A flaky test:** `tests/test_glasses.py` failed once on GitHub around midnight UTC (run 44203625881): FW-02.
- **Codex on Windows** needs `-s read-only -c windows.sandbox="unelevated"`, or it can't run any command.

**New 2026-11-18, Prompt 16 (Claude on Opus).**
- **Zac answered Q-99 to Q-101 yes:** the repository stays public for now; her merged changes pushed; a monthly
  release he approves.
- **Prompt 16 (implementation phases, migration, the roadmap) is done:**
  `docs/mia_os/MIA_OS_IMPLEMENTATION_MASTER_ROADMAP.md` and twenty-one more; DEC-0269 to 0274 proposed;
  REQ-IMP-001 to 006; work packages WP-01 to 22 (WP-01 to 12 build on Windows now). **Waiting on Zac:** Q-102 (the
  Windows drive kept in a USB enclosure), Q-103 (build on Windows alongside), Q-104 (R1's order). Prompt 17 (the
  independent review of the whole plan) on his go.

**New 2026-11-18, Prompt 15 (Claude on Opus).**
- **Zac answered Q-95 to Q-98 as recommended:** updates at night by themselves; the second backup on an external
  drive and the laptop (to buy: a drive, a UPS); a monthly restore drill (to build).
- **Prompt 15 (development, builds and releases) is done:** `docs/mia_os/MIA_OS_DEVELOPMENT_INFRASTRUCTURE.md` and
  twenty-five more; DEC-0262 to 0268 proposed; REQ-DEV-010 to 030. **Waiting on Zac:** Q-99 (the repo public or
  private), Q-100 (push her merged changes), Q-101 (a monthly release he approves); and still his step for the
  phone's signing key (DEC-0160). Prompt 16 on his go.

**New 2026-11-18, Prompt 14 (Claude on Opus).**
- **Zac answered Q-91 to Q-94:** sensitive data never to a cloud model; two-step offered, not required; a lockdown
  phrase (to build); add-ons only from MIA's repository, and everything local once she's built out.
- **Prompt 14 (boot, updates, recovery and reliability) is done:**
  `docs/mia_os/MIA_OS_BOOT_AND_STARTUP_ARCHITECTURE.md` and twenty-five more; DEC-0255 to 0261 proposed;
  REQ-REL-015 to 037. **Waiting on Zac:** Q-95 (updates at night), Q-96 (the off-PC backup), Q-97 (a UPS), Q-98
  (a monthly restore drill). Prompt 15 on his go.

**New 2026-11-18, Prompt 13 (Claude on Opus).**
- **Zac answered Q-87 to Q-90:** the Pi 5 first a household display on the TV; Tailscale only away; the laptop (he
  has it; its model to check) a full engine; a lost phone erases itself on reconnecting.
- **Prompt 13 (security, privacy and permissions) is done:** `docs/mia_os/MIA_OS_SECURITY_ARCHITECTURE.md` and
  twenty-nine more; DEC-0248 to 0254 proposed; REQ-SEC-011 to 039; scenarios A to L. **The specific gaps are in
  `audit/SECURITY_GAPS_2026-11-18.md` on the PC only** (the repo is public). **Waiting on Zac:** Q-91 (sensitive
  never to a cloud model), Q-92 (two-step required away), Q-93 (a lockdown phrase), Q-94 (add-ons only from MIA's
  own repository until sandboxed). Prompt 14 on his go.

**New 2026-11-18, Prompt 12 (Claude on Opus).**
- **Zac answered Q-83 to Q-86:** the Theme Studio from a picture, interface sounds, a Light theme (all to build);
  Zeta Astralis first on an old Android or the Pi 5.
- **Prompt 12 (one MIA across many devices) is done:** `docs/mia_os/MIA_OS_DISTRIBUTED_ARCHITECTURE.md` and
  twenty-five more; DEC-0241 to 0247 proposed; REQ-DST-001 to 033; scenarios A to J. It keeps today's shape (the PC
  the hub, the phone a full engine, the glasses through the phone, the greenhouse node read-only). **Waiting on
  Zac:** Q-87 (the Pi 5's first job), Q-88 (Tailscale only away), Q-89 (the laptop a full engine), Q-90 (a lost
  phone erases itself on reconnecting). Prompt 13 on his go.

**New 2026-11-17, built overnight (Claude on Opus).**
- **Voice approvals:** "approve it", "approve 2", "approve it from now on", "reject it", "what's
  waiting for me?" (`core/spoken_approval.py`, heard in code before anything else; the model never approves).
- **The ambient view on the second monitor** (Q-80): `web/ambient.html` (clock, day, weather, due, music, mission,
  what she's doing) opens full screen on the monitor MIA's window isn't on, and closes when that monitor is turned
  off (`gui/ambient_screens.py`). **Zac to try:** restart MIA with both monitors on, then turn the 1080p one off and
  on. `gui.ambient_screen: false` turns it off.
- CLAUDE.md now names the everyday model correctly (qwen2.5:14b, 32k).
- **Ollama tuned** (Q-67, `docs/HARDWARE.md` §4): flash attention and an 8-bit attention cache, as your user
  variables; Ollama restarted with them. Measured before and after at 32k context: the specialists' qwen2.5:32b went
  from 9–13 to 20–29 tokens/s with the same answers; qwen2.5:14b uses 3 GB less and writes about 5% slower.
- **Recall by meaning, first slice** (DEC-0210, Q-71): `core/recall_index.py`. What MIA remembers, notes, notes to
  self and projects are embedded every 10 minutes (refs, hashes and vectors only, in your folder); "what do I have
  about the coop?" finds them by meaning and re-reads each from its store; without the embedding model it matches
  words and says so. Tried on the PC's real memories: 12 indexed in 1.4 s. Next slices: conversations not in a
  private mode, sqlite-vec when it grows, a "related" group in Ctrl+K search.
- **Q-68 measured: qwen2.5:14b stays the everyday model.** Same routes and flags on the 112 questions; qwen3:14b
  invented context more on open questions and was slower (`pc-check/intelligence-*.md` on the PC; not in git).
- **MIA notes what you're working on** (Q-44, DEC-0197): the program and window title in front of you on the PC,
  every 30 seconds, kept 7 days in your folder; never password managers, private windows, sign-ins or MIA herself.
  The sidebar says "Noting your active app" while it's on; Settings has the switch and **Erase**. Ask "what am I
  working on?" or "where was I?". `core/activity_watch.py`. **It now shapes when her offers come** (Q-74,
  DEC-0217): after 10 of the last 15 minutes on one window, non-urgent offers wait (once, at most 30 minutes) unless
  they're about the project in front of you; urgent ones never wait.

**New 2026-11-17, Prompt 11 (Claude on Opus, overnight).**
- **Prompt 11 (visual identity, themes and spatial interfaces) is done:** `docs/mia_os/MIA_OS_VISUAL_IDENTITY.md`
  and twenty-four more; DEC-0234 to 0240 proposed; REQ-VIS-001 to 026. It keeps the built identity (Aquatic glass,
  one cyan accent, ten themes as data) and completes it: the orb's fourteen states, a Light theme, the Theme Studio
  from his pictures, interface sounds (the Theme Studio, high contrast and win sounds already exist). **Waiting on Zac:** Q-83 (the Theme Studio from his picture), Q-84 (default sounds), Q-85 (a Light
  theme; Graffiti, Neon later), Q-86 (Zeta Astralis on a small phone first). Prompt 12 on his go.

**New 2026-11-17, Prompt 10 (Claude on Opus).**
- **Prompt 10 (the desktop and primary interface) is done:** `docs/mia_os/MIA_OS_DESKTOP_ARCHITECTURE.md` and
  twenty-four more; DEC-0227 to 0233 proposed; REQ-DSK-001 to 032. Her shell on MIA OS is today's web front end,
  full screen under KWin, Linux windows beside it, Plasma one press away. **Zac's answers:** Q-79 to Q-81
  yes; she must flow to one monitor when he turns one off (REQ-DSK-033); Q-82 no: the household display is for
  him and his wife, planned for real (REQ-DSK-028, 034). Prompt 11 on his go.

**New 2026-11-17, Prompt 09 (Claude on Opus).**
- **Approve From Now On is built** (`core/kind_grants.py`; DEC-0215): a card's second button makes a standing grant
  for that kind, listed and taken back with his other grants, lapsing after 90 days unused.
- **Prompt 09 (self-awareness, inspection and self-development) is done:**
  `docs/mia_os/MIA_OS_SELF_AWARENESS_ARCHITECTURE.md` and twenty-one more; DEC-0220 to 0226 proposed; REQ-SLF-001
  to 021. **Zac said yes to all:** a daily summary of her own merged changes with an Undo each (Q-76), restarting her
  own services on a failed check (Q-77), the protected list shown and extended (Q-78); DEC-0222 and 0225 approved.
- **Built the same day:** `core/self_merges.py` (Night School step 7a1b: one kept change a night reviewed; Claude's
  pass merges through the lab; a daily summary; Undo is `lab.revert`, on Diagnostics or "undo my change"),
  `core/self_repair.py` (every five minutes: Ollama started, the model reloaded, a stuck job run again; told after),
  `core/protected_list.py` (the list in words on Diagnostics and "what can't you change?"; grants, the stop, browser
  safety, action effects, the inspection, the lab's actions and these three files added to `PROTECTED`).
  Prompt 10 on his go.

**New 2026-11-17, Prompt 08 (Claude on Opus).**
- **Prompt 08 (autonomy, agents and execution) is done:** `docs/mia_os/MIA_OS_AUTONOMY_ARCHITECTURE.md` and
  twenty-three more; DEC-0213 to 0219 proposed; REQ-AGT-001 to 034 (the matrix reads them: 290 requirements).
  **Zac's answers:** every approval card offers **Approve Once** or **Approve From Now On** (a standing grant; never
  money, messages, publishing, deletion outside undo or system changes): DEC-0215 approved as amended, **built**
  (`core/kind_grants.py`: the card's Approve From Now On keeps a standing yes; MIA's own later proposal of that
  kind runs at once with an Undo, marked `auto`; listed and taken back with his grants; lapses after 90 days
  unused; 373 of 482 kinds may have it). Not yet: by voice ("yes, and from now on");
  what he's working on may shape offers (DEC-0217 approved); no quiet hours. Prompt 09 on his go.
- **Bench:** Mistral Small 24B done (strong on electrical, textiles, power; weak on crafts; guessed once on
  embedded). gpt-oss:20b's run had died printing a narrow no-break space to the Windows console; `tools/eng_bench.py`
  now prints UTF-8; re-running. Commit all of `work/eng_bench/` when it's done.

**New 2026-11-17, later at the PC (Claude on Opus): Prompt 06 answered, the window, Prompt 07.**
- **Zac answered Q-63 to Q-67:** case and power supply unknown (his brother built it); grow by nodes approved
  (DEC-0202); a bigger drive approved, but the board has **one** M.2 slot, so it replaces the 1 TB; a laptop, tablet
  and smart display are planned (DEC-0205 amended); tune the PC: **multithreading is back on** (Gigabyte's X3D Turbo
  Mode had switched it off), EXPO and virtualization already on. Ollama's flash attention and q8_0 cache wait for a
  bench before and after.
- **The window** opens maximized; the Dashboard uses two columns on wide screens and fits; the sidebar tightens on
  short screens; **each area opens its own dashboard** (a card per subcategory with what needs him there), the room
  one button away (`d6864114`).
- **Prompt 07 (intelligence infrastructure) is done:** `docs/mia_os/MIA_OS_INTELLIGENCE_ARCHITECTURE.md` and twenty
  more; DEC-0206 to 0212 proposed; REQ-INT-001 to 036. **Found: the everyday model is qwen2.5:14b with a 32k
  context; CLAUDE.md still says llama3.2 3B.** **Zac: "Yes to all your recommendations"** (DEC-0206 to 0212 approved); knowing who's talking is low priority,
  not planned (DEC-0163). Prompt 08 on his go. **To build from it:** measure qwen3:14b vs qwen2.5:14b on his own
  questions (Q-68), whisper.cpp vs Vosk on his voice (Q-70), the recall index without the journal (Q-71).
- **The bench:** qwen3:14b done on the full set; the other three and gpt-oss:20b, mistral-small:24b running (a
  session restart killed the first attempt). Commit `work/eng_bench/` when it ends.

**New 2026-11-17, at the PC (Claude on Opus): Prompt 06, and Zac's word on Plaid and the window.**
- **Prompt 06 (hardware and platform) is done:** `docs/mia_os/MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md` and twenty
  more. The PC was read from the machine: **a Mini-ITX build (Gigabyte A620I AX): one graphics slot, two memory slots,
  both full**, 1 TB drive; SMT appears off. So MIA grows by adding machines, not cards (DEC-0202). DEC-0201 to 0205
  proposed; REQ-HW-007 to 031 added (the matrix reads them). **Waiting on Zac: Q-63 to Q-67.** Prompt 07 on his go.
- **Corrected:** the hardware advice recommended a second graphics card, which can't fit this PC; `docs/HARDWARE.md`
  now recommends a model-serving machine, a bigger drive, memory later.
- **Zac:** no Plaid until MIA is much further along and secure; no USB stick yet (PoC 1 waits). **The window** is
  too tall (he scrolls to reach the bottom), crammed to one side with empty space, and the areas (Home, Garage,
  Finances...) should open their own dashboards of subcategories, not the portals: in `docs/WAITING_ON.md`, to fix.
  His main monitor is 3840 x 2160; check the layout at that size and his scaling.
- **Bench:** gpt-oss:20b and mistral-small:24b pulled; the four-model re-run is in progress; bench the two new ones
  after it.

**New 2026-11-17, later still (Claude on Opus): Zac's "Yes to all" (Q-59 to Q-62, DEC-0199), Claude's inspection (DEC-0200), hardware.**
- **Decided:** the Specialist Forge, online learning kept offline, the Workroom (DEC-0199). **DEC-0200:** Claude inspects
  a new specialist, calculator, model choice or adapter before it's used, as Night School's teacher does; a model
  choice goes live on Claude's pass, code still merges on Zac's approval (Claude's reading of "to test and approve
  them", flagged for him to correct).
- **Hardware recommendation** in `docs/HARDWARE.md` ("What to add for the specialists"): bench gpt-oss-20b and
  Mistral Small first (a different-family reviewer, free); then a second graphics card (a used RX 7900 XTX is the best
  value; check the power supply, slot and case), a 2 to 4 TB drive, memory later, a second machine much later.
- **Built, F1:** `core/specialist_roster.py`, the "counts as added" bar in code; the Specialists page (AI Tools); voice
  `specialist_roster`. It found Software and AI engineering had one starter question (fixed). Today: the hoodie's
  four are built but not passing, because no model has been benched on their disciplines yet.
- **The bench is re-running all four models** on the full task set (the hoodie's tasks landed mid-run). Commit
  `work/eng_bench/` when it's done; the roster and each specialist's model update from it.
- **Built, F6 (DEC-0200):** `core/model_inspection.py`. Each specialist's chosen model is pending until Claude inspects it
  on its current bench results (a re-run makes it pending again). Code builds the evidence (the bench counts, the
  problems it got wrong with what was expected); the inspector only reads; a pass can't stand against a failing
  bench and an unreadable reply is a hold; every verdict is kept in `work/inspections.json`. Night School inspects
  one a night before study hall. The Specialists page shows inspected, held or not yet; by voice
  `model_inspections`. **Not yet:** the worksheet still uses a chosen model before it's inspected (DEC-0200 says
  before it's used: gate it once the first inspections are in, so the specialists don't all fall back to the
  everyday model overnight); inspecting the Forge's code (with F4).
- **Next:** F2 (online to offline packs), F3 and F4 (the Forge drafts and builds the next
  planned specialist, IoT and sensors), W1 (how many agents the card serves). Q-44 still unbuilt.

**New 2026-11-17, later, on the PC (Claude on Opus), after the PC restarted for an update.**
- **The bench re-run was cut off by the restart** (2 of 4 models done, with the new structural and crafts tasks):
  qwen2.5:14b and qwen3-coder:30b kept; qwen3:14b and qwen2.5:32b re-running. Commit all four with the
  specialist models re-chosen when it finishes.
- **Zac's request, kept verbatim** (`docs/mia_os/prompts/26_SPECIALIST_FORGE_AND_PARALLEL_AGENTS.md`): MIA should add,
  refine and specialize her own specialists, use resources online and keep working offline, and explore many agents
  working at once with visible cursors. **Design:** `docs/mia_os/MIA_OS_SPECIALIST_FORGE.md` (the Forge's pipeline,
  learn online and keep it offline, the Workroom of parallel browser agents). **Waiting on Zac: Q-59 to Q-62.**
  F1 (the "counts as added" check and the roster page) and W1 (measure how many agents the card serves) need no
  decision.
- **Q-44 (MIA knows what he's working on) is still not built**; the design is in DEC-0197 and the prompt 23 review's
  section on activity context.

**New 2026-11-17, on the PC (Claude on Opus), alongside the cloud session below.**
- **Opus's independent review of Fable's three** (the stop UI-2, Forge's scaffold M7, plans across apps UI-7): all
  fixed, each with tests (K-0277). Plans: nothing that pays, buys, sends, publishes, deletes or touches a grant is a
  step any more (marking a bill or debt paid is the one bookkeeping exception); the card pins the step it showed; a
  finished plan takes no more changes; a failed step can be retried; "do step N" never rides along with other calls.
  The stop: "stop all alarms" is no longer "stop everything"; "tonight" late at night ends next morning; a time she
  can't read is asked about, never held forever; "stop it" ends a job walkthrough; the desktop's Qt chat and
  push-to-talk now hear the stop; reminders he set still come while stopped; the hold is known from boot. Forge:
  all-or-nothing on a failed write; unsafe names, a trailing-newline id and Windows device names refused; a comment
  after a list's last item no longer swallows the new one. **The review queue for Fable's UI-2, M7, UI-7 is clear.**
- **Built (T1, first part, DEC-0198):** every specialist is an agent role (`core/specialists.py` `ROLES`):
  department, task types, read-only tools, reasoning, needs, reviewers, caveat for all 18; one whose answers rest on
  figures has the worksheet (`work_it_out`); `list_specialists` by voice. Tests: no agent can call a tool that
  changes anything; every safety department carries its caveat. Maker's esp32/arduino words moved to embedded.
- **Built (T2, the workspace, DEC-0198):** `core/teamwork.py`. Each project has a workspace of entries (finding,
  constraint, question, recommendation, conflict, review, decision, risk, deliverable): his are confirmed, a
  specialist's derived until he confirms (it must name its model; a sourced finding names its source; withdrawn ones
  are kept, marked). `framed()` hands a specialist exactly the entries named, as outside text. A team is proposed
  (`team.propose`) and is `ready` only on his yes (`team.start`, tier act_with_approval, so MIA can never start one);
  nothing runs in it until T3. On each project's card (Projects page): Workspace, Note Something, Confirm, Withdraw,
  Propose A Team, Start, Stop. By voice: "note a constraint for the greenhouse: ...", "what's in the workspace",
  "confirm entry 1", "propose a team", "start the team".
- **S4, the first new specialist: Greenhouse systems** (the pilot's), complete by the plan's bar: charter and
  limits, caveat, starter questions, its role, four calculators in `core/eng_calcs.py` (glazing heat loss, fan size,
  drip water, heater propane; each checked against a hand-worked example) and five bench tasks (g1 to g5, one with a
  missing input). Its worksheet uses the greenhouse and electrical calculators; homesteading and HVAC get the
  greenhouse ones too. New units: mL (the first PC run couldn't read it), ft3, BTU/h, cfm, gpm, gph, U-values.
  Found on the way: `calculate()` refused every negative input, so a night below 0 °F couldn't be entered; a
  calculator now names the inputs that may be negative (`signed`).
- **S0b, the bench's PC run, done** (`work/eng_bench/`, K-0280). With calculators (the worksheet's way), share good
  and guesses: qwen2.5:32b electrical 100%, greenhouse 100%, embedded 50%, crafts 67%, never guessed; qwen3:14b
  86 / 100 / 75 / 67, never guessed (10 s a task); qwen3-coder:30b 86 / 80 / 75 / 67 but guessed in every
  discipline; qwen2.5:14b 86 / 80 / 50 / 67. Alone (no calculators) every model is far worse at greenhouse and
  crafts, which is why the worksheet exists. Fixes the run forced: thinking capped at 3072 tokens and left out
  before scoring; a placeholder for a missing input isn't a guess; descriptions never offer a value (two models
  copied "about 1.15" as a U-value); cfm/ft2 is a unit.
- **Built, T1's second part:** `core/specialist_models.py`, each specialist's model from that table (most disciplines
  benched, then fewest guesses, then share, then speed; passes at 80% with no guess). Now: embedded, maker and
  software on qwen3:14b; electrical, greenhouse, HVAC, radio, homesteading on qwen2.5:32b; crafts on qwen2.5:32b
  but not passing (only 3 bench tasks); construction and carpentry not benched (structural has no tasks yet). The
  worksheet plans and writes on that model, and says so when it didn't pass.
- **Built:** structural and crafts calculators (stair risers, board feet, concrete with 80 lb bags; soap lye from
  published NaOH values for five oils, alum mordant) and 12 new bench tasks, so those disciplines can pass or fail;
  re-benched on the PC (`work/eng_bench/`). **S5, the review** (`core/specialist_review.py`): a second local model
  checks the worksheet's plan (calculators and inputs against the question, never the arithmetic) for
  safety-critical work or when he asks ("check it"); the best other model on the bench; independent only across
  families, and every capable model here is a qwen, so it says "not fully independent"; a doubt holds the answer;
  an unreadable or missing review is never agreement.
- **S4's second batch, the hoodie's four (Opus, after the broken session's sign-in failure):** Acoustics and audio,
  Audio signal processing, Textiles and wearables, Portable power, each complete by the plan's bar: charter and
  limits (NIOSH listening time near the ears; heat and burns from anything electric worn; lithium named a fire risk
  every time), caveat, starter questions, role, worksheet disciplines, 19 calculators in `core/eng_calcs.py` (SPL at
  distance, amplifier power, sealed box, sound delay, safe listening time; buffer latency, data rate, dynamic range,
  FFT resolution, delay in samples; yardage, fabric weight, shrinkage, conductive thread; battery pack, charge time,
  C-rate, converter input current), each against a hand-worked example, and 22 bench tasks (a, d, t, p; one missing
  input each). New units: dB, data rates and sizes, GSM and oz/yd2, ohm/m. **Fixed on the way:** a temperature
  given on another scale was converted as a difference (7 degC into a degF input became 12.6, not 44.6).
- **Next (Opus):** T3, the team's coordination on UI-7's task engine; the next S4 batch (the rest of the Engineering
  department). Zac's question in the broken session ("what were Q-54 to Q-58?") was answered by DEC-0198 since. **For Zac:** an independent
  reviewer needs a capable model from another family (a Llama or Mistral of 30B or more) or a bigger card.
  **Hardware (Prompt 06):** the 24 GB card holds one 32B model at a time; the bench is what a bigger card would be
  measured against.
- **Not mine, left uncommitted on the PC:** a third session's email inbox files, budget/Plaid edits and specialist
  workbook notes. Its homesteading notes make `tests/test_connections.py::test_a_plan_is_found_only_when_it_really_is_a_plan_for_it`
  fail on the PC (it passes on a clean checkout), and its Plaid edit fails `test_import_transaction_transfer_is_skipped`.


**New 2026-11-17, from Zac's phone (Claude, cloud session; the PC session needs Zac to sign in again).**
- **Q-53 answered (DEC-0197):** the specialists run on local models that can do the engineering; build whatever makes
  that possible. **Q-44 answered yes:** MIA should know what he's working on. Q-54 to Q-58 still open.
- **Q-54 to Q-58: "Yes to all" (DEC-0198)**, and the other specialists stay a priority: added in batches on a
  schedule, not left for later.
- **The plan is written, for Zac's review:** `docs/mia_os/MIA_OS_LOCAL_SPECIALISTS_PLAN.md`. The model decides,
  code computes every number, a second local model checks. Order: S0a the units module and engineering bench
  (Fable), S1 the worksheet engine (Fable), S2 calculators with electrical first (Opus), S4 the roster track from
  week one (Opus), S0b the measurement run **on the PC**.
- **Zac, 2026-11-17: "Lets build."** He wants specialists for embedded systems and homestead crafts for sure, and is
  open to buying better hardware for the models (`MIA_OS_LOCAL_SPECIALISTS_PLAN.md` section 9).
- **Built (Fable): S0a and the start of S2** (K-0275):
  - `core/quantities.py`: numbers with units; adding metres to volts is refused.
  - `core/eng_calcs.py`: 13 calculators (electrical 5, embedded 5, structural 1, crafts 2), each tested against an
    example worked by hand; a missing input is named, never guessed; safety-critical ones carry the caveat.
  - `core/eng_bench.py` and `python -m tools.eng_bench --model <name>`: 18 tasks whose answers code checks, asked two
    ways (the model alone, and the model choosing calculators); counts right, wrong, **guessed**, asked, unreadable.
  - Two new specialists: **Embedded systems** and **Homestead crafts** (18 now).
  - Fixed on the way: `tests/test_stop.py` had a test that only passed on 2026-11-16 (it used the real clock).
- **Zac at the PC (S0b):** pull the candidate models in Ollama, then `python -m tools.eng_bench --model <name>` for
  each (and for `qwen2.5:14b` as the baseline). Results land in `work/eng_bench/`; commit them.
- **Built (Fable): S1, the worksheet** (K-0276): `core/specialist_work.py`. The model plans which calculators to run
  (JSON), code runs them, the model writes the explanation, and code checks every number in it traces to a
  calculator, the question or a note; one that doesn't is sent back once, then the calculators' own sentences are
  the answer. A missing value is asked for. By voice: `work_it_out` ("what wire gauge...", "what resistor...").
  **Not yet:** a screen for it (parity), review by a second local model (S5), the model chosen per specialist (S3).
- **Next:** a Specialists screen with the worksheet and the roster **(Opus)**; S2 more calculators (radio, plumbing, HVAC,
  acoustics, greenhouse) **(Opus)**; S4 the next batch of specialists (greenhouse systems, IoT, acoustics, textile)
  **(Opus)**.
- The teams document (`MIA_OS_SPECIALIZED_AGENT_TEAMS.md`) still says cloud models in its sections 1 and 12: read it
  with DEC-0197.

**New 2026-11-16, on the PC (Claude on Fable): the Fable run Zac asked for.**
- **Review queue items 14 to 23**: done (K-0261; what changed is listed under the queue below).
- **Prompt 23 (Universal Intelligence)**: Fable's architectural review is `docs/mia_os/MIA_OS_UNIVERSAL_INTELLIGENCE_REVIEW.md`.
  Two thirds exists; six real gaps; no new service; one run record under skills, workflows and browser routines
  comes first. DEC-0188 proposed. **Waiting on Zac: Q-43 to Q-46.** Next for it: Opus's independent engineering
  review (the handoff's own order; the brief is the review's section 8), then steps UI-1 to UI-3 on Opus.
- **MIA OS Prompt 05 (the core operating system architecture)**: done, planning only (K-0262). Start at
  `docs/mia_os/MIA_OS_CORE_ARCHITECTURE.md`; fourteen more beside it. Linux underneath untouched (Fedora's KDE
  desktop as an image built from this repository); MIA as user services and one session on top; one coordinator
  (the runtime); a small root helper whose every operation the operating system itself asks Zac to confirm. DEC-0189
  to DEC-0195 proposed. **Waiting on Zac: Q-47 to Q-51**, above all Q-49: six proofs of concept described and not
  run, one of which needs him at the PC with a Fedora USB stick (it decides the foundation). Prompt 06 waits for
  his review and go; it is not started.
- **Zac's answers the same day** (Q-43 to Q-51): the PC's base approved (DEC-0189, with DEC-0154, 0157, 0158),
  test both compositors leaning to KDE's, always the password, MIA runs when he's signed out, the shelf keeps
  only what's sent, Opus starts prompt 23's work. Q-44 open (he asked why; answered in chat). Q-45 answered: one
  browser, MIA's becomes his everyday one; Q-52, its four safety rules: "Yes to all" (DEC-0196 approved).
  **To build (Opus):** the import of his bookmarks and passwords, tab ownership, a sensitive-sites list, private
  windows left alone; then her browser as his everyday window.
- **Proofs of concept, first results** (GitHub's Linux machines; `os/`, `.github/workflows/mia-os-poc.yml`):
  Landlock passed; the Fedora 45 image builds and passes bootc's lint with Ollama ROCm and Vulkan from Fedora;
  the runtime runs as a user service; the suite passes on Linux. Bug found and fixed: no sound server stopped
  the runtime. **Zac at the PC: the graphics card test, `os/poc/README.md`.** Still to do: a VM for booting the
  image, the session test (PoC 3) and the helper (PoC 5).
- **Opus's independent review of prompt 23** is done (the review's section 14).
- **Built (Opus): UI-1, the run record** (K-0264): `core/runs.py`, one record for anything MIA runs in steps.
  Browser routines, taught skills and workflows write it; a restart marks cut-off runs stopped (shown with a
  killed process); saying no to a held browser step, or letting it expire, ends its run at once (a new optional
  `rejected` hook on action types). "What's running?" by voice (`whats_running`) and a Running column on the
  Dashboard's Agent Activity. **Next on Opus:** UI-3, the durable history (reversibility and reach per action
  kind; before-states on disk, grouped by action; undo by time), or DEC-0196's one browser (import, tab ownership,
  sensitive sites, private windows left alone). UI-2 (the stop) is Fable's, on this record.
- **Built (Opus): UI-3, first part, the lasting history** (K-0265): `core/change_history.py` keeps every change
  30 days on disk (sealed, compressed before-bytes, once per content), so "undo what you did to the greenhouse
  this afternoon" works after a restart: newest first, each change whole or not at all, only where nothing
  changed it since; the tool lists first and waits for a yes; Recent Changes has Undo By Time. **Next on Opus:**
  UI-3's second part (reversibility and reach on every action kind, REQ-AUT-006, 007), then DEC-0196's browser.
- **Built (Opus): DEC-0196, one browser** (K-0266): Settings › Browser has "Use MIA's browser as my everyday
  browser" and "Private sites"; everyday mode opens a normal Edge window (Playwright's testing switches left
  off) with MIA in her own tab; "take over this tab"; private sites read only when he asks right then. **Zac at the
  PC:** turn it on, import bookmarks and passwords through Edge's own Import, list private sites, and check that
  InPrivate windows stay invisible to her (`docs/BROWSER.md`).
- **Reviewed (Fable): the shelf (UI-4) and opportunity scoring (P3)**, both written on Opus (K-0274). Three fixes:
  shelf entries used together stay sensitive when any of them came from a bank, health or password app (the
  combined selection used to lose that, so an online action could be offered for it); a listing with several
  amounts ("was $80, now $45", "$5 off") has no price she trusts, so a discount is never read as the price and
  called the lowest seen; a drop into a text box is left to the browser. **Still to review, by Opus (they were
  written on Fable, so Fable's review wouldn't be independent): the stop (UI-2), Forge's scaffold (M7) and plans
  across apps (UI-7).**
- **Built: UI-7, plans across apps** (K-0273): `core/step_plans.py`. A plan is a list of changes in different apps,
  each shown with its app and that it can be undone; nothing runs when it's made. He does (asks first), changes or
  leaves out steps one at a time, on the Step By Step page (AI Tools) or by voice ("plan my week", "what's the
  plan", "do step 1", "drop step 2"). Anything that buys, sends or can't be undone is listed as "can't" and is
  never run from a plan. "Plan my week" builds one in code from today's list. A plan is a run (shows in what's
  running, waiting on him). **This is the task engine the Specialized Agent Teams design (prompt 25, T3) builds
  on.** Not yet: steps that depend on each other, a plan drafted by a model. **Fable reviews it (it runs other
  apps' actions).**
- **Built: M7's first half, MIA Forge's scaffold** (K-0272): `python -m tools.new_app <id> "<Name>" <area>` writes a
  new app as a registered, empty screen: its manifest, page, script and first test, and its line in the seven
  places that list apps (found by running the whole suite on a scaffolded app). It refuses a bad or taken id
  and writes nothing; `--dry-run` shows the plan; `--root` points at a lab worktree. The app gets no tools,
  actions, stores or permissions, and MIA says it's "planned, not built yet". **Not built:** generation in the
  lab (a model filling the app in), and asking for a new app by voice. **Fable reviews it.**
- **Prompt 25, Specialized Agent Teams** (Zac, 2026-11-16; verbatim in
  `docs/mia_os/prompts/25_SPECIALIZED_AGENT_TEAMS.md`): the audit and architecture it asks for are done (Fable),
  `docs/mia_os/MIA_OS_SPECIALIZED_AGENT_TEAMS.md`. Nothing is built. It extends the 16 specialists into the agent
  registry, reuses the council's floor, the run record, the stop, projects and grants, and adds a team record and
  a workspace of structured entries. **Waiting on Zac: Q-53 to Q-58** (cloud models for specialists, teams start
  only on his yes, the pilot project, start with the 16, the safety caveat, where it sits in the queue). Then T1
  (registry) and T2 (workspace) on Opus; T3 shares its task engine with UI-7. Opus should review the document
  before building, as with prompt 23.
- **Built (Opus): Procurement P3, first part** (K-0271): `core/opportunity.py`. A find that meets a project's need is
  scored on the proposal's nine dimensions, each with its reason, and gets buy when ready, investigate, wait or
  skip; a saving only when the price book verified it. The World page's Opportunities tab; "what's worth buying?".
  Bug found on the way: a price was read from "12V"; prices now need a currency sign. **Not yet:** quality,
  distance and strategic value from real records; the Procurement view's Compare, Saved, History and Reports.
  **Fable reviews it.**
- **Built (Opus): UI-4, the shelf** (K-0270): `core/shelf.py`. Only what you send goes on it (Q-43), each thing for a
  week. Keep On My Shelf in the Ctrl+K and phone selection menus; drop text, a link or a file on any MIA page;
  "keep this on my shelf: ...". The Shelf page (AI Tools) picks several and does one thing with them together
  (summarise, find what you know, make a mission...); Take Off and Clear, each undoable. Nothing on it becomes a
  memory by itself. Not built: watching the clipboard (stays off), a file's contents (only its name is kept),
  and the phone's own Share-to-shelf. **Fable reviews it.** **Zac:** try a drop and the Shelf page.
- **Built (Fable): UI-2, the stop** (K-0269): `core/stop.py`. "Stop" ends her speech, the skill she's running with him and
  her browser task (a held step is let go, never pressed); "stop everything" (optionally "until tonight", "for two
  hours") also makes her own background work wait, holds her unprompted messages (urgent ones still come) and
  refuses anything she'd start herself, until "carry on". Recognised in code before the model; a Stop control in
  the frame on every page and a banner while it's on; survives a restart. Alarms, reminders, backups and the
  greenhouse are never touched. Every job and daily check is sorted in `core/stop.py` and a test fails on a new
  one nobody sorted. **Left:** a turn already in progress finishes its reply before the stop is handled (her speech is cut at once), a fetch in progress finishes rather than being dropped;
  and the glasses have no button yet. **Zac:** try it by voice and from the phone.
- **Built (Opus): UI-3's second part** (K-0267): `core/action_effects.py` says what every action kind reaches
  (records, device, system, outside) and whether it can be undone; 22 of 468 differ from "records, undoable". An
  irreversible one's approval card says "This can't be undone."; system and outside ones always ask (merging a
  lab change into MIA's code was only within a grant: now it asks every time). REQ-AUT-006, 007 met.
- **For the next session:** nothing of Fable's is queued until Zac answers. Opus can take prompt 23's independent
  review, Procurement P3, or Forge (M7).


**New 2026-11-15, on the PC (Claude): World Intelligence, proposed (prompt 18, DEC-0170).**
- Zac's handoff "World Intelligence, Opportunity Discovery & Demonstration-Based Browser Automation" is kept verbatim
  in `docs/mia_os/prompts/18_WORLD_INTELLIGENCE_EXPANSION.md`. It asked for an investigation before building.
- The proposal: `docs/mia_os/MIA_OS_WORLD_INTELLIGENCE_PROPOSAL.md`. About two thirds exists (Good News Radio's feed
  reader, SearXNG lookup, Research This and Verify, her browser and its gate, browser routines, taught skills, the
  gate, links, the development engine). New: watches, a discovery store with provenance, relevance in code, a World
  page. Phases W0–W8, beside MIA OS; W4 (grants) and the unattended browser review are **(Fable)**, the rest **(Opus)**.
- **Zac's answers (DEC-0171, approved):** no fixed limit on her own messages, pacing learned from what he engages
  with; MIA makes watches herself from his life; Marketplace, Craigslist and eBay by his demonstrated skills; about
  four finds a day. Starting sources checked from the PC (proposal 5b), with a source loop to keep improving them.
- **DEC-0170 approved** (Zac, 2026-11-15). Q-20: within 360 miles. Keys skipped for now. Stores added: auctions,
  home stores, import marketplaces, Amazon, Walmart, Target, Kroger.
- **Procurement proposed** (prompt 19, `docs/mia_os/MIA_OS_PROCUREMENT_PROPOSAL.md`, DEC-0172): requirements per
  project from plans, specs compared by numbers, price observations, acquisition plans. Waiting on Q-21 (approve
  it). Q-22 (his own trip figures) and Q-23 (his stores, in his own data) answered.
- **Later device step (Zac, 2026-11-15):** MIA in his vehicle, through the phone or a Pi with a screen and the
  vehicle's OBD-II port (trips, fuel use, engine codes). Details in his own data (`data/world_local_sources.md`).
- **Local research for Zac's area** is in his own data (`data/world_local_sources.md`, git-ignored, never committed):
  stores, yards, auctions and surplus to seed his watches when W1 is built.
- **Built 2026-11-15 (Opus):** the gate's learned pace (DEC-0171; no fixed cap, each kind paced by what Zac opens,
  uses or dismisses; this PC's saved cap set to 0) and **World Intelligence W1** (K-0236): watches, finds with their
  sources, the checked feeds, the World page (Home › Learning › World, `web/intel.html`), voice tools, a glasses card,
  the 10-minute job. Off until Zac turns it on. DEC-0172 (procurement) approved.
- **The Living System doctrine** (prompt 20) is approved (DEC-0173). Built: L1, the three invariant tests
  (`tests/test_living_system.py`), and L2, homeostasis (`core/homeostasis.py`: deferrable work waits while the PC is
  busy, offline, on low battery or nearly out of disk; a job failing three times in a row backs off; she says so each
  time). Next: L3 with W2; L4 grants **(Fable)**; L5 Fable's challenge review of `MIA_OS_LIVING_SYSTEM.md`.
- **Fable's review queue (DEC-0174: Fable reviews all Opus work; work it first in a Fable session):**
  1. a3c88483, the gate's learned pace (core/communication_gate.py);
  2. 8e237dd7, World Intelligence W1 (core/world_intel.py, world_sources.py, the worker thread, the actions);
  3. 11685d02, the Living System audit (docs/mia_os/MIA_OS_LIVING_SYSTEM.md): the doctrine's own L5;
  4. the homeostasis and invariant-tests commit (core/homeostasis.py, core/scheduler.py, tests/test_living_system.py);
  5. World Intelligence W2 and W1b (core/relevance.py, WorldBook.sync_own_watches, run_watches);
  6. the source loop (core/world_intel.source_stats, mute, the world.sources loop);
  7. Procurement P1 (core/requirements.py, requirement_actions.py, the plan.project hook, needs as anchors);
  8. Procurement P2 (core/product_specs.py, core/price_book.py, price actions and tools);
  9. Prompt 03, the application framework (docs/mia_os/MIA_OS_APPLICATION_*.md, DEC-0175 to DEC-0177);
  10. prompt 22's plan (docs/mia_os/MIA_OS_APPLICATION_REGISTRY.md, DEC-0178);
  11. M1, the Application Registry (core/app_registry.py, tools/app_manifests.py, apps/*/manifest.json, the schema);
  12. M2, her apps asked about (core/app_ecosystem.py, core/assistant_app_registry_actions.py, the Apps page section);
  13. M3, the app list from the manifests (core/web_surfaces._apps_from_manifests, tools/app_manifests._keep_hand_fields,
      the phone bundle in android-phone/app/build.gradle.kts).
  **All thirteen reviewed by Fable, 2026-11-15 (K-0245). What changed:**
  - 1 (the gate): opening a combined message now credits every kind it carried; "not for me" lowers a kind's pace
    instead of raising it (`passed_at`).
  - 2, 5, 6 (World Intelligence): a find's link is kept only when it's a web address, and `web/shell.js` refuses a
    script as a link on every page; the finds tool is listed as outside text (`tool_loop.OUTSIDE_TOOLS`: a guard, its answer isn't read back by the
    model in the same turn today);
    MIA's own watches look for a record's meaningful words, not "the ... by".
  - 3 (the Living System audit): section 14, four claims corrected, one missing invariant row named.
  - 4 (homeostasis, scheduler): no change needed.
  - 7 (needs): a changed quantity, ceiling or amount on hand is checked like a new one.
  - 8 (prices): measurements ("120VAC", "2X4X8") are never model numbers (unlike products were "identical");
    trip figures can't be zero or negative; a price's link is only a web address.
  - 9, 10 (Prompt 03, prompt 22's plan): decision headings marked approved; the security page's outside-text
    claim corrected.
  - 11 to 13 (the registry): the running check no longer rebuilds the PC's tool list on every Apps page load
    (it failed on the phone and a windowless runtime); comparing records with the code stays the tests' job.
  **Built 2026-11-15 (Fable): M4's first part** (K-0246): `core/grants.py` (the five tiers, `decide`, the
  watching-only `observe` called from `actions.run_as_tool`), every tool's and action kind's tier in its manifest
  (`capabilities.tiers`; 86 action kinds and 44 tools need the person's yes each time), the outside-text tag
  (`capabilities.outside`, checked against `tool_loop.OUTSIDE_TOOLS` and `grants.FRAMED_TOOLS`), store permissions
  (`stores.write:<name>`). **Second part, on Zac's yes to Q-31 (DEC-0156 approved; K-0247):** the check is
  enforced (`grants.require`, through `taught_skills.guard` and in `core/workflows.py`): a skill's step that changes
  records asks until the skill is learned, a learned one still asks to pay, send or delete, and a `never` tier is
  never a skill's step. Grants are a view, not a new store: learned skills and published workflows
  (`grants.standing`), listed on the Apps page (Manage apps) and by `list_grants`, taken back with
  `grant.take_back` (the skill practises again; the workflow is put away). No action or tool gives a grant.
  **Rule for new work:** anything MIA starts herself that changes a record calls `grants.require(kind, grants.MIA,
  granted=...)` first. Not declared yet:
  network and device permissions per app (40 engine files reach the network or a device; map each to its app with
  a test that fails on an unmapped one).
  New Opus work joins a fresh list below this line.
  14. M5, each app's status (core/app_ecosystem.statuses, _breakages, _recovered; the Apps page's chips);
  15. Prompt 04 (docs/mia_os/MIA_OS_SYSTEM_*.md and the twelve others, tools/requirements_matrix.py);
  16. prompt 24's plan (docs/mia_os/MIA_OS_APPEARANCE_ENGINE.md, DEC-0183, DEC-0184);
  17. appearance A2 (web/tokens.css tiers, web/themes.css glass, core/themes.clamp_tier, tools/css_colours.py);
  18. appearance A3 (core/appearance.py, web/shell.js attributes, the sheets' layout and effects rules, the tools);
  19. appearance A4 and DEC-0186 (the presets in core/themes.py, the frame glow, accent_problem's saturation, --win);
  20. appearance A5 (web/studio.js Your Look, core/appearance.picker, the Look settings, core/orb_state.py and its hooks);
  21. appearance A6 (web/*.css onto tokens, --on-accent, the green and amber buttons, the apps' colours in tokens.css, the three new tests);
  22. appearance A7's first part (core/theme_picture.py, core/theme_design.adjust, /api/themes/picture, the two tools, From a Picture);
  23. A7's ambient motion (display.ambient, core/homeostasis.easing_now, shell.js's ambient(), themes.css's .theme-ambient). Copilot, Claude, ChatGPT or Muse may check pieces independently.
  **Items 14 to 23 reviewed by Fable, 2026-11-16 (K-0261). What changed:**
  - 14 (app status), 16 to 21 (the appearance plan, A2 to A6), 23 (ambient motion): read against the code; no change
    needed. Checked on the way: the desktop's browser engine (Chromium 140) has `color-mix()`, which A6 leans on.
  - 15 (Prompt 04): its handoff to Prompt 05 still said the greenhouse is "never commanded" (DEC-0185 changed that)
    and called DEC-0179 to DEC-0182 proposed (approved); corrected. Sampled "Exists" claims hold.
  - 18 and 22 (glass readability): the check that text reads on every glass tier ran only in tests on the built-in
    themes; `build_theme` now refuses a saved, imported, designed or picture-made glass theme that fails it.
  - 22 (a theme from a picture): only PNG, JPEG and WebP are decoded (Pillow's other decoders include ones that run
    outside programs); the pixel cap is checked from the file's header instead of changing Pillow's own limit for
    every other user of it; "make it warmer" alone no longer reaches the theme (it may be about the heat): every
    phrase of `adjust_theme` names the theme, the colours or the look.
  - Left as it is, for Zac if he cares: a pure vivid yellow accent (hue near 60) passes the meaning-colour check,
    though "yellow" by name is refused; DEC-0184 (the appearance engine) is built but still marked proposed.
  New Opus work joins a fresh list below this line.
  24. the MIA OS proofs of concept kit (os/, .github/workflows/mia-os-poc.yml, .containerignore) and the
      sound-server fix in core/voice_manager.py;
  25. Opus's review of prompt 23 (the review's section 14) and UI-1 (core/runs.py, the browser routine and skill
      hooks, actions.ActionType.rejected, Agent Activity's Running column, whats_running);
  26. UI-3's first part (core/change_history.py, UndoLog.add/forget, undo_last's mark, history.undo and the
      undo_by_time tool, Recent Changes' Undo By Time);
  27. DEC-0196's one browser (core/browser.py EVERYDAY_DROPS, _page and take_over, withheld/asked_now,
      sensitive_sites; the three tools; the two settings); and the VM workflow (.github/workflows/mia-os-vm.yml);
  28. UI-3's second part (core/action_effects.py, ActionCenter.propose's sentence, as_dict, lab.approve's tier,
      tests/test_action_effects.py).
  **Items 24 to 28 reviewed by Fable, 2026-11-16 (K-0268). What changed:**
  - 27 (one browser): while she's being taught, only the tab she's taught in is recorded (the everyday browser's
    recorder runs in his other tabs too), and what he does on a private site is kept only as "you do this part".
  - 26 (the lasting history): a tool's arguments are left out of the history when the tool's or the argument's name
    looks secret (password, PIN, key, card, vault, wallet); "undo by time" checks the yes in code, against the
    exact list she said in the last five minutes, so a confirm that skips the list gets the list.
  - 25 (the run record): a run book rebuilt in the same process (a store reload) no longer marks live runs as cut
    off; only the first load in a process recovers.
  - 24 (the proofs of concept kit, the sound fix) and 28 (reach and reversibility): no change needed.
  New Opus work joins a fresh list below this line.
- **Built 2026-11-15 (Opus): World Intelligence W2 and W1b** (K-0238): finds ranked by his own goals, projects,
  missions, the homestead plan's next step, learning paths and equipment, with the record named; MIA's own watches,
  one per open record, matched on the PC (nothing sent). Added to Fable's queue (item 5).
- **Zac reviewed Prompt 03 (2026-11-15):** DEC-0175 approved as the direction of his handoff (prompt 22, kept
  verbatim): MIA owns her app ecosystem, one manifest per app, an Application Registry, MIA Forge. Planned in
  `docs/mia_os/MIA_OS_APPLICATION_REGISTRY.md` (phases M1–M8); DEC-0178 (JSON manifests in apps/<id>/, code moved app by
  app later) approved (Q-30: yes). DEC-0176 approved; DEC-0177 approved with his clarification (MIA-native apps by the runtime,
  never Flatpak; conventional apps by Flatpak). No app store. **Prompt 04: Opus, on Zac's go.**
- **Built 2026-11-15 (Opus): M1, the Application Registry** (K-0242): one `apps/<id>/manifest.json` per app (56, plus
  `apps/mia/` for the platform), generated from code; `core/app_registry.py` reads them and checks every tool, action
  kind, store, job and daily check is claimed exactly once. Adding one now means claiming it in its app's manifest
  (`python -m tools.app_manifests check`). Nothing changes behaviour yet.
- **Built 2026-11-15 (Opus): M2** (K-0243): "what apps do I have?", "what can Greenhouse do?", "which app can
  monitor energy?", "is anything wrong with my apps?" answered from the manifests and the scheduler; the same on the
  Apps page (Manage apps: "Her apps, checked"). Overlapping tools are said as suggestions.
- **Prompt 24 (Zac, 2026-11-15): visual identity and the appearance engine**, kept verbatim in
  `docs/mia_os/prompts/24_VISUAL_IDENTITY_GLASSMORPHISM_APPEARANCE_ENGINE.md`. Phase 1 done (Opus):
  `docs/mia_os/MIA_OS_APPEARANCE_ENGINE.md`. Most of it extends what exists (`core/themes.py`, the Theme Studio,
  `web/tokens.css`, `web/themes.css`); three gaps to build: five glass surface tiers, theme / colour scheme /
  layout as three settings, the orb's state from real activity. DEC-0183 (glass identity, direction approved by
  his handoff), DEC-0184 proposed. **Zac answered:** Aquatic is the default, based on his reference picture (kept in
  `docs/design/reference/`, its palette read in code: APPEARANCE_ENGINE §I); Claude builds, Muse refines.

- **Built 2026-11-16 (Opus): appearance phase A2** (K-0253): the five glass surface tiers as tokens
  (`web/tokens.css`), the glass material drawn from them (`web/themes.css`), clamped per tier in `core/themes.py`
  (`TIER_RANGES`: a dialog can't go below 0.8 opacity), chart and gradient tokens, a hard-coded-colour baseline
  that may only fall (`tools/css_colours.py`, `work/css_colour_baseline.json`). Stark unchanged.
- **Built 2026-11-16 (Opus): appearance phase A3** (K-0254): `core/appearance.py` composes the theme, a colour
  scheme (`display.scheme`: cyan, turquoise, violet, champagne, ice, rose, or the theme's own) and a layout
  (`display.layout`: compact or comfortable; sidebar full or icons only) plus effects (auto, full, light, none) and
  reduced transparency, each independent; `readability_problems` checks text on every glass tier at 4.5:1; voice:
  `set_color_scheme`, `set_layout`. A gold accent is refused (it reads as amber or a reward): **Q-41** for Zac.

- **Built 2026-11-16 (Opus): appearance phase A4** (K-0255): Aquatic (the default now, from his picture), Nebula,
  Evergreen, Aurelia, Glacial, Eclipse as glass themes; a frame glow around the window; the gold scheme. Q-41
  answered (DEC-0186): soft gold accents allowed, rewards legendary orange (his follow-up). **Muse refines the presets' values (Q-38).**

- **Built 2026-11-16 (Opus): appearance A7, first part** (K-0259): a theme from a picture (Appearance › From a
  Picture, or "a theme from my ocean painting"; colours read in code, a meaning colour never the accent) and
  "make it darker / warmer / calmer" for the theme in use (`adjust_theme`). Then ambient motion (K-0260): a
  slow drift of the colours' glow behind the pages, off unless chosen (Appearance › Background, or "moving
  background"), held still when hidden, on battery, with reduced motion or light glass, or while MIA eases off.
  **Zac, on the phone:** turn it on and check it stays smooth and still on battery. A7's rest belongs to later
  prompts (the Plasma scheme, Prompt 10; spatial rooms, the Nexus).
- **Built 2026-11-16 (Opus): appearance phase A6, the literal colours** (K-0257): every style sheet but the glasses
  page draws every colour from a token (203 hard-coded down to 40, all the glasses page's own token block); pages
  compared pixel by pixel before and after (identical but for the brand orb's centre, the reward orb's centre and the
  Label page's Print button, now the theme's green). Q-42 / DEC-0187, each app's atmosphere
  colour (rose, cream gold, indigo, olive, plum, steel; none a meaning colour): **approved and built the same day**
  (DEC-0187). Next: A7 (advanced customization).
- **Built 2026-11-16 (Opus): appearance phase A5** (K-0256): the Appearance page (`web/studio.html`, "Your look":
  theme tiles, colour swatches, spacing, sidebar, glass effects, reduced transparency; point to preview, choose to
  save), the five look settings per person in Settings too (A3 had saved them device-wide by mistake: fixed), and
  the orb's states from real activity (`core/orb_state.py` via the live stream). Not done: "speaking" (answers
  aren't streamed yet). Next: A6, apps onto the shared system app by app (literal colours out, atmosphere hues). Fable reviews it (queue item 16).
- **Prompt 04 done (2026-11-15, Opus):** the requirements and system philosophy, sixteen documents in
  `docs/mia_os/` (start at `MIA_OS_SYSTEM_PHILOSOPHY.md` and `MIA_OS_SYSTEM_REQUIREMENTS.md`). 194 requirements,
  each with priority, release tier, status against the code, verification and owner prompt; the matrix is generated
  (`python -m tools.requirements_matrix`) and tested. Measured on the PC: models and engine timings (in
  `MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md`). **Zac answered (2026-11-15):** DEC-0179, 0180, 0182 approved; DEC-0181 approved with the stop as specified
  (AUTONOMY §4, Q-40); DEC-0185: MIA may adjust the greenhouse's controllers, and a stop never touches the
  greenhouse (REQ-FUN-103, R1: the node's command interface and limits first, against its simulator); the multi-user list marked not planned (Q-36).
  **Prompt 05 is Fable's** (DEC-0166); run it in the next Fable session with prompt 23's review. Fable reviews Prompt 04 (queue item 15).
- **Prompt 23 (Zac, 2026-11-15): Universal Intelligence and intent-driven computing**, kept verbatim in
  `docs/mia_os/prompts/23_UNIVERSAL_INTELLIGENCE_INTENT_DRIVEN_COMPUTING.md`. Its own order: **Fable's
  architectural review first** (feature inventory, existing-capability mapping, gaps, the five domains, each
  feature classed Existing / Extend / Build / Integrate / Defer / Reject), then Opus's independent engineering
  review; no implementation before its deliverables. Much of it already exists in part (the UAL, taught skills,
  links, the life-event history, undo, the gate, the inbox, search, Forge in prompt 22); the review should start
  from those. Run it in a Fable session; where it sits against Prompt 04 is Zac's call.
- **Built 2026-11-15 (Opus): M5** (K-0248): every app has a status now (working, needs attention, failing,
  missing something it needs, hidden, retired) with why, from its record, its jobs, the Fix-It Log's unfixed
  breakages of its tools, pages and actions this week, and its stores that had to be reset. Shown as a chip on
  its card and row on the Apps page; "is the Greenhouse app working?" answers it. Next in the plan: M6, per-app
  packages (Fable), M7 Forge (Opus, Fable reviews).
- **Built 2026-11-15 (Opus): M3** (K-0244): the app list is read from the manifests; a new app is a new
  `apps/<id>/manifest.json`. **The phone app needs rebuilding** to carry the manifests (its bundle now includes them;
  the installed one still has the old list in its code, so it keeps working until then). M4 is built (below); next:
  M5, lifecycle status (Opus) can go first if Zac prefers.
- **Prompt 03 done (2026-11-15, Opus):** `docs/mia_os/MIA_OS_APPLICATION_FRAMEWORK.md` and sixteen supporting
  documents. Capability-first; DEC-0175 to 0177 proposed; waiting on Zac: Q-27 to Q-29, then Prompt 04. Added to
  Fable's review queue (item 9). Prompt 04 is Opus's.
- **Prompt 21** (Living System completeness, kept verbatim in `docs/mia_os/prompts/21_LIVING_SYSTEM_COMPLETENESS.md`) is
  **scheduled after Prompt 17, on Fable** (Zac, 2026-11-15): it assumes Prompts 03–17 are done, and only 00–02 are.
  Its five deliverables build on 03–17's documents and on `MIA_OS_LIVING_SYSTEM.md`.
- **Built 2026-11-15 (Opus): the source loop** (K-0239) and **Procurement P1** (K-0240): each project's needs, from
  plans and his words, marked off against the workshop and inventory, on the World page's Needs tab and by voice;
  open needs rank finds and get MIA's own watches. **Built after it: P2** (K-0241): specs compared by numbers, prices
  remembered and judged against what's been seen, total cost. **Next (Opus), Zac's order:** Prompt 03 (the MIA OS
  sequence resumes); then P3.
- **Was next, now done:** W2, relevance from his records (projects and their material lists, intents, the
  development engine's needs, inventory, budget, places); W1b, watches MIA makes herself from those records; then
  P1 (requirements per project), W3 (eBay's and GSA's APIs wait for keys Zac skipped; capture and browser skills
  first). **(Fable)** later: W4 grants, the unattended browser review. On Q-16's yes, W1 starts with the gate's learned pacing **(Opus)**.
- **Skipped for now (Zac, 2026-11-15):** the Pi. **Next Fable items:** the phone on the full MIA, the window as a
  client (both need a Fable session).

**New 2026-11-15, MIA OS now (Zac, DEC-0168).**
- **Zac wants MIA OS as soon as possible**, on the PC (dual boot beside Windows) and on a Raspberry Pi 5 with the AI
  HAT+ and other devices, worked on from a Claude Code session on the Pi. The Pi starts the Zeta Astralis (a wrist
  computer and phone), a later project.
- **The runtime extraction (DEC-0155, approved), (Fable).** The plan is
  `docs/mia_os/preliminary/MIA_OS_INITIAL_IMPLEMENTATION_PLAN.md`. Where it stands:
  - **Done, steps 1 to 3:** the ten timers and 43 daily checks are out of the desktop window's class, in
    `core/background_jobs.py` (no Qt), on `core/scheduler.py`. The desktop runs them through one timer; nothing
    else changed for you. `tests/test_background_jobs.py` pins both lists.
  - **Done, step 4:** `python -m core.runtime` runs the whole MIA with no window: 95 services, the same 401 tools
    as the desktop, the schedule on a thread, the phone server when it's on. One function builds her for both
    (`core/runtime.build_services`); the tools are `core/assistant_tools.py`. `/api/runtime/health` reports it.
  - **Done, step 6 (Linux half), not yet run on a real machine:** `deploy/mia-runtime.service` and
    `deploy/install_runtime.sh` (a systemd user service). First real test: the Pi.
  - **Next, in order:**
    1. **Done: a data folder outside the code.** One setting, the environment variable `MIA_HOME`
       (`core/data_root.py`); all 131 files that named the data folder follow it. Not set (the PC today): nothing
       moves. `python -m tools.move_home <folder>` copies a MIA to a new home, checks every file, and never touches
       the old folder. The Linux service installer sets `MIA_HOME` to `~/.local/share/mia`.
    1b. **Done 2026-11-15 (built, not yet run on a real Linux machine): sealed files on Linux** (DEC-0169,
       proposed: Zac to approve the choice). The data key is wrapped under an unlock secret that systemd keeps for
       this user on this machine, with the TPM where there is one (`core/key_unlock.py`; `at_rest` entries say how
       they're protected, and each system keeps the other's). `python -m tools.data_key protect` makes the secret
       (the installer runs it and names it in the unit); `restore` takes the PC's recovery key (asked for, not
       shown); the runtime exits with 3 rather than start over sealed files it can't open. K-0235.
       **First run on Fedora or the Pi must check:** `systemd-creds --user encrypt/decrypt` and
       `LoadCredentialEncrypted=` in a user unit (systemd 256+), then `python -m tools.data_key` says "protected by
       secret". Moving the PC's data: `tools.move_home <folder> --sealed-ok`, then on Linux `protect`, `restore`.
       Not built: a passphrase typed at each start (stronger on a Pi with no TPM; waits on Zac, DEC-0169).
       Zac: keep the recovery key now (`.venv\Scripts\python -m tools.data_key recovery`, run inside the MIA folder).
    2. **The phone runs the full MIA too**: `android-phone/.../mia_phone.py` still uses the smaller
       `core/core_runtime.build_core_context`; fold the two builders into one. **(Fable)**
    3. **The window as a client** (step 5): the desktop window (and the MIA OS session, a browser on her web
       screens) attaches to a running runtime instead of building its own MIA. **(Fable)**
    4. Then the images: `os/Containerfile` for the PC (Fedora bootc), and the Pi's setup on Raspberry Pi OS.
  - **On the Pi, when the Claude Code session there is connected:** clone, make the venv, install requirements,
    `bash deploy/install_runtime.sh`, then `systemctl --user status mia-runtime`. The Qt packages aren't needed
    for the runtime (it imports none of them), which a requirements split should make real.
- **Stopped:** new features in the Qt desktop app and Windows-only parts (fixes only). The rest of UAL U3 (Convert, the
  consent step) waits until after the extraction.
- **Answered by Zac:** Raspberry Pi OS on the Pi, Fedora on the PC, the app on stock Android (Q-15).

**New 2026-11-15, very last (Claude).**
- **UAL U2 is built: "MIA" on any selection on the phone** (`SelectionActivity.kt`, `web/selection.html`). To try,
  after installing the next phone build:
  1. In Chrome (or any app), select some text. Tap the ⋮ in the selection menu if MIA isn't shown at once, then **MIA**.
  2. A card opens over Chrome. Pick **Find What I Know About This** (a result at once) or **Make This A Mission**
     (asks first, then Undo).
  3. Or share a link or text and pick **Do with MIA**.
- **UAL U3, first part, is built**: Explain, Summarise, Translate, Explain This Code, Pull Out Tasks And Dates,
  Draft An Email (a draft to copy; nothing saved or sent). They use the device's own model.
- **UAL U3, second part, is built**: Learn This Myself (a path draft, on a yes) and Build A Skill For MIA (steps from
  her own tools offered as Teach It To MIA, or else Build It In The Lab).
- **UAL U3, third part, is built**: Research This and Verify These Claims, offered only once Settings › "Let selections
  search the web" is on. They need SearXNG on the PC (`docs/ONLINE_LOOKUP.md`). Not checked yet: on the phone, the engine address
  (`online.searxng_url`) defaults to the phone itself, so it likely needs the PC's home-network address to work there.
- Left in U3: Convert (to a note, table, list or document) **(Opus)**, and the consent step before a selection reaches
  an outside AI (the council) **(Fable)**: security work.

**New 2026-11-15, last (Claude).**
- **Taught skills, phase 1, is built** (DEC-0123, `core/taught_skills.py`, K-0227). To try on the PC:
  1. In the chat: "watch me: the evening close". Ask her for two or three things. Then "that's it".
  2. "Run the evening close". Say yes to each step. Do it twice: the second clean run makes it learned.
  3. AI Tools › Taught Skills shows the steps, and which ones ask every time.
- **Next for the skills system** (DEC-0167), in order:
  - UAL U2, the phone's text-selection menu: **(Opus)**.
  - UAL U3, the first action set, with "Build A Skill" ending in a taught skill, and the consent step for anything leaving the device: **(Opus)**.
  - Taught skills phase 2: a schedule or an event starts a learned skill; browser steps; her offering after a repeat; the loop over failed runs (`work/loop_coverage.json`, `store:taught_skills`): **(Fable)** for the unattended gate, **(Opus)** for the rest.

**New 2026-11-15, latest (Claude).**
- The **Universal Action Layer** (DEC-0165) has a spec (`docs/specs/UNIVERSAL_ACTION_LAYER.md`) and a plan (`docs/mia_os/MIA_OS_UNIVERSAL_ACTION_LAYER_PLAN.md`). Its phases wait for Zac (Q-11 to Q-14).
- **Model per task** (DEC-0166, `docs/mia_os/MIA_OS_MODEL_ASSIGNMENTS.md`). The queue, marked:
  - MIA OS Prompt 03, the application framework: **(Opus)**, on Zac's go.
  - UAL U1, registry and offer: **built 2026-11-15** (`core/ual.py`, K-0226); was **(Fable)**, approved by Zac (Q-11 yes, 2026-11-15; system-wide scope, Q-14); U2 and U3: **(Opus)**. Q-12 answered B + C; Q-13 answered yes, as one skills system (DEC-0167). Next after U1: the taught-skills engine, phase 1 **(Fable)**, before U3's "Build a skill".
  - The runtime extraction (DEC-0155), once approved: **(Fable)**.
  - The test-isolation fix (the at-rest key reset): **(Opus)**.
  - Smart Closet stage 2 and LEP stage 1: **(Opus)**.

**New 2026-11-15, later (Claude).**
- **Prompt 02 is done**; Prompt 03 waits for Zac's say-so.
- **Smart Closet is built.** Its next stages are in `docs/specs/SMART_CLOSET.md`: the morning card, laundry flow, collage previews, packing lists, the partner's closet, the learning loop.
- **Zac's step, the phone signing key.** Until he does this, builds use the legacy key.
  1. On the PC, create a key: `keytool -genkeypair -v -keystore mia-signing.keystore -alias mia -keyalg RSA -keysize 4096 -validity 10000`. `keytool` comes with Android Studio's JDK. Choose a strong password.
  2. Keep the file and the password somewhere safe, outside the repo.
  3. Copy the key as text: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("mia-signing.keystore")) | Set-Clipboard`.
  4. On GitHub, under Settings › Secrets and variables › Actions, add `MIA_SIGNING_KEYSTORE_B64` (the pasted text) and `MIA_SIGNING_PASSWORD`.
  5. **Before reinstalling:** sync the phone with the PC. The phone app keeps its own data, and uninstalling deletes it.
  6. Then uninstall the old app, install the next build, sign in, link, and sync.
- **After the secrets are in:** remove the legacy fallback and `android-phone/legacy-signing.keystore` (DEC-0160).
- **Waiting on Zac:**
  - Q-08: may LEP go online in the background, and from which sources?
  - Q-09: are LEP interests private per partner?
  - Q-10: should Send to MIA start on the phone first?

**New 2026-11-15 (Claude: MIA OS).**
- Zac's MIA OS prompt library is in `docs/mia_os/prompts/` (00 to 17, plus 17b). Work it **one prompt at a time, and stop for Zac's review after each**.
- Prompt 01 (the existing-system audit) is done: start at `docs/mia_os/MIA_OS_MASTER_PLAN.md`. Prompt 02 starts only on Zac's say-so.
- Open from the audit:
  - the questions in `docs/mia_os/MIA_OS_OPEN_QUESTIONS.md` (Q-01 to Q-07, PC checks P-01 to P-05);
  - a release-signing finding reported to Zac privately on 2026-11-15 (not written here: the repo is public);
  - the test-isolation leak: `tests/test_id_wallet.py` resets the at-rest key with `use_key(None)`, and later sealing tests fail on Linux. It's a test fix and still to do.
- Setting up a cloud container for the full suite:
  1. `pip install -U --ignore-installed wheel setuptools`;
  2. `pip install -r requirements.txt`, run with `/usr/bin/python3` (3.13);
  3. `apt-get install libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 libportaudio2 libglib2.0-0`.

**New 2026-11-11, latest (Claude, after Zac's "lets build it"; Trade Master moved to Home › Learning).** Built and pushed:
- **The Dashboard's DEC-0153 cards:**
  - Today and **Your Week** tabs;
  - **weather**: Open-Meteo; you name your town once on the card or by voice ("my town is ..."), `core/weather.py`;
  - **the mission in play** with its next objective;
  - **Agent Activity**: her changes, what she held back, what she made, and for the owner the Council and the dev log (`core/agent_activity.py`).
- **Businesses**:
  - `businesses.html`: a card per business from Money's entities and their tagged money;
  - `biz.html?id=`: each business's own dashboard with its Orders & Quotes section;
  - orders and quotes carry their business.
- **Upkeep as scheduled missions** (`core/upkeep_missions.py`): one mission per due upkeep this week, attached to its asset, Done either way.

Two things found on the way:
- an accepted quote never kept its order (fixed, K-0222);
- a test of mine wrote ten test missions into the PC's real `data/missions.json`. I removed them the same minute by their `upkeep:` keys; nothing else under `data/` changed (K-0224).

**Next:**
- Health's meals widget.
- The Muse handoff (the destinations' pictures, the world portals' art).
- Zac's look at Toolbox, Trade Master, the Lab and Field Kit (WAITING_ON 0j).
- Tagging existing orders and quotes to their business (Businesses shows a link while any aren't).

**New 2026-11-11, later (Claude).** Zac approved the architecture and answered its questions (DEC-0153 holds his answers). **Built and pushed:**
- the eight destinations and their subdashboards in `core/web_areas.py`, each item with one owner, enforced by a test;
- hubs, the sidebar, the Apps page and the phone's bottom bar;
- MIA opening on the Dashboard;
- voice ("open the homestead");
- the glasses' three screens (orb, menu, Nexus);
- the Nexus as Living Worlds (a portal per story, opened from Living Worlds in Recreation);
- Portal Pictures on stories;
- the camera app shown as Cameras.

K-0218, K-0219.

**Next, in order:**
1. **The Dashboard** (step 3):
   - a **Your Week** tab: what's due this week, from the same due items as Today;
   - **Agent Activity**: her own changes, screens she made, messages she held back, plus the Council and the Development board's latest;
   - **weather** online (Zac said yes; Open-Meteo, no account; the place from the region setting; the life state's `weather` stops being PLANNED);
   - the active mission by name with its next objective.
2. **Upkeep as scheduled missions** (his decision). Home upkeep and asset maintenance become scheduled missions, each attached to its property or asset (`Mission.project_id`'s pattern, a ref through `core/links.py`), shown in the Calendar and on Your Week. Read `core/maintenance_manager.py` and `core/missions` first: a maintenance task already has a schedule, so the likely shape is the task stays the record and its due occurrence becomes a mission, never a second copy. Plan it before building; it touches stores.
3. **Businesses** (his decision):
   - the Businesses subdashboard with a quick view per `BusinessEntity` (income and expenses from tagged transactions);
   - a dashboard per business;
   - orders and quotes per business (`core/business_book.py` gains a business field).
4. Health's meals widget.
5. A handoff to Muse for the destinations' pictures and the world portals' art.

**New 2026-11-11 (Claude, engine session on the PC).** Zac decided MIA's navigation: eight destinations (Dashboard, Home, Garage, Finances, Health + Fitness, AI Tools, Missions, Settings) with subdashboards, one owner per feature, and the Nexus only for Living Worlds; the glasses get three screens (orb, menu, Nexus). DEC-0153, his spec `docs/specs/NAVIGATION.md`. Stages 1 to 3 are written as `docs/NAVIGATION_ARCHITECTURE.md`: the audit, the hierarchy, every app id and page to one owner, the hard cases, and a seven-step migration that keeps every id, route and store (`core/web_areas.py` gains `parent` and `shortcuts`, old area ids alias to the new ones). **Next:** nothing moves until Zac reviews it and answers its section 4; then step 1 (registry, hubs, sidebar, the single-owner test). Muse will need a handoff for the destinations' pictures and the world portals.

**New 2026-11-10, night (Claude, engine session on the PC: Zac's four messages on conversation, music and two specs, and his note that MIA should feel like one intelligence, not a collection).** All pushed. **Built:** a window no longer flashes open and shut on the PC (MIA's own daily documentation check ran git with a window; `tests/test_no_flashing_windows.py` guards every program she starts; K-0207). The Browser page explains how to teach her a task. Good News Radio is a station on its page (play, read the stories, follow one). **How she talks** (`docs/specs/CONVERSATION.md` is Zac's spec, `docs/CONVERSATION_REVIEW.md` the findings): asked about herself she answers from her own records (`core/self_knowledge.py`: the app registry, decisions, commits, her files), not from whichever help page shared a word; a chat can be copied, exported and summarised. **Music** keeps playing from page to page and with the Music app closed (`web/player.js`, one player for every page: MIA plays in the desktop window, the phone's player in the phone app, the page in a plain browser; a small bar on every page; K-0215 to K-0217). **Written for Zac, nothing built:** `docs/CONVERSATION_MODE_PLAN.md` (the phone-call mode his spec `docs/specs/CONVERSATION_MODE.md` asks for: what the voice code does now, what carries over, six stages, five decisions) and `docs/ORGANIZATION_REVIEW.md` (every app measured; sixteen portals proposed as eight rooms, one page that is MIA, the machine under Settings; seven decisions, two of which reverse DEC-0129 and DEC-0130). **Saved to build later:** `docs/specs/SELF_ORGANIZATION.md` (she tends her own organization and dashboards; extend `core/web_areas.py` and Made By MIA, no second registry). **Next, in order:** (1) whatever Zac decides on the two documents; if he approves conversation mode, stage 0 is measuring ten spoken turns on the PC with the real model. (2) The conversation review's five proposals (its section 8). (3) The four screens that are mostly displays for voice-only actions: Money, Garage, Memories, People. **Not tried by hand** (Zac's list in WAITING_ON): music across pages on the PC and the phone, the chat's Summary with the real model, Save to Files, the glasses' answer about herself. **Don't forget:** `core/llm_manager.py` and the model-check files were left alone on purpose; conversation mode needs a streamed call there and that waits for Zac's yes.

**New 2026-11-10, evening (Claude: the roadmap's tier 2 and 3, on Zac's "please continue").** Pushed, CI green: (2.3) the server lets go of its lock while the model thinks (`core/store_lock.py`: a StoreLock that knows its holder, `released()` around each model call in `LLMManager._ask`, a per-conversation lock so one conversation's turns stay in order); (2.4) that lock lives on `AppContext` (`context.store_lock`), the desktop's ten timers run their ticks under it or skip (never wait), and `core/instance_lock.py` lets one MIA run per data folder (a second says so and quits); (2.7) `web/shell.js` redraws once more for a change that arrives mid-redraw and holds a live redraw while the person types; (2.8) `tools/page_check.py` opens every page in headless Edge in CI, and `tests/test_turn_harness.py` runs turns through the real engine with a scripted model; (2.9) the phone's libraries are pinned and a `phone-libraries` CI job runs the server's tests on them (Python 3.13, FastAPI 0.99.1, pure-Python pydantic 1); (3.4) an exception that ends a thread is logged; (3.5) pages show loading, offline and failed states with the existing styles. **Left on purpose** (reasons in the audit's roadmap): the sync tie-break, streaming replies, route-shape tests. **Waiting on Zac:** 1.1, 2.1 (measuring a larger model runs over his records), 2.5 (a quiet window), 2.6, 2.10, 2.11, 3.7. Not yet: the Qt screens' own edits don't take the store lock; the glasses' guitar check can't run on the phone (no numpy). A session's suite run while MIA itself is running on this PC sees the guard fire on her own writes (activity, browser profile, config): that's the app, not a test.

**New 2026-11-10, later (Claude, engine session on the PC: tier 1 of the audit's roadmap, on Zac's goal "work towards fixing these issues").** Done and pushed: (1.2) the file writer keeps `.<name>.prev` before a large shrink and retries a busy replace; (1.3) a backup every night after 2 a.m. (`core/auto_backup.py`, 7 nights + 4 weeklies, hand-made ones never removed) and a restore from Settings that is checked now and applied at the next start (`backup_manager.schedule_restore` / `apply_pending_restore`); (1.4) only tools offered this turn run, `check_off_grocery_item` counts as a change, a change asked for right after web text or the inbox is said back instead of run, and Talk's `?ask=` sends only from MIA's own pages; (1.5) linked phones are listed and unlinked on Sign-ins and Security, and sign out everywhere or a password change unlinks them; (1.6) sync re-reads a file under the lock after the computer answers. (1.7) The suite's run is clean on this PC, and in a fresh checkout the guard found the greenhouse tests running ssh-keygen into the real `data/.keys` and a `maintenance_documents/` folder at the top; fixed, and CI now names failed tests (and the guard's finding) as annotations on the run's page, since its log needs a sign-in. **The Windows CI is green again** (`a1c334ba`, the first since 2026-11-07). **For every session:** regenerate `docs/ATLAS.md` and `work/doc_baseline.json` from a clean clone of your commit (K-0202), because on this PC other sessions' uncommitted files get counted. **Left:** 1.1 is Zac's (public or private); 1.6's tie-break rule; 3.7's small hardening items; tier 2 onward waits for Zac's approval (architecture).

**New 2026-11-10 (Claude, engine session on the PC: the system-wide audit Zac asked for). Nothing in the repository was changed.** Eight investigations plus an independent reviewer, every finding re-checked in the code. The audit, a five-tier roadmap and the security detail are on Zac's PC in `audit/` (kept out of git by `.git/info/exclude`, so a cloud session will not see them), **waiting on Zac: no roadmap item starts without his approval, and no major architectural change either.** What any session should know now: (1) this repository is public, though `CLAUDE.md` says private, so never commit a description of a weak point, and there is no auto-push hook (push after each commit); (2) the suite's 6,178 tests pass but the run is not clean: `tests/conftest.py`'s guard reports writes into the real `data/` (from `tests/test_glasses.py`'s every-panel test, which runs a real inspection, and `tests/test_at_rest.py`, which leaves `MagicMock/` folders); (3) the Windows CI's test step has failed on every run since 2026-11-07 (first red `7f6ba40e`), cause not yet read from its log. The first roadmap steps, once approved, are small: guards in the one file writer, a nightly backup, and a clean test run.

**New 2026-11-09 (design session, unattended, Zac's /goal "every screen of MIA built out, glasses, PC and phone"):**
the screens audit found these missing and built them, each with its actions, tests, demo data and a glasses panel
where it fits, all pushed: **Trade Master** (`web/trades.html` in Home, `core/web_trades.py`; glasses Workshop → The
Job moves it along, `trade.*` in GLASSES_KINDS), **How Your Good Runs Go** (DEC-0148, on the Operating Journal;
glasses Good Runs), **Waiting for the Internet** (the online reminders, on Notifications; `online.remind`,
`online.forget`), **Tracks** (GPX walks, rides and drives, `web/tracks.html` in Recreation; `track.add`,
`track.delete`; glasses Maps → Tracks), voice for **look it up online**, **what isn't working**, and **past
conversations** (`core/assistant_screen_tools.py`), the Dungeon's **shift differentials and tips**
(`run_loot`, `dungeon.tips`), and Real Estate **selling** (`property.list_sale`, `property.sell`, a Sold section;
a sold property leaves equity), Home's spoken briefing (**Hear It**, `core/web_surfaces.briefing`), and on the
glasses Practice (Classroom: a path's next step and a chord's shape) and Start a Job (Workshop, `trade.start`).
Glasses lines with no mark now split at a word. All 99 pages pass the demo sweep on
desktop and phone. K-0156 to K-0162. **Sensors** (core/sensors.py, the Sensors page): any device on the home network sends readings to the Lab, Power
or the Greenhouse with its own key (shown once, hashed, can only log to its series); DEC-0150's greenhouse node can
use it. The **Character portrait** is a crest MIA paints from your two strongest stats when you press Paint My Crest (never
a person; core/art_studio "crest"). The inbox falls back when the budget lacks `include_uncounted`, and the tool
reference is regenerated. **Passwords autofill** on the phone: MIA is an Android autofill service (`MiaAutofillService.kt`,
`AutofillActivity.kt`, `core/password_autofill.py`), checked on every phone build's emulator (registered and taken as
the phone's autofill service, a fitting login listed without its password, a look-alike refused, 423 when locked);
**Zac:** turn it on in Android Settings → Passwords and
autofill → Autofill service → MIA, and try a sign-in. No app is partial in the capability list now. **Sight through the glasses' camera** (the last parity todo): "what am I looking at?" said
through the glasses takes one photo with their own camera (`GlassesCamera.kt`, mwdat-camera 1.0.1) and asks Sight;
builds and passes the emulator check, untried on the real glasses (Settings → Glasses → Let MIA Use the Glasses' Camera).
**Loose ends from a full cloud run
(2026-11-09):** besides the cloud's usual stand-in failures (FastAPI StopIteration, Qt mocks, libzim, astral, PDF
readers), `core/inbox_manager.py` called `budget.all_expenses(include_uncounted=True)`, which this repo's
`BudgetManager` doesn't take (the PC's uncommitted budget work, left alone): the inbox now falls back to
`all_expenses()` when the option isn't there, so the receipt tests pass; and `test_life_events`' and `test_living_worlds`' sealed-store tests pass alone but fail
after some other test in a full run (a data key left behind by an earlier test).

**New 2026-11-08 (engine session's unattended run, 09:42 to evening): what's built, and what's next.** Built, core
only, all pushed: the deep What's Next (DEC-0144, every chain); T-0020 repository inspection plus the weekly docs
audit; T-0021 the shared development history (`core/dev_history.py`, `data/dev/history`, every commit); T-0022
disagreements (`core/disagreements.py`); T-0023 the evolution timeline (`core/dev_evolution.py`); T-0025 the lab's
method traces (checked against a real headless Claude Code run); T-0017's core (`core/online_lookup.py`); the Fix-It
Log sealed at rest (DEC-0126), then the history sealed a line at a time, the fix report and the kept seasons
sealed, `tools.data_key seal --history`; creations, art and the world map in the history (no details); What's
Next never re-suggesting what's on hand, and checking the food rules before a food stand. CURRENT_STATE has the
summary; knowledge K-0139 to K-0153. **For the parity session:**
voice tools for online lookup (`online_lookup.search` / `said`, offer line `OFFER`), "what isn't working?"
(`capabilities.status_summary`). **For the design session:** `/api/dev` `disagreements` and `evolution` (shapes in
section 2's engine claims). **For the next engine session:** `life_events.jsonl` is now sealed a line at a time
(DEC-0126 note): a scan found sealed stores' names copied into the plain history, so it closed a gap in an approved
decision; appends only, never rewritten; lines from before today stay plain (Zac's call in WAITING_ON). Anything
reading the history must go through `at_rest.open_text` (tests too). The fix report is sealed too: read it with
`python -m tools.fix_report`. When the phone gets its Keystore sealing, its sync base copies (`data/.sync/`,
`SyncState.set_base`) hold each synced file's opened content and must be sealed with it. What's Next, still open: a
fresh start in spring gets "build a compost bin" rather than a raised bed (a bed missed in spring costs a season); a
"now or wait a year" bonus was tried and reverted (K-0153: strong enough to fix it, it beat jars ready to sell).
T-0052 (create_app's length) only when no one else is in
`server/app.py`; T-0017 stays open for its voice tool and Zac's SearXNG. **Zac:** start SearXNG (WAITING_ON), the
history's older lines (seal them or not), the homestead push, DEC-0147's choices, the iOS path, restart MIA.

**Built (engine, 2026-11-09 night, uncommitted until Claude can commit: WAITING_ON item 0): Trade Master's whole first list** (49 of 49, DEC-0149): the workshop circuit, the root cellar, the hoop-house and cold-room calculators and plans, and every home-building job from site layout through gutters, plus the furnace diagnosis. A second tier of 20 (everyday jobs and breakdowns: clogged drain, leaky faucet, GFCI that won't reset, frozen pipe...) is written as well (69 of 69). Next depth for Trade Master: a person confirming the drafted jobs, and a third tier when Zac names the ground (outbuildings, well and septic, solar...).

**Built (engine, 2026-11-08 evening): DEC-0150, the aquaponics greenhouse built with MIA and handed to her**
(approved). The homestead merge (DEC-0145) is committed on local master with this work on top; **the push was held
by the session's safety check, so it waits for Zac** (`git push origin master` in C:\Users\zacrh\MIA, or a
permission rule). Then remove the worktree C:\Users\zacrh\MIA-merge-homestead (`git worktree remove`) and the
`homestead-merge` branch. Built: the setup sequence (`core/greenhouse_setup.py`: "let's set up the greenhouse", "what's next?" across
build, PlatformIO, flash, controls, Pi, card, push, start, take-over, commission), the three aquaponics jobs,
`homestead/viewer/serve_exports.py`,
`core/greenhouse_link.py`, `core/greenhouse_provision.py`, the `greenhouse.reporting` loop. Next: the SMTP secret
pushed from the vault, the live link (DEC-0150 answer 3c), and for the design session a Greenhouse screen (monitors,
alerts, "take over", the flash and push steps). Zac also
asked for the Trade Master walkthrough screen (2026-11-08, "let's build those"): **for the design session**, as
noted below; the six starter diagnoses are built.

**Built by the engine session (2026-11-08 evening), core only: DEC-0149 Trade Master (approved).** Next on
`core/trades.WANTED` (the `trades.depth` loop opens a task for it): `workshop_circuit` (the workshop's wiring, a
permit and the electrical stop rule), then `root_cellar`, the greenhouse and cold-room calculators in
`core/build_calcs.py`, then all of home building in order. Every job must pass `trades.problems()`. For the design
session: the Trade Master screen is **built** (claude, design, 2026-11-09): `web/trades.html` in Home (`core/web_trades.py`,
`/api/trades`): the library by trade, a job or diagnosis opened whole with Start It and Make It a Mission, and the
walkthrough (the step large, why, watch for, the hold, the phases, Checked / Next Step / Back / Stop, Yes / No for a
diagnosis); on the glasses, the Workshop card's "The Job" panel moves it along (`trade.*` in `GLASSES_KINDS`). For the
parity session: voice is code-done for the walkthrough itself; a model tool to start one by a vaguer phrase is open.
`core/trades.py` (jobs as sourced data, stop rules in code, the quality standard), `core/job_session.py` (step by step,
hold points), a job as a mission, diagnosis sessions, the Carpentry apprentice program, a specialist per trade, the
`trades.depth` loop, and the first builds: greenhouse, coop, workshop, cold storage. Screens are the design
session's; voice tools beyond the session's own phrases are the parity session's.

**Built by the engine session (2026-11-08 evening), core only: DEC-0148 Natural Momentum (approved).** For the
design session: **built** (claude, design, 2026-11-09): How Your Good Runs Go on the Operating Journal
(`core/momentum.picture`, the counts, or how many runs of the three she waits for; "you're on a run" while in flow),
and Good Runs on the glasses' Operating Journal card. Never a score. For the parity session: "I did X" is code-done already
(`core/did_it.py`), so no tool is needed for it; the gate topic is `momentum`.
`core/did_it.py` ("I did X": recorded, counted toward a routine, offered toward a task or mission objective or as a
new routine), `core/momentum.py` (windows, chains, flow, one easy start, tomorrow's prep), the gate's flow guard.
Screens stay the design session's, voice routing beyond these code-done phrases the parity session's.

**⏸ New 2026-11-08 (night): homestead merged into MIA, waiting on Zac's push OK (DEC-0145).** `mia-homestead` is
subtree-merged as `homestead/` with all 94 commits, byte-identical to GitHub, on branch `homestead-merge` in the
worktree `C:\Users\zacrh\MIA-merge-homestead` (+ `pytest.ini`, `testpaths = tests`, so the two `core` packages never
collide; CLAUDE.md section). The safety check held back pushing another repo's history onto master without Zac's
explicit yes. On his yes: `git merge homestead-merge`, push, remove the worktree, then update
`core/homestead_manager.py`'s docstring (still names the sibling repo) and regenerate the atlas. Its scenarios: 242 of
245 on Windows (the 3 are rsync).

**New 2026-11-08 (night): the Development Intelligence Engine, Phase 1 (DEC-0144, approved).** `core/development_engine.py`:
a development profile from real state, compounding-value scoring, `next_step`; homestead catalog; the
Zero-to-Something benchmark is `tests/test_development_engine.py`. Next: "what should I do next on the homestead?"
as a tool and a screen control, then Phase 2 (development edges on `links.py`, real homestead state once merged).

**New 2026-11-08 (night): connections (DEC-0146).** "The magic is in the connections": `core/connections.py` ties a
remark to an open project, goal, mission or set-aside idea at least a week old (through the link graph, or a shared
word), holds it 2h, raises it once in the everyday conversation if it fits; loops `connections.landed` and
`connections.unlinked` (kind pairs her graph doesn't connect yet, opens a task). Next: research before raising one,
and a "don't bring that up" tool + screen control.

**New 2026-11-08 (night): she knows her specialties.** `capabilities.specialty_list()` + the `get_specialties` tool
("what are you trained for?"): aquaponics greenhouse scientist and manager (grow lab, and MIA Homestead once merged),
her specialists, Night School and its aim, teacher, builder, homestead planner, experimenter, game master, model
maker, browser, painter, each read from its module, left out if missing.

**New 2026-11-08 (overnight, design session, Zac asleep): screens for everything decided.** Built, each with its
actions, voice tools, demo data and tests: **My Directions** (web/directions.html, DEC-0141/0143: directions, today's
seed, one thing within reach), **How MIA Answers** and Talk's **"this one or this one?"** (web/answers.html,
core/answer_compare.py, DEC-0138: the model rephrases her own reply, code checks no number changed; at most once a day,
never private), **Living Worlds Phase 1** (web/worlds.html, DEC-0134: now a personal store; play waits on Phase 2),
**About MIA** (web/about.html, DEC-0142), **Connections** with "don't bring that up" (web/connections.html, DEC-0146),
**Trail Maps** (web/trails.html) and the chat page's **History** (past conversations: read, pick back up, delete),
the Theme Studio's **Mix Two**, **sound sets** and the **glasses taking the theme accent** (DEC-0136), the
Greenhouse's **What's Next** in the canvas look (DEC-0144), the flat Nexus showing Muse's portal pictures, the room
lowering its resolution when slow (NEXUS_PLAN M4), the chosen portal's rim held back off its picture (H-0099), two
stale tests fixed (Good News freshness by the episode's day; Talk's mic test), and 65 test helpers documented.
Every page passed the demo-mode error sweep (95 pages). K-0120 to K-0126. Later the same night: every other
area became a **room of its apps** in the Spatial look (Nexus M5's first pass, core/web_environments.room), **compound
maintenance triggers** on the task form (DEC-0131), and the canvas's Built page gained **Built: New Overnight** (ten
phone shots of tonight's screens, above New Tonight). Still later (2026-11-08 morning, Zac asleep): **Portal Pictures**
(web/portals.html, core/portal_pictures.py, DEC-0140: your own painting in any area's Nexus portal, "paint a misty
forest for the Plants portal", `portal.picture`, `set_portal_picture`; the Nexus card's "Change its picture"),
**playing Living Worlds** (DEC-0134 Phase 2: The Story So Far and "What do you do?" on web/worlds.html, `world.turn`,
`play_world_turn`, the story from the engine's `turns_in`), **Connections' "What She Found First"** (the engine's
research, on the page and by voice), and every remaining test helper documented except the budget and Plaid files
(waiting on Zac's Plaid work). K-0137, K-0138. All 96 pages pass the demo sweep on desktop and phone, none wider than
the phone. Evening (Zac back, "build out the glasses screens"): **every app has a glasses card** but Passwords and Look
(core/glasses_cards.py; DEC-0125 note), plus What's Next, Your Campaign, My Directions and Connections on existing
cards; demo data in docs/schema/glasses*.example.json regenerated from each screen's own demo. Afternoon (Zac still away), screens for each engine piece as it landed: the Greenhouse's **What's Next**
shows "step 1 of N on the way to…", the whole path and the checks behind it, and where the budget came from;
**About MIA** shows how her apps are doing on this device (DEC-0057; Diagnostics' and Settings' stale "no web screen
yet" limits corrected); **Diagnostics** shows her own repository's findings (T-0020); the **development board** shows
open disagreements (T-0022, "your call" in amber) and her evolution timeline (T-0023); **Look It Up Online**
(web/lookup.html, DEC-0053/T-0017; no "Say:" line until the parity session's voice tool exists). K-0148.

**New 2026-11-08 (latest): capability reminders — "did you know you could go do X right now?" (DEC-0143).** Zac asked
for MIA to remind him, now and then, of what he's already capable of doing right now — a subtle, affirming redirect
that meets him where he is and gets him on track, never a new task or a value to live up to. `core/capability_reminders.py`
wraps a real, right-now ability in a warm, low-pressure frame; the daily check (`_check_capability_reminder`) gathers
the ability from live state — a learning path he's a step from advancing (`core/paths.py`), a project he started and
parked (`core/project_manager.py`). Empty in, empty out (never fires without a true thing behind it); paced every few
days through the gate (topic "capability", auto-covered by `checks.dismissed`). Tested (`tests/test_capability_reminders.py`,
5). Sample: *"Did you know you could put some time into Guitar right now? You're on stage 2, Chords — the next step is
ready when you are."* Both this and the whimsy seeds are logged under **DEC-0143**. More sources to add later as his
life fills in (a skill with the tools owned, a buildable project with materials on the shelf, an asset enabling a
trip). It leans on `paths`/`projects` being populated, so it'll feel richer once he fills MIA.

**New 2026-11-08 (late evening): whimsy seeds — MIA inspires the slow, made life.** Zac asked (twice, warmly) for MIA
to inspire the whimsy and artsy in his life — slowness, drawing, making, forest creatures, dreaming — alongside his
consumer→producer shift. `core/whimsy.py` turns his standing directions (DEC-0141) into a concrete little **seed** he
can act on today, composed from real facts (the season, what's on the workshop shelf via `core/material_manager.py`,
his directions in his own words) — never improvised, nothing personal hard-coded. The direction nudge
(`core/application.py._check_direction_nudge`) now prefers a seed over the plain canned line, still paced by the
communication gate. Tested (`tests/test_whimsy.py`, 6). Sample autumn seeds read like: *"Ten quiet minutes with a
pencil — sketch the falling leaves out the window, no plan, just the line."* / *"You've got walnut scrap on the shelf
— what little thing wants to be made from it this week?"* It only fires for directions he actually set. Extends
DEC-0141; no new decision needed. **Also closed this session:** the loop-coverage + generated-catalog debt from the
self-knowledge/Living-Worlds/directions builds (LOOPS.md, EVENTS.md, ATLAS.md, doc_baseline.json, loop_coverage.json
all current; `check:system_map`, `store:direction`, `store:response_style` decided). **Note:** two tests fail on
master that are the design session's, not core — `test_good_news` and `test_web_home_voice` (both expect strings in
`web/shell.js` / good-news the web frame hasn't got yet). Left for that session.


**⏸ RESUME HERE (2026-11-08, saved mid-thread): MIA's device fabric.** The live thread when Zac paused was his wish
for MIA to recognize, talk to, secure, and install herself onto his technology. Written up as **DEC-0128**
(`docs/DEVICE_FABRIC_PROPOSAL.md`), awaiting his approval (WAITING_ON → "MIA across your technology"). Key reframe:
interop comes from protocols + credentials he holds, **not exploits** (the Echo proved it). On approval, the
read-only defensive half (network discovery → identify + CVEs → home-network audit → a Field Kit screen) can start
with no further decision; the offensive/active-testing half is gated to his own authorized devices (browser-commit
model). Also offered and not yet built: **panel mode** — a full-screen kiosk view of the web UI (clock, due items,
Talk) for a wall display, the Pi, or a cheap tablet. Everything from this session (security steps 2/5/6/8, Your Data,
the Echo verdict) is committed and pushed.

**New 2026-11-08: MIA's floating desktop orb (Zac's ask).** `gui/orb_presence.py` — a frameless, transparent,
always-on-top window that reuses the existing `PresenceWidget` orb (no new look invented), floating centred with a
gentle bob; drag to move, click (or Enter) wakes the main window. Opt-in boot via **`gui.boot_orb`** (default off):
when on, the PC opens on just the orb and rings, no window/border. Wired in `core/application.py._show_main_window`
(guarded, kiosk-exempt), tested (`tests/test_orb_presence.py`). This is the *desktop* orb (Qt); it's distinct from
the design session's *web* Nexus orb (DEC-0130) — I reused their `PresenceWidget` visual, didn't make a new one. To
turn it on: set `gui.boot_orb` true in config and restart MIA.

*Earlier: 2026-11-07 (afternoon)*

**New 2026-11-07 (latest): Start Here, a grouped sidebar, the live browser, and the audit.** Start Here
(web/start.html, core/web_guide.py: a test keeps its phrases routed to tools); the sidebar grouped by life area;
her browser lives inside MIA (hidden Edge, live frames on the Browser page, the person clicks and types on the picture,
teaching records it; `browser.own_window` for the old window). The audit (Claude Doc
https://claude.ai/artifact/56xyaTxEQThT1vrYh484Ay) proposed seven areas; **superseded by DEC-0129** (Zac, 2026-11-08):
the Dashboard and fifteen areas with hub screens, built in core/web_areas.py. Real use so far
is light (33 messages, most apps never opened): the organization is the priority.

**New 2026-11-07 (late night): the desktop opens on the web (DEC-0124); only Zac's words go out of the browser
(DEC-0122); taught procedures proposed (DEC-0123).** The window's web mode (`gui/main_window.py` set_web_mode,
`gui.web_first`): web front end edge to edge, classic Qt screens by Ctrl+Shift+C or for PC-only apps (the web Apps
page's "Open on this PC", a `/desktop-open/<id>` link the web view catches). Checked off-screen with the real
modules; not yet seen on Zac's screen. Phone app 145 installed on his phone by adb (built locally with
GITHUB_RUN_NUMBER=145, one above CI's 144).

**New 2026-11-07 (night): the Browser page and HTML e-receipts.** `web/browser.html` (core/web_browser.py): what her
browser is on, held steps with screenshots (Go ahead / Cancel on the step's own proposal), taught tasks with Do it /
Forget (`browser.run_task`, `browser.forget_task`). Emailed HTML receipts now keep each item on its own line
(core/document_text.py), so their pantry and materials effects work.

**New 2026-11-07 (night): the phone keeps your place.** The app is "MIA" with no title bar (theme NoActionBar); it
reopens the last page (MainActivity.remember / lastPlace, SharedPreferences, never the token), and every page keeps
its scroll, an open Talk and its draft for 12 hours (web/shell.js keepPlace / backToPlace, localStorage). Checked in
Edge with Playwright; not yet on the real phone.

**New 2026-11-07 (night): receipts that do things (DEC-0120), filed on their own with exact Undo (DEC-0121).** The inbox's email intake reads Zac's everyday
mailbox read-only, taking only receipts and orders (`core/inbox_mail.fetch_receipts`); a receipt proposes what it
means (`core/receipt_effects.py`: pantry and grocery list, a service done on the vehicle, workshop materials), done on
filing. Next: Zac's first real receipts (store formats will need tuning), the web Inbox's email setup (desktop only
today), and order emails from online stores (Amazon lines rarely parse as receipt lines).

**New 2026-11-07 (late): more projects, the design brief, MIA for Zac alone (DEC-0119).** Calculators for a chicken
coop and run, garage shelving, a bookshelf, a lean-to, a compost bin, a cold frame, a picnic table, a firewood rack
and deck stairs, each a built-in plan with steps, and `cut_list` for any project of his own parts (boards and 4x8
sheets). The Claude Design brief, "MIA: Screens and Flows for Claude Design", is a Claude Doc
(https://claude.ai/artifact/3R3ZjAWg4JzV1yE6dXK515): every screen, the frame, flows, states, round-one order.
DEC-0119: MIA is for Zac alone, never children; whether to remove the old child-account code is his call (WAITING_ON).

**New 2026-11-07 (evening): humor and plans (DEC-0118).** Humor: `core.personality.humor_for` (light turns, by
chance, a random flavor) and each person's level by chat (`set_humor`). Plans: the Library's plans shelf
(`core/plan_library.py`, tools in `core/assistant_plan_actions.py`, the Knowledge page's Plans section), material and
cut lists worked out in `core/build_calcs.py`. Next for it: more calculators as Zac names them (chicken coop, lean-to,
shelving, stairs), reading the text of dropped-in plan PDFs (OCR is in `core/ocr.py`), and a size form on the web.

**New 2026-11-07: MIA's browser (DEC-0117, `docs/BROWSER.md`).** Edge through Playwright in her own profile per
person; every step is sorted in code (`core/browser_safety.py`); commits wait as `browser.commit` for the person's
OK (screen or a coded yes); secrets never typed; tasks taught by showing (`core/browser_routines.py`), learned after
two clean runs (`browser.runs` loop). Tests: `tests/test_browser.py` (a pretend Edge); smoke-tested on real Edge.
Next for it: Zac's first real try (WAITING_ON), a web screen listing taught tasks and their runs, and a routing
corpus check that "open the website" reaches `browse`.

**Canvas build (DEC-0113 approved 2026-11-07; the design canvas "MIA Core Screens" is the reference, H-0092).**
Build order and where it stands (tick as each lands; screenshots in demo mode: serve a folder with `web/` and
`schema/` -> `docs/schema/` and open `/web/<page>?demo`):
- [x] Shared pieces: `web/ui.css` (orb states, finding, kind tags, status strip, focus surface, big action, states,
      What I used), app accents in `web/tokens.css` (`--atmo` from `<body data-app>`: Workout, Kitchen, Workshop).
- [x] Home: date, greeting, status strip, MIA Noticed (core/findings.py), focus rows with their kind, Upcoming beside
      it, MIA's column on wide screens. Engine: `dashboard()` gained `strip`, `finding`, each row's `kind`/`tone`.
- [x] Talk: her orb and state in the header (Ready, Listening, Thinking, Speaking, Can't Reach), What I used.
- [x] Sidebar: Home, Apps, Pinned (favorites), life areas folded (`shell()` gained `favorites`, `groups`, each app's
      `group`).
- [x] Workout: Today leads with one big Start; a live session takes the whole screen as Active (count large, how
      it was counted), Rest (draining ring) and Done (planned → done); tuck it away and a bar brings it back. Engine:
      `training_session.view()` gained each count's `how`, `last_counted`, `weight`, `rest_total`. "+30 s" on rest is done
      (`training.rest_more`: the button, "thirty more seconds" by voice, the glasses' panel). Progress has Week by Week
      bars (workouts and volume a week, `core/web_screens.weekly_training`).
- [x] Kitchen: Today leads with the next meal's Start Cooking; the recipe page has Start Cooking; cook mode
      (`web/cook.js`) takes the screen: one step large, what it uses, the step's own timer offered, named timers that
      keep running, Back / Next Step / I Made This. Engine: `core/cooking_session.py` (a personal store, `cooking`),
      `core/cooking_actions.py` (`cooking.start/next/back/go_to/timer/timer_cancel/made/stop`; made = `meal.cook`),
      `cooking` on the Kitchen and recipe reads. Cook mode by voice is done (`core/assistant_cooking_actions.py`:
      cook_start / cook_step / cook_timer / cook_finish, DEC-0125). Servings scaling is done (a − N + stepper; core scales
      each amount to kitchen fractions: `web_screens.scale_factor`, `units.kitchen_amount`). The glasses have a Cooking Now panel (`core/glasses._kitchen_cooking`: the step
      large, timers, Next / Back / the step's timer / Stop timer in one press, I Made This with a confirm).
- [~] Every other app: the shared frame now matches the canvas on every page (`web/ui.css`, "every app's frame"):
      status strips with the label above, a white value and an index bar; "needs you" amber instead of red fills
      (attention panels, overdue chips and rows; red stays for real errors); tabs as a rail lit from below. Checked
      in demo mode on 60 pages (no new script errors; presence.html's old error is the page to retire).
      Done per app: Missions (ready-to-complete focus card, next objective, XP, source), Freedom (each figure tagged
      Fact/Calculation/Missing by `core.freedom.figure_kind`), Skills (capability status and next honest step first),
      Money (net worth with "+$X this month" and its six-month line: `core/net_worth_history.py` keeps one point a
      day, noted when Money is read, so the line starts the day it ships and grows with use), Garage and the asset
      page (machine cards with meter and plain due words; Spent this year, condition, one Needs You card with a big
      Done, what it cost lately: `core/web_equipment.due_words`, `meter_reading`, `_upkeep_this_year`), the Dungeon
      (today's run card with gold projected loot and a big Run Cleared, the overtime boss card, the week's runs meter), Compliance (one panel per group, each obligation
      a row with the one step `core/web_compliance.next_step` says comes next), Insurance (You Have, then
      quotes side by side each with `core/insurance.verdict`'s sentence, and a big Draft A Quote Request), Real Estate (the property card: its word from `core/web_screens.property_badge`,
      Rent Due amber; Rent / Cash Flow / Equity in one row), Workshop (Builds first: the bench card with Budget / Spent /
      Hours and the next step, Sell First, Best Earner per hour, a big Start A Build), Orders (the stage rail New / Building / Ready / Delivered
      with the step `core/web_business.order_stage` says moves it on; owed amber, paid green), Inbox (each waiting item's "Goes to" line from `core/web_inbox.goes_to`),
      Calendar (one page: Due Today, Past Due, Due Soon as short lines, the month beside them on PC), Journal (Write Entry first, the privacy line, one column of entries with
      date and tags above the title), People (Birthdays first: a card each with gift ideas, then the one person
      `core/web_more.catch_up` says to catch up with), Classroom (the course to continue from
      `core/classroom_manager.continue_course`, lessons to tick with their XP, subjects as rows that open), Guitar and any learning path (`core/paths.path_card`: stage rail, the week, Work On Next
      with homework, every check of the stage with who verifies it), Memory Vault ("N of M safe at home" per month from
      `core/memory_vault.vault_page`, a green or amber dot on each photo), Operating Journal (a card per line with its meter from
      `core/operating_journal.line_score`), Play (six weeks of play minutes as bars, the latest games with
      `core/recreation.effort_word`, a big Log a Game), Observations (a card each: Needs You or Noticed, the
      apps it drew on, Open in <app>, from `core/observations_web.card`), Expeditions (the next one as one card:
      heads-up from `core/web_more._trip_heads_up`, packing to tick, Start Trip; the rest as rows),
      Maps (the route card under the map: from the first
      waypoint to the one picked, distance, bearing, sunrise and sunset; no climb until MIA has elevation). The map now fills the page as on the canvas: its name and kind float at the
      top, zoom / waypoints / keep-offline as buttons on the right, the route card along the bottom (vector areas: zoom
      and take-off buttons).
      Navigation (a compass with the needle on the bearing, waypoints with their grid, sun and moon tiles).
      World Map (km² cleared as the headline, the next achievement from `core/world_map.next_rank`, a big I'm Here).
      Knowledge (Search / Packs / Plans Shelf tabs; result cards with a snippet from
      `ReferenceLibraryManager.search_titles`; its test needs libzim, so run it on the PC).
      Music (song rows you tap to play, the one playing in cyan; a Now Playing bar held at the bottom).
      Files (the path, Upload, one list with line icons and a meta line, ⋯ for Rename and Delete).
      Passwords (one line per login; Show opens one card at the top with a countdown, Copy and Hide; ⋯ for the rest).
      News ("Three stories today", a card per story tagged by how it's known: `core/good_news.KNOWN_TAGS`).
      Look (the photo shown but not kept, the questions as chips, the answer with how she knows it, Take a Photo).
      Settings (a label over one card per group; each setting a row with its note and a switch; the demo now has
      `docs/schema/settings.example.json`).
      Profile (initial, name and email; About You rows that open their editors; Security; Sign Out; no household per
      DEC-0119; the demo now has `docs/schema/profile.example.json`).
      Fix-It (a big Report a Problem, Open · Worst First cards with ×N and the latest thing said, learned phrasings).
      Diagnostics (Passed / Look At / Unread tiles, a dotted row per check-up, Run Again).
      Chickens (Log Today's Eggs first: four big one-tap counts; This Week / Lay Rate / Feed per Dozen; two weeks of eggs
      with today lit; Cartons on Hand with Carton Them; feed, birds and the log below).
      Greenhouse (a Today tab first: Needs You with upkeep due and readings out of range, then each planting with
      its stage meter from `core/web_grow.growth_stage`, which goes by days planted and harvests, never a guessed date).
      Character (the portrait card with level, prestige and the XP meter; Stats as the six attributes with meters;
      Collection by rarity; Top Skills; buffs, the Chronicle and the rest below).
      Reward Shop (Earned / Spent / Left tiles; Ready to Buy with Buy; Saving Toward with a meter and credits to go;
      Edit and Delete under ⋯).
      Kept (a label per kind, a card per note with when, Done and Forget).
      Memories (On This Day card; a card per trip with Time / Distance / Pace, a journal line, places and photos).
      Security (a two-column wall of camera pictures, each with its state dot and name on the picture).
      Sunday Check-in (the week in a sentence, Runs / Loot / Quests, MIA Noticed, the week ahead a line a day,
      Debrief Done; the full week folds below).
      The Chronicle (the newest chapter as prose with its highlights as tags; Earlier Chapters to open).
      Apps (find always at hand, favorites as tiles labelled as your glasses cards too, then every app by life area
      as a list with its star; Manage stays one tap away).
      Sign In (her breathing orb, the wordmark, labelled boxes, one bright Sign In; recovery is on the PC).
      Recent Changes (new, from Settings: what MIA can put back with Undo as `undo.last`, and the fortnight's history).
      Notifications (new, from Settings: newest first, why MIA sent each one she sent on her own, Mark All Read,
      Dismiss; and by voice).
      Also: Diagnostics shows This PC (the hardware list) and Recent Problems from MIA's log ("any errors in your
      log?" by voice); Navigation can change a waypoint (`waypoint.edit`, change_waypoint); Power's History › opens a
      meter's chart in the Lab.
      Household (Done Today with its meter, a card per routine with its streak in words and Did It, paused ones
      apart; Add a Routine / Pause / Resume as `routine.add/pause/resume`, and by voice).
      Power has its web page (`core/web_power.py`, `/api/power`, `web/power.html`; energy sources and the battery),
      and readings can be logged by voice too (`log_energy_reading`, through `energy.reading`).
      Toolbox (`core/web_toolbox.py`: Ohm's law from any two, the unit converter, board feet, concrete volume,
      answered by core as you type at `/api/toolbox/calc`; alarms set / on-off / deleted as `alarm.*`; a stopwatch on
      the page. The math moved out of the Qt calculators into `core/toolbox_calcs.py` and `core/unit_conversion.py`).
      The Lab (`core/web_lab.py`: series chips, the chosen series' chart placed by core, latest/low/high/average/
      change, readings with Delete, Add a Reading as `lab_reading.*`; Power's and Garage's series read only).
      Field Kit (`core/web_field_kit.py`: Devices, Network (hash kind, subnet) and Scripts tabs, read only; eject,
      run and port scan stay on the PC). Voice gained calculate_board_feet, calculate_concrete, switch_alarm and
      delete_lab_reading. Every app now has a web page except Diagnostics (an owner page) and Settings.
      Later the same night (parity gaps closed, each with its tool and screen control, DEC-0125): Classroom lesson
      notes (`lesson.notes`; get_lesson_notes), Money's business tags (`expense.business`: each charge's business,
      "Which business?" for bank charges waiting, MIA's guess in amber), a trip's route and checkpoints
      (`core/trip_route.py`: stops from saved waypoints, Arrived, legs with distance, time and pace, out and back
      allowed; add_route_stop, log_arrival, get_trip_route; the glasses' On The Trail panel), the glance (the
      glasses' app tiles) gained net worth and Observations and Inbox tiles, a plan's page in Knowledge (your size, what to buy, `plan.keep` /
      `plan.project` / `plan.delete`; forget_plan), and the Toolbox's inventory (`inventory.*`). The canvas has a
      **Built** page: full-length screenshots of every built screen, row by row like the Phone page (retake them
      with the demo server and `builtshots.js`-style Playwright full-page shots when screens change).
      Still later: two new pages, **My Why** (`web/why.html`, from Profile: the why chain with reasons and facts,
      `why.link/unlink/achieve`) and **Projects** (`web/projects.html`, from the Workshop: builds with budget, spent,
      reason and tasks, `project.*`, `task.add/reopen/delete`); Classroom textbooks (Look Up inside them, Add a book,
      Make a course, Remove; remove_textbook) and a lesson's skill (`lesson.skill`, set_lesson_skill); Workshop
      listings (`listing.add/remove`; list_product, unlist_product); a receipt's items under its expense
      (get_receipt); a trip's log with its weather from the trip; Memories draws each trip's route map (placed in
      core); the Lab names an upkeep task's sensor readings and the asset page links to the chart; Settings offers
      starter sets (`starter.add`, one Undo). The Built page was retaken with a "New Tonight" row.
      Then: Settings has Backups (owner only, Back Up Now with an optional passphrase: `/api/backups`, never an
      action; get_backup_status) and MIA's Voice (owner only: the voice, AI effect, volume; `/api/settings/voice`;
      list_mia_voices, set_mia_voice); Knowledge can delete a pack (owner, name typed); the glasses gained panels for
      Workshop (Project Tasks, Done), Classroom (Continue, Done), and readouts for Observations, the Lab, Power, the
      Journal and Memories. The Built page's shots predate these Settings sections.
      Later: glasses readouts for Field Kit, Navigation and Maps too (every app with a glasses card has a panel);
      a page can name its own "Say" phrase (`<body data-say>`); the "still using it?" mark on subscriptions
      (DEC-0054, core/subscriptions.py: Still Using on Money's bills, by voice, a quiet finding; T-0018 done); the
      design review went onto the canvas as orange notes (DEVELOPMENT_PLAN step 4). Knowledge ids collided across
      the parallel sessions (seven pairs): renumbered, and tests/test_knowledge_ids.py now catches it.
      Last: Skills' "Show the tree" (drawn prerequisite lines, laid out in core/web_progress.skill_tree); pictures in
      Knowledge articles (`article_images`, `/api/knowledge/picture` serves images only); the Qt Toolbox's last two
      tools on the web: MIA's Idea on Missions (Discovery: Suggest One, Accept, Set Aside) and From the Field on the
      Journal (MIA Lite recordings: Keep It, Leave It Out, Check For New), with voice tools (core/web_proposals.py).
      Then search on the web: Ctrl+K or "/" on every page, or Search in the sidebar and the phone's bar (apps, then
      every kind of record through links.KINDS, core/web_search.py, then the library and Ask MIA). The skills tree
      shrinks to fit a phone and says when it scrolls. The Built page on the canvas has the three newest screens.
      Assets have photos (page and Garage card). **Fixed:** the security change (d795fb4) had overwritten the Grow Lab
      module `web/grow.js` with grow.html's redirect, so every asset page and the Greenhouse's Growing tab broke; the
      module is back and the redirect is `grow-redirect.js`. tests/test_web_scripts.py now catches that kind of overwrite.
      Properties have photos too. Parts per asset (core/asset_parts.py: stated links asset REQUIRES part, out/low
      first, page and voice) and a trend line on each of an asset's reading tiles (web_equipment.trend). Sign Out is
      no longer red (the standard keeps red for errors, overdue and destructive actions; a red Delete is right).
      **Full suite on the PC, 2026-11-08 00:08:** 5541 passed, 8 skipped, 2 failed, both from another session's
      uncommitted work on that PC (core/plaid_manager.py, core/budget_manager.py: transfers kept and marked instead
      of dropped, DEC-0042): the Plaid test still expects them dropped, and docs/ATLAS.md is stale. That session
      updates the test and rebuilds the atlas when it commits. Nothing committed tonight failed.
      **2026-11-08 night, with Zac:** DEC-0129 (areas and hubs: sidebar, Apps page, hub.html, Communications,
      Dashboard life cards, Pets page, Home Upkeep, Look in the chat, Health with sleep/visits/meds/records) and
      DEC-0135 (two looks per person: Spatial or Cards, by device by default; core/display_style.py). DEC-0136 (themes as data, core/themes.py; Theme Studio steps 1-4 built (studio.html: tweak, save, import/export, MIA designs one), still to come in docs/design/EXPERIENCES_AND_THEMES.md section 9: mixing two themes, sound sets, the glasses' accent). Portal art: Muse's batches 2-4 (H-0097). DEC-0140 (MIA paints): Zac to install ComfyUI and an SDXL model on the PC (docs/ART_ENGINE.md), then try "paint me a fantasy castle village for my background"; untested against the real engine (tested against a stand-in). DEC-0130 (the Nexus: docs/design/NEXUS_PLAN.md; now a real-time 3D room, web/nexus3d.js, waiting on Zac's look on the PC and Muse's portal pictures, H-0096; M1-M3 built, and the glasses' ring: a Nexus card opens the areas as a flat ring of names, each area's apps one select in. Next: Zac reviews the Garage environment and the ring on the real Display, then the other environments one at a time). The ID wallet is built (wallet.html in Security, core/id_wallet.py).
      **Maps' other scripts need Zac or a session with network:** place names in Cyrillic, Greek, Arabic and so on
      need more glyph ranges in `web/vendor/fonts/` (web/vendor/README.md says where from); the cloud shell here
      can't download them.
      **Git in the cloud clone:** it had no post-commit hook, so nothing was pushed for a while; it has one now
      (pushes the branch and master). A merge doesn't run it: push by hand after merging origin/master.
      Left on WEB_PARITY on purpose: voice/phone access/backup/updates in Settings (device config: an undo can't put
      back a running voice engine), Knowledge pack install/delete (deleting is for good), Modules device-wide,
      the Lab's live sensors (none connected), Maps' other scripts (glyphs to download), Home's spoken briefing
      (Zac: no quick buttons; "what's on today?" answers by voice), the private journal (passphrase on the PC), links.
- [x] Glasses (the canvas's GlassesHome and GlassesTraining): Home shows her state (Ready, Listening, Thinking,
      Needs You), the one line that matters now (`core/glasses.priority`, amber orb from `priority_tone`), the latest
      card for ten minutes, and a dot per card; gold once when something is earned. The live workout panel leads with
      `core/glasses.training_hero` (exercise, set and weight, one big number that's never a guess). Checked in demo
      mode; not yet on the real glasses.
- Note: DEC-0119 (MIA for Zac alone) came after the canvas: drop household members from Party's leaderboard and
  Profile's household card when those screens are built.

**What Zac and the other agents need to do is in `docs/WAITING_ON.md`** (kept current every session).

**Where the build plan stands (`docs/BUILD_PLAN.md`, 2026-11-07).** Phases A and C are done; most of D is built.

- **Phase A, the loops (done):** 60-odd loops in `core/loops.py` (daily; heavy ones weekly from Night School);
  the dev suite, reverts and dependency audit (`core/dev_checks.py`); corrections in every area
  (`core/corrections.py`); weekly benchmarks graded by code (`core/benchmarks.py`, `python -m tools.weekly_bench`);
  the standing mission M-0001 (paused until Zac starts it) and MIA's Sunday self-report. Loop coverage
  (`core/loop_coverage.py`): 229 of 257 processes covered (2026-11-06), 25 declined with a reason, 3 to do (Plaid),
  with its why; a test fails on a new process nobody decided how to watch. Every loop as built: `docs/LOOPS.md`
  (generated: after adding a loop, run `python -m core.loop_catalog`; a test checks it).
- **Night School (DEC-0100, `docs/NIGHT_SCHOOL.md`):** starts at 01:30 from MIA's daily check once MIA restarts
  with the new code (Zac sleeps in the morning: see WAITING_ON). First real full night run by hand 2026-11-07
  08:55: one lesson passed (phone_link, kept in the lab for Zac), two failed.
- **Phase B:** step 7 (the module contract) waits on the rest of Zac's Interconnection Architecture doc. Step 8
  (cross-domain) built: composed plans, `afford`, `slipped`, `projects`, `habits`, `priorities`, `resources`
  and, 2026-11-06, `recall`, `person`, `patterns`, `discussed`, `returns`, `time`, `held back` and `running costs` (the routing
  audit: 90 of 112 benchmark questions answered by a plan, 11 by tools, 10 by the model alone: research, how-to
  and open-ended coaching, where the model belongs; the benchmark with the model: 85 of 112 clean, from 60),
  sureness in every plan answer, calibration by ratings and by projected dates checked when they come.
- **Phase C (done):** capability gaps (`core/capability_gaps.py`), seasons of memory (`core/seasons.py`), the
  Operating Journal (`core/operating_journal.py`), recreation (`core/recreation.py`).
- **Phase D:** Good News Radio (on for Zac; `core/good_news.py`); maps and comms (MGRS, TAK package and
  local-network sharing, GPX tracks; `docs/MAPS_AND_COMMS.md`; mesh and vector maps next); sight on the PC
  (`core/sight.py`; the glasses' and phone's Look button is Kotlin work next); the council from the phone
  (`web/council.html`); the Chronicles' weekly issue (`core/chronicle_issue.py`; waits on Zac approving archive
  events; consistent characters need T-0036's bigger image model).
- **Phase E (done):** T-0040, T-0042, T-0044, T-0045. T-0041's rest waits on real use of MIA's creations.
- **DEC-0054 built (T-0018, 2026-11-06):** `core/life_notes.py` (promises, decisions, ideas, goals set aside,
  kept on "keep it", a dated promise mentioned the day before and on it, done or forgotten by voice) and the
  goods-before-market-day finding. Left: the "still using it?" mark on subscriptions (it touches
  `core/budget_manager.py`, which holds Zac's Plaid work in progress: after it lands) and a screen for the notes.
- **T-0010:** a rating said out loud works everywhere, the glasses included; a 👍/👎 on the glasses screen is
  Muse's, if Zac wants one.
- **Working web screens** (formatting only, the look is muse's): `web/operating.html`, `web/play.html`,
  `web/news.html`, `web/council.html`, and 2026-11-06 `web/kept.html`, `web/diagnostics.html` (owner only),
  `web/knowledge.html`, `web/classroom.html`, `web/household.html`, `web/navigation.html`,
  `web/observations.html`, `web/memories.html`, `web/maps.html` (the offline topo tiles, no map library; vector
  tiles later). Still desktop-only: the Pi-era Power, Toolbox, Lab and Field Kit (DEC-0015: the Pi is a later step). Check a new page's script with
  `C:\Users\zacrh\Android\node\node.exe --check web/<page>.js` (a syntax error leaves the page blank). To see a page render on this PC, use
  headless Edge (no Playwright here): `msedge --headless=new --window-size=600,900 --screenshot=x.png
  "file:///C:/Users/zacrh/MIA/web/<page>.html?demo=1"`.
- **Found by the loops, 2026-11-06:** T-0050 (fixed: git output read as UTF-8), T-0049 (fixed: `dev.lab` counted
  practice), T-0051 (the phone's old `cryptography`/`starlette`/`fastapi`: Zac chooses; Claude recommends keeping
  them for now with the exposure written down, then Android Keystore over time). `phone.vulnerable` audits the
  phone's packages weekly from its build.
- **Known flaky:** the reference library's (one cause fixed 2026-11-06: an open libzim handle on delete), a native
  Qt crash mid-suite (seen twice), and `test_inbox.py`'s reading-corrections test (once in a full run).
  The one failing test is Zac's uncommitted Plaid work (`test_import_transaction_transfer_is_skipped`).

**Next for Claude:** the glasses' own camera and the question by voice for Look (the phone's web view takes and
chooses photos now, 2026-11-06, built but untried on the phone), Meshtastic once radios exist, vector offline
maps, the same character across panels (T-0036: SDXL-Turbo is in, 2026-11-06; an IP-Adapter next), the module
contract once the doc arrives, and
DEC-0054's last piece (a "still using it?" mark on subscriptions, after Zac's Plaid work lands).

**Glasses navigation: `docs/GLASSES_NAVIGATION_PLAN.md` is a draft waiting on
Zac's five questions.** Recipes open by shelf; Music plays on the phone
(`Music.kt`) from the glasses and reads the phone's Music and Download folders
(`music.extra_folders`); neither tried on real hardware.

**First boot and User Sync (2026-11-02): slices 0-5 of
`docs/GLASSES_FIRST_BOOT_PLAN.md` are in.** User Sync has all seven topics,
the phone permission step and a phone screen (`web/sync.html`, linked from
Home). After it come the Know Your System mission, Home's tour, the app
menu and four app tours (`core/welcome.py`, `core/app_intro.py`). Next is
slice 6 (idle tips). Still to do: a weekly repeat for the meal-prep mission;
a birthday without a year gets no reminder. Glasses' Home, app menu and
Missions are in the boards' look, and everyday actions go through the relay
(DEC-0064): compiled, not yet tried on the real pair; `mia-art` needs
publishing with them. Zac, on the
phone: Home, Getting To Know You, try the Allow buttons and a topic or two.

**The development platform's MVP is built (DEC-0070, 2026-11-03):**
`python -m tools.work` (list, claim, run --as, review --as, approve, history),
and `web/dev.html` for the device's owner. Details and what's not yet proven:
`docs/DEV_ECOSYSTEM_AUDIT.md` section 13.

**Tasks now live in `work/tasks/` (DEC-0068, 2026-11-03):** `python -m
tools.work list --ready` shows what can start. The build queue below is
history; anything still open from it is a task.

**Parked, to come back to (Zac, 2026-11-03), in this order:**
1. Personality plan (DEC-0067), `docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md`
   sections E to G. Done: phase 1, tuning round 1, 👍/👎 ratings, turn traces.
   Next: **phase 3, the self-knowledge map** (needs Zac's go), and **GitHub
   Issues** (blocked: no GitHub login on this PC; sign `gh` in, or a cloud
   session sets it up). Later: rating on the glasses (relay + Claude Design's
   screen), a fine-tune from the ratings, shopping for models.
2. Glasses: install phone build 143 or newer (DEC-0066 screens, fixes from the
   fifth relay review); Zac's call on making the glasses' question buttons
   read-only (an email question puts stranger-written text into a Talk turn).
3. Restart MIA on the PC to hear the new voice.

**Personality phase 1 is in (DEC-0067, 2026-11-03):** results in
`docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md` section E. The glasses' answers come from
`core/response_composer.py`; restart MIA on the PC, and the phone needs a new build,
to hear it. Next: her manner (jokes, stiffness, closing offers), measured with
`python -m tools.conversation_check`.

**Pending on the glasses (2026-11-03):** phone build 142 (DEC-0066: every
designed screen, money included, offered question buttons) is built in
`android-phone/app/build/outputs/apk/debug/` but not installed: Zac's phone
wasn't plugged in. Plug in, `adb install -r` it, reopen MIA on the glasses.
The glasses page is already live. A security review of everything added since
the fourth one (DEC-0064 to 0066: actions, missions, music, questions, money)
found no High issue (2026-11-03). Fixed: a reference could be approved after it expired, and I Made This couldn't work. Build 143 has both; install it, not 142. Still open, Zac's call: the glasses' question buttons run full Talk turns that can change things, and 'Any emails I should answer?' brings stranger-written email into such a turn (make glasses Talk read-only?). Recipe photos and her
awakening voice need a way round the relay's size limit (H-0079).

**The glasses are here (2026-11-01).** Meta's DAT plugin is installed in
Claude Code on the PC (`mwdat-android`, DAT 1.0.1). It corrects MIA's
docs: through the phone app the toolkit offers Display (a native UI on
the glasses), a live camera stream and photos, Inputs, and experimental
Speech, Motion and audio, plus "Hey Meta, start MIA" (Voice Invocations);
MockDeviceKit tests without glasses. **DEC-0059 (Zac, 2026-11-01): the
glasses go through the phone app's toolkit; no Web App, no Funnel.** The
first-boot work in `web/glasses.*` is Claude Design's, still in progress:
leave it to that session.

**Toolkit in the phone app (2026-11-01):** `MetaGlasses.kt` connects from
Settings (Glasses, phone app only), opens a session on display-capable
glasses and draws `/api/glasses`: pinned apps, each app's panels, their
readouts, Back. **It runs on Zac's real glasses (2026-11-02).**
Read-only so far: actions, Inputs, voice and the orb come next. The
toolkit needs Android 10, so minSdk went 26 to 29; build tools are AGP
8.11.1, Kotlin 2.2.21, Chaquopy 17, compileSdk 36. The app's id and token
live in `android-phone/local.properties` (gitignored), never in the repo;
CI builds get "0" unless the workflow is given them as secrets. Developer Mode
with 0/0 stopped at DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED. What fixed it
(Meta's docs don't say): real id and token in the build, then in the
Developer Center the package and signature under Configuration, a version
built to Ready, that version on the Beta channel, and Zac invited to it.
A later signing key or package change needs a new version. Keep
versionCode above the phone's when installing a local build (set
GITHUB_RUN_NUMBER; last used 141, installed over USB on 2026-11-02). Her art is public in `TheKingCS/mia-art`
(DEC-0061, artwork only; `python -m tools.glasses_art <folder>` draws the orb).

**Superseded in part by DEC-0062/0063 (2026-11-02):** her face becomes a Web
App (test page live at thekingcs.github.io/mia-art, installed by QR; look,
icon, key through the install link, crypto and speech all passed on the real
glasses) joined to the phone by a sealed relay, not built yet. Her icon opens
her; a tap makes her listen. The relay is live and passes `relay/test.mjs`
(`docs/GLASSES_RELAY_PLAN.md`; deploy from `relay/` with Node in
`C:\Users\zacrh\Android\node`). Next: the page's and phone's encryption and
pairing, with fake data; nothing personal crosses until the plan's gate passes. The phone can't open a Web App. Still unknown:
camera while the Web App shows. The tap works through the glasses (she heard
Zac and answered there); her spoken answers there run long and should be short.

**Getting MIA on the glasses (2026-11-02):** opening the phone app connects
her; a drop retries four times; Close MIA on her Home stays closed. **A tap
on the glasses brings her back** (works, Zac tested): the glasses send
KEYCODE_MEDIA_PLAY over Bluetooth, and ListenService plays a moment of
silence to hold Android's media button. With her showing, the tap is Select.
While the listener runs, a tap can't start paused music (Zac is fine with
it; MIA will be his music app). Not yet tried with the phone in a pocket.
**"Hey Meta, start MIA" doesn't work:** Meta says "no device called MIA",
and on the phone the voice stream reaches STARTED then "Channel error
occurred" within 100 ms, every time. Next step is Meta support checking the
Voice Invocation permission, optional now: DEC-0060 makes the tap the way
in (Zac doesn't want to ask one AI to open his AI); the code stays.
Next: her look on the glasses, then approving actions. Local
build: `C:\Users\zacrh\Android\phone_build.ps1 assembleDebug`.

**Zac's call: qwen3:14b or stay on qwen2.5:14b** (both measured
2026-10-30: same speed, tool choice 212 vs 213 of 213, qwen3 reasons
more on open questions; `docs/INTELLIGENCE_BENCHMARK.md` section 2,
the answers in `pc-check/intelligence-*.md` on the PC).

**Inspection and self-knowledge (2026-10-30, DEC-0056/0057 approved):**
`core/inspection.py` built (the core, this computer, MIA herself; "inspect
this computer", "inspect yourself", "run a self-check"); assistant port
scans limited to the own network. **The development lab is built
(DEC-0058, approved):** `python -m tools.lab list / propose / approve /
reject` (`core/dev_lab.py`), "what proposals are waiting?". Plan and next
phases: `docs/INSPECTION_AND_SELF_PLAN.md`.

**Usage audit and the design brief (2026-10-30):** `docs/UI_AUDIT.md`
(web pages weren't counted anywhere; now every web screen counts its
opens in `data/page_usage.json`; re-run the audit in a few weeks) and
`docs/design/CLAUDE_DESIGN_PROMPT.md` (Zac pastes it into Claude Design).
Retire-after-checking: `finances.html`, `grow.html`, `presence.html`.

**Active Training (DEC-0055, approved): phases 1 and 2 built** (the live
workout session, voice controls, Count With Me on the Workout screen,
the glasses' Active Training card). Next for it: the phone app's native
count voice and workout-listening mode (an Android build), retiring the
Qt Workout module's old in-memory session; status in
`docs/ACTIVE_TRAINING_PLAN.md` section 9. Zac, at the PC: say "start my
workout" and try a set with Count With Me.

**Waiting on Zac: DEC-0053 (looking things up online, when asked) and
DEC-0054 (remembering commitments, decisions, ideas and dropped goals),
both PROPOSED in `docs/DECISIONS.md` with their open choices.** Built
since the last note: the desktop panels get the instant code answers
(`core.assistant_turn.instant_answer`), long conversations keep their
start (`earlier_topics`), what "it" means (`what_it_means`), and a second
try before a loop answer is thrown out for an unchecked number.

**2026-10-30 (later): built.** Step 1 (one owner per fact:
`core/fact_owners.py`), the question plans (`core/question_plans.py`, 15
plans, by meaning with `core/meaning.py` and nomic-embed-text, in every
chat surface), the debt payoff math (`core/debt_math.py`), `llm.num_ctx`.
Live on the PC: plan answers in 3 to 7 seconds. Zac: ask MIA the
benchmark questions in your own words and say which answers are off.
Then built the same day: the tool loop (`core/tool_loop.py`), findings
(`core/findings.py`: on Home, in a "noticed" plan, and the four kinds
Zac allowed unprompted through the gate) and conversation state's first
slice (`core/conversation_state.py`, follow-ups). Next: the rest of
conversation state (what "it" is on any turn, open questions, a running
summary), then propose outside research (benchmark F4-F6) and the data
MIA doesn't record yet (commitments, decisions, ideas, best-by dates,
subscription use) as their own decisions. Also try qwen3:14b on the
bench (`tools/pc_model_check.py`, research R7) before any switch. Note: the desktop's chat panels don't use
`run_assistant_turn` (no quick commands or direct lookups there); unify
them when conversation state is built.

**2026-10-30: DEC-0052 approved** (`docs/REASONING_PLAN.md`): one owner
per fact (step 1, next to build), answers that combine several lookups
(question plans from Zac's own list, then a tool loop with up to 60 s),
findings across apps, conversation state. Zac's Intelligence Benchmark
(112 questions) is `docs/INTELLIGENCE_BENCHMARK.md`: today 77 reach the
model with no tools at all (`python -m tools.bench_audit`). Build order:
step 1 (pay owned by the Dungeon), then the 15 question plans in its
section 4, then the tool loop. Outside research (F4-F6) and the data MIA
doesn't record yet (commitments, decisions, ideas) need their own
decisions (section 5).

**2026-10-29 (Claude on the PC): her voice, and how she describes herself.**
- Zac: restart MIA, listen to Kokoro's Heart (now your saved voice), and
  try the others in Settings → Voice (Emma, Bella, Nicole, Michael,
  George...). `voice.kokoro_speed` (default 1.0) sets her pace. Then
  check Home and Missions look right (the stretched-cards fix was tested
  offscreen only).
- A fresh install gets Kokoro from `deploy/finish_install.py` (about
  350 MB in `voice_models/kokoro/`) and `kokoro-onnx` from requirements.
- Next for the voice: the phone still speaks with Android's own voice
  (`android-phone/.../Voice.kt`); it could fetch Kokoro audio from the
  PC when linked. A custom voice just for MIA is a later step (DEC-0051).
- Loose ends seen on this PC: 15 tests fail on master here (not checked
  against CI): the inbox and textbook PDF tests when the full suite runs, OCR
  because Tesseract is installed, and presence's out-of-date "Due in 2
  days" expectation.

**Collaboration hub (2026-10-05):** the team shares memory through
`docs/COLLABORATION.md`, `CURRENT_STATE.md`, `DECISIONS.md`,
`QUESTIONS.md` and `HANDOFFS/`. Start there too.

**Engine Phase 1 (2026-10-05): approved and built.** Life events
(history), links (how things relate), Life State v2 and the read model
(`/api/state`, `python -m tools.export_state`, the published schema).
Details, acceptance results and the 10-question guardrail for new
proposals: `docs/ENGINE_PHASE1_PLAN.md` sections 8 and 9. For Muse (design): `docs/HANDOFFS/H-0003_claude-to-muse_where-mia-is.md`, with a placeholder sample state in `docs/schema/life_state.example.json`. Never put
real personal data (seed data) in the repo.

**Cognitive Extension:** you approved slices A → B → C → D → E
(`docs/COGNITIVE_EXTENSION_PROPOSAL.md`, "Decisions"). **Slice A
("Talk it out") is built:** conversation modes, journaling into an
encrypted Private Journal, off the record, and the safety floor. **Slices B ("Remember Why") and C
("Know when to speak") are built too.** D waits on your first real use
of the Android app.

**Claude on Zac's PC (2026-10-20).** Claude Code now runs on Zac's PC
(`claude remote-control` in `C:\Users\zacrh\MIA`, started at sign-in in
auto mode by `pc_remote_control.bat`; the PC signs in by itself after a
restart, 2026-10-20), next to the real MIA,
Ollama (qwen2.5:14b on the RX 7900 XTX) and the linked phone. On the PC:
`git pull` before starting, and commit and push after each piece (the
cloud sessions and Muse work from GitHub). Real data lives in `data\` and
`config\config.json`: gitignored, never committed, never pasted (DEC-0002).
**Top priority for the next PC session: Plaid, all cards linked (see the ⭐ section below).** First jobs, in order: (1) ~~the 14b's misses caught by MIA's own code~~
**done 2026-10-19: 213/213** (`settle_on_named_tool`, `core/assistant_chat.py`);
(2) a real
test of glasses voice, location quests while closed, the memory vault
and sync with the linked phone; (3) the voices (install.bat again);
(4) finishing modules without a web screen (`docs/WEB_PARITY.md`).

---

## ⭐ NEXT PC SESSION'S PRIORITY (Zac, 2026-10-21): every card and bank linked with Plaid

Zac wants MIA managing his finances: before anything else at the PC,
get all his cards and accounts connected through Plaid. Guide:
`docs/PLAID_SETUP.md`. State on 2026-10-21: Plaid isn't set up on the PC
yet (no `data\plaid_vault.enc`), and MIA's bank code has never talked
to Plaid for real.

**Zac, before you sit down:**
- [ ] A list of every bank and card company to link. The Trial plan
      allows **10 logins** (one login covering checking + savings + a
      card at the same bank counts once). Over 10? Pick the 10 that
      matter most, or ask Plaid about the next plan.
- [ ] Your phone nearby: banks send a verification code.
- [ ] Your Plaid dashboard login (Developers → Keys: client_id, the
      **Sandbox** secret and the **Production** secret). Never paste
      them into a chat.
- [ ] A vault passphrase saved in your password manager (MIA's
      Passwords app works) before you type it into MIA: it can't be
      recovered.

**The session, in order (Claude watches the logs and fixes as you go):**
1. `git pull`; open MIA → Budget → **Bank Sync**.
2. **A 10-minute sandbox test first** (Parts 3-4: Plaid's fake bank,
   `user_good` / `pass_good`). It costs no connections and catches any
   bug before a real login counts against the 10.
3. **Reset Plaid Setup** (clears the fake data), then **Set Up Plaid**
   with the **Production** secret (Part 6).
4. **Connect a Bank** for each login on the list; **Sync Now**.
5. Check with Claude: Expenses and Income categories, the Debts tab
   (APRs, minimums; add promo APR end dates by hand), nothing doubled
   on a second sync, the Summary's totals.
6. Then open **Freedom** (DEC-0038): with the bank synced it fills in by
   itself (spending, saved, the pace). Tag build spending to its build in
   Money so the builds count down. Then: bills, the budget, which debt
   to pay first, business tags for the homestead goods.

**Claude, at that session:** start here. Tail `logs\mia.log` while Zac
links; fix any failure before the next login (a failed login can still
use up a connection). Never read or print the vault, keys or access
tokens.

---

## 1. Your hands-on steps

- [ ] **Back at the PC (2026-11-04), in this order.** Restart MIA first so it loads everything new.
  1. **Approve T-0019**: `.venv\Scripts\python -m tools.work approve T-0019`, type T-0019 (about 4 minutes, two test runs; your settlement still counts).
  2. **Sign the reviewers in**: `codex login`, `gh auth login`, then `copilot` and `/login`. Until Codex is in, every task needs you to settle it (approve wants two providers).
  3. **The MIA Development window** (desktop shortcut): the board, the **Council** chat (`@mia` is free; `@claude`, `@codex`, `@qwen` use that one's allowance; `debate`, `discuss`, `budget 4`, `stop`), **Missions** (give one a goal and a scope; its tasks are `tools.work new "..." --source M-0001`; starting one spends your usage), **Voices** (play each member, keep one), **What the team learned** (confirm or withdraw MIA's notes), **The Chronicles** (106 candidates: keep, private or drop).
  4. **Make Something** in MIA's sidebar: describe something you track ("the seeds I save") for a screen, or something recurring ("every Sunday, tell me what I spent") for a workflow. Drafts change nothing until you publish.
  5. **Council Mode on the glasses**: "MIA, bring the council together", then a name ("Claude, start us off"), "everyone", "debate it", "sum up", "hold on", "that's all". The engine side is built; the speaker card and each member's voice on the glasses still need building and testing with you (T-0035).
  6. **Decide**: how the Creator looks on the page (DEC-0087).
  - Samples from the local image model: `C:\Users\zacrh\DevTools\imagegen\out\` (draft quality, under a second each).
  - Also new in the window: **Independence** (what each member has shown it can do; MIA's coder is 0 of 2 so far, from two real attempts on T-0019), **MIA's architecture** (read from the code; it found one real break, T-0042), and Made by MIA takes a **CSV file**.
  - Next build: T-0042 (a good first mission task), T-0035 (glasses side, with you), T-0036 (a bigger image model and consistent characters), the rest of T-0040 and T-0041.

- [ ] **Later, together (Zac, 2026-10-21): fill in all of Zac's own information** once the systems are built: the real addresses (homestead, each rental), how each activity is owned, filing jointly or not, the Freedom plan's numbers and builds, the flock, the recipes, the label info, the Compliance list verified one by one. Entered in MIA on the PC (data\, never the repo), with Claude walking through it.

- **PC day: done (2026-10-19).** The readiness check passed (Python, Tesseract, Plaid, account, password, Ollama with qwen2.5:14b, Phone Access, Tailscale serving, ffmpeg, starts with Windows); the speech and voice models didn't download yet (run install.bat again). Model picked: qwen2.5:14b (DEC-0022 note). Left: link the phone, and run install.bat again for the voices. Was: follow `docs/HOME_COMPUTER_SETUP.md` top to bottom: Windows Update + AMD driver + Git, `git clone` MIA, **install.bat**, set your password, **setup_home_pc.bat** (Ollama + qwen2.5:14b, Phone Access, ffmpeg, Tailscale, starts with Windows, no sleep, the model comparison, the readiness check), then on the phone Tailscale + Settings → Home Computer → Link. Then tell Claude "the PC is up" (and paste `pc-check\models.md`).

- [ ] **New in the next phone build (2026-10-19):** (1) **Talk to MIA through your glasses:** pull down Quick Settings → edit (✎) → drag **Talk to MIA** in, or long-press MIA's icon → Talk to MIA. With the glasses connected over Bluetooth, say "open Kitchen", "I weigh 182", or ask anything; she answers in your ear, and the glasses' screen switches to the app (once the glasses app is set up, ~Nov 16). Works with the phone alone too. (2) **Location quests while MIA is closed:** Settings → My Places → Allow All The Time (Android opens its settings: choose "Allow all the time"), then Allow Notifications. Arriving at a place then shows a notification; tap it.
- [ ] **Your insurance (DEC-0034):** Apps → **Insurance** → Add → **Read A Policy** (your car insurance's declarations page PDF, or a photo of it), check what MIA read, save. Then Shop It → **Draft A Quote Request**, send it to two or three insurers, and put their answers in with **Add A Quote**. MIA lines them up against what you have.
- [ ] **After PC day, the Memory Vault (DEC-0030 E):** on the phone, Apps → **Memory Vault** → Turn On The Vault, allow all photos. Leave MIA open on Wi-Fi a while; the strip counts what's safe on the PC. Then Free Up Space (Android asks you each time; its Trash keeps them 30 days). `docs/MEMORY_VAULT.md`.
- [ ] **Cameras (DEC-0033):** when you pick cameras, get local-stream ones (Reolink is easiest; `docs/SECURITY_CAMERAS.md`) and put them on the PC's Wi-Fi. With the phone linked to the PC (Settings → Home Computer) and Tailscale on both, add them from the phone: Security → Add A Camera → "On the home computer's Wi-Fi". They then work from anywhere. Next for Claude after that: smoother live video, motion alerts, cameras on the glasses, then lights/locks via a local Home Assistant.
- [ ] **Try the new game layer on the phone (DEC-0032):** Missions → **Quests** (start Ready For Winter; finish chapter 1 and watch chapter 2 open), the **Party** link there (start a raid; Join the leaderboard), Expeditions → **World Map** (press I'm Here; the phone asks for location once), Settings → **My Places** (Add Where I Am at the gym or store, Turn On, and next time you arrive MIA asks), a recipe → **I Made This** (the pantry goes down), and listen for the chime when you finish an objective (Settings → Sound to turn MIA's spoken lines on).

- [ ] **Homestead goods (DEC-0036, 2026-10-21):** in MIA (PC or phone) → Workshop → Recipes → Add Recipe: one real thing you make in batches (materials in your own units, "One batch makes", the price each, how many days it keeps). Add its materials under Materials, Begin Crafting, Finish, then the **Goods** tab: Label Info (your business name, address and Kentucky's statement), print a label, and try a market day. Zac's line stays within Kentucky's home-based processor rules (banana bread, cookies, breads, honey; `docs/HOMESTEAD_GOODS.md`). Tell Claude what's clumsy.

- [ ] **Chickens, greenhouse goods and starters (DEC-0037, 2026-10-21):** Workshop → Recipes → **From A Starter** → Eggs (set your price and how many days they keep). Apps → **Chickens** → Add A Flock (pick Eggs for the cartons), tap the eggs in each day, log feed when you buy it, and put a dozen Into Cartons. In the Grow Lab, harvest a batch "Also into stock". Tell Claude what's clumsy.

- [ ] **Freedom (DEC-0038, 2026-10-21), from the phone now:** Apps → **Freedom** → **Your Plan**: what a month of living takes, saved so far, about what you save a month, your take-home an hour and your shift length. Then **Add A Build** for each: greenhouse, chicken coop, solar, root cellar (about what each costs). Tell MIA your reasons ("remind me why") so they show at the bottom. Once Plaid is linked, the numbers fill in by themselves.

- [ ] **Zac's two specs (2026-10-21): approve the next steps.** Read `docs/BUSINESS_OS_AUDIT.md` and `docs/INTELLIGENCE_AUDIT.md` (sections 7-8 / 7 say what Claude needs). Approve DEC-0040 (the obligations calendar; and give MIA your addresses, how each activity is owned and whether you file jointly, in MIA, not in a chat that gets committed) and DEC-0041 (capability registry, then docs retrieval). Then ask your phone "What AI model are you using?" again.

### From your phone, now (you're phone-only for the moment)

Everything here works from a phone: the GitHub app (or github.com) for
the hub, and the Meta AI app.

- [ ] **Read `docs/CURRENT_STATE.md`** in the GitHub app: where the
      whole team is.
- [x] Q-0015 answered and DEC-0019 approved (2026-10-07): MIA on the
      phone, the spike now, Android first, iPhone soon after.
- [ ] **Try MIA on your phone, no computer:** open
      `https://github.com/TheKingCS/MIA/releases/tag/phone-spike` on your
      Android, install **MIA-Phone-Test.apk** (it sits beside the companion
      app), open it, and tell Claude how long it took to start and how it
      feels. Done: under 8 seconds (2026-10-07).
- [ ] **Fitness and meals (2026-10-14, DEC-0020/0021): the screens are
      in the phone build.** Workout → Today → **🎯 My plan**: set your
      goals, training days, what each training day is ("Dips 3x8", one a
      line), handstand practice, prep day, allergies. Kitchen → **Week
      Plan**: tap "+ add" on a day (or "Fill empty meals"), open a meal to
      see its recipe, try **Schedule meal** and **Add to grocery list**.
      Then log a weigh-in (Workout → Progress) and say "step one of
      today's workout complete", "today's lunch complete", "I weigh 182".
- [x] Your PC's specs (DEC-0022, via Muse H-0037/H-0038): Ryzen 7
      9800X3D, Radeon RX 7900 XTX 24 GB; on once the Ethernet cable
      arrives. (RAM still unknown; it doesn't change the plan.)
- [ ] **When the PC is set up:** install MIA on it (the Windows
      installer from the Windows CI run), Ollama for Windows (it runs on
      the 7900 XTX; Claude will say which model to pull), and
      **Tailscale** on the PC and your phone, signed in with the same
      account (free; this is what lets the phone reach the PC from work).
      Leave the PC on (sleep off) for MIA to reach it.
- [ ] **Look at MIA's new look (DEC-0023)** in the newest phone build and
      say what to change.
- [ ] **Your plan from Muse (H-0030):** ask Muse for your plan "in MIA's
      paste format" (she has `docs/PLAN_TEXT_FORMAT.md`), copy it, then
      Workout → 🎯 My plan → **Paste a plan** → paste → **Read it** → check
      what it says → Yes. Undo takes it all back.
- [ ] **Run the 1.5B Quick test again on build 21 or newer** (Model test,
      tap Start first) and send the screenshot: some questions are now
      answered by MIA's code instantly.
- [ ] **Test MIA's own AI model on your phone (2026-10-07):** install the
      newest MIA-Phone-Test.apk, then gear → Settings → **Model test**.
      Download **Qwen 2.5 · 1.5B** on Wi-Fi, tap **Start**, then **Quick
      test**, keep MIA open, and send Claude a screenshot of the results.
      If you have time, do the same with **Qwen 2.5 · 3B**.
      (`docs/PHONE_MODEL_TEST.md`)
- [ ] **Make your account on the phone (2026-10-07):** install the newest
      **MIA-Phone-Test.apk** from the same page over the old one. It asks
      for your name, email, password, country and what MIA should help
      with, then shows a **recovery code once: write it down**. Your "You"
      becomes you, and you stay signed in until you log out. The gear
      (top right on Home) now opens your real **Profile** and **Settings**.
- [x] DEC-0014 and DEC-0016 approved; Q-0011 answered (Android, no
      glasses yet, MIA not on the PC yet); Q-0012 parked (2026-10-05).
- [ ] **The screens' photos (DEC-0018):** ask ChatGPT for the images in
      `docs/design/IMAGE_REQUESTS.md` (paste that file), then on github.com
      → TheKingCS/MIA → `web/img` → Add file → Upload files, with exactly
      the filenames listed. They can come one at a time.
- [ ] **Switch on the public preview (one setting):** on github.com
      (in the phone browser, "Desktop site" if the menu is missing) →
      TheKingCS/MIA → Settings → Pages → "Build and deployment" →
      Source: **GitHub Actions**. Then Actions → "Pages preview" → Run
      workflow (or wait for the next push). The preview is at
      https://thekingcs.github.io/MIA/ (placeholder data only).
- [ ] **Try the new round (2026-10-16, H-0048)** in the phone app once it
      updates (or https://thekingcs.github.io/MIA/web/calendar.html and
      .../glasses.html with placeholder data): the **Calendar** (Home →
      Calendar), a **photo** on a recipe (open it → Add Photo), and on the
      glasses Missions → Select Mission → Sort, Kitchen → Recipes, Garage
      → Past Due. Star the apps you want pinned on the glasses (Calendar
      too, if you want it in your pins).
- [ ] *(When the glasses arrive)* **In the Meta Wearables Developer Center:** check that Web Apps
      (and the Device Access Toolkit) are enabled for your account.
- [ ] **In the Meta AI app:** turn on Developer Mode (Settings › App
      Info › tap the version number 5 times). It's needed to load
      MIA's glasses app later.
- [ ] **See MIA install and pass on Windows without your PC:** github.com
      → TheKingCS/MIA → Actions → "Windows". Green means GitHub's Windows
      machines installed MIA and passed its tests.

### At the PC, when you're back (your Windows PC, DEC-0015)

### New on 2026-10-01: try these first (about 30 minutes)

Start with `git pull` in your MIA folder. Tell Claude anything that
looks wrong (the text on screen, never passwords or keys).

- [ ] **Run the installer.** Ubuntu: `bash install.sh` in the MIA folder.
      It skips what you already have, adds a "MIA" shortcut to the app
      menu and ends with a setup check. Check that the shortcut opens
      MIA. On a Windows PC, if you have one: double-click `install.bat`
      (it has never run on Windows: send Claude what it prints).
- [ ] **Your account.** Settings → Email, Recovery Code & Household →
      add your email and Save. If you have a password: "Make a new
      recovery code" and **write the code down** (it's shown once). No
      password yet: Settings → Change Password gives you one and the
      code. Your existing profiles are now one household: check that the
      calendar, budget and kitchen still show everything.
- [ ] **Sign in by email.** Switch User → "Sign in with email". On the
      phone and in the Android app, sign in with your email too.
- [ ] **A test account.** Switch User → New Profile, choose "Nobody"
      for sharing: check it sees an empty calendar and budget. Then
      Settings → Email, Recovery Code & Household → Delete my account
      (tick "erase") while signed in as the test account.
- [ ] **MIA's setup questions.** Settings → My Apps → "Ask Me the Setup
      Questions Again". Pick a focus, or "Show me everything".
- [ ] **Country.** Settings → Support & Safety → Your country (United
      States keeps everything as before).
- [ ] **Email drafts.** In People & Pets, give someone an email (use your
      own address for the test), or say "Pat's email is ...". Then say
      "write an email to Pat saying hi": a draft opens; try Copy and "Open in my mail app".
      Optional: Settings → Sending Email with a Gmail **app password**
      (never paste it into a chat), then press Send. On the phone, the
      Android app's "Email drafts".
- [ ] **Imports.** Settings → Import from Another App: a calendar export
      (Google Calendar → Settings → Import & export → Export, unzip the
      .ics), your phone's contacts (.vcf), or a bank's "download
      transactions" .csv. Check the categories the bank import guessed
      in Budget. Say "undo that" if an import isn't what you wanted.
- [ ] **Undo and why.** Ask MIA to add something ("add milk to the
      grocery list"), then "undo that". When MIA messages you on her own,
      ask "why did you tell me that?".
- [ ] **Check My Setup.** Settings → Check My Setup (or ask "is
      everything set up?"); fix or report anything marked ❌.
- [ ] **Today.** Look at the new Today card on Home (under the
      greeting); tap a row to jump to its app. On the phone, the Today
      tab. Ask "what's on today?". Tell Claude if something you'd expect
      is missing.
- [ ] **Quick capture.** Click the "✚" in the header (or Ctrl+Shift+Space)
      and try a few: "milk and eggs", "changed the truck's oil today",
      "dentist Tuesday at 2", "idea: rain barrel by the shed". Each says
      where it went (Undo is right there); anything MIA can't place
      becomes a note tagged "capture". Tell Claude what landed wrong.
- [ ] **Private budget (optional).** Budget shows whose budget it is.
      Only if you want your own money separate from the household's:
      "Keep my money private...". Switching back keeps it for later.
- [ ] **Whose is it.** In Maintenance, edit the truck (or anything) →
      "Belongs to". Or tell MIA "the truck is mine". Things marked as
      someone else's drop off your Today list.
- [ ] **Accessibility.** Settings → Accessibility: try a bigger text
      size and high contrast (switch back after). Press Ctrl+Shift+R on
      any screen to hear it (needs MIA's voice installed). Tell Claude
      anything that's still hard to read.
- [ ] **Child accounts (only if a child will use MIA).** Add User →
      tick "This is a child's account", pick your household and type
      your password to approve. Sign in as them: only kid-friendly apps
      show, money and admin apps say "ask a parent", Settings has just
      text size and contrast. Your Account window (Settings → Email,
      Recovery Code & Household) can reset their password or make it a
      regular account later.
- [ ] **Starter sets.** Settings → My Apps → "Add a Starter Set...":
      look through the six sets and add any that fit (untick the parts
      that don't). Or tell MIA "set me up with the homestead starter
      set". Tell Claude what's missing or doesn't belong.
- [ ] **Your real life, entered through MIA (Engine Phase 1).** Put in
      your properties, loans, bills, income, vehicles and people the way
      any user would (or tell MIA). Tell MIA how things connect: "the
      land loan funds the lot", "the greenhouse depends on selling the
      lot". Then run `python -m tools.export_state --out me.state.json`
      in the MIA folder and look it over (it stays on your computer;
      never paste it anywhere public). Ask MIA "what did I get done this
      week?" and "what depends on selling the lot?".
- [ ] **Check the new front end on your new computer and phone (Phase 2).**
      On the new computer, in the MIA folder: `git pull`, then
      `python -m tools.web_check`. It opens MIA's new web Home in the
      built-in browser and prints one line (load time, memory,
      smoothness) and PASS or CHECK. Paste that line into the hub
      (`docs/CURRENT_STATE.md` under Recent changes) or send it to
      Claude. Then open MIA → Apps → "Home (preview)" and try "Done" on
      something that's due. On the phone (with phone access on), open
      the phone address plus `/web/` to see the same Home. Also answer
      Q-0010: what OS and hardware the new computer has.
- [ ] **Export your data** once, to see what's in it (Settings → Email,
      Recovery Code & Household → Export my data).

### Still waiting from before

**New computer? Start with `docs/SETUP_GUIDE.md`.** It walks through
every step below in order, from a blank machine, with Windows notes.

- [ ] **Plaid sandbox test** (full checklist: `docs/PLAID_SETUP.md`).
      1. On your main computer: `git pull`, activate `.venv`,
         `pip install -r requirements.txt`, `python main.py`.
      2. Plaid dashboard → Developers → Keys: copy your client_id and
         **Sandbox** secret. Never paste them into a chat.
      3. MIA → Budget → Bank Sync → Set Up Plaid: paste the keys, pick
         `sandbox`, and choose a vault passphrase (store it in a
         password manager; it can't be recovered).
      4. Connect a Bank → any bank → log in with `user_good` /
         `pass_good` (code `1234` if asked) → Sync Now.
      5. Check the Income, Expenses and Debts tabs, sync again, and
         confirm nothing is duplicated.
      6. Report back to Claude (the error text plus the last lines of
         `logs/`, never keys).
      7. Then Part 6: **Reset Plaid Setup** (clears the test data) → Set
         Up Plaid with your **Production** secret → connect your real
         banks (10 free connections; one bank login = one connection).
- [ ] **Phone voice first run** (full guide: `docs/PHONE_VOICE_SETUP.md`).
      1. Install Tailscale on the computer (`sudo tailscale up`) and on
         your Android phone, both on the same account.
      2. login.tailscale.com → DNS: turn on MagicDNS and **Enable
         HTTPS**.
      3. Give your MIA profile a password (Settings).
      4. Settings → **Phone Access** → tick **Let my phone reach MIA**
         (its checklist shows what's left).
      5. `sudo tailscale serve --bg http://127.0.0.1:8765`, then
         `tailscale serve status` to get your `https://…ts.net`
         address.
      6. On the phone: open that address in Chrome → log in → ⋮ → Add to
         Home screen → allow the microphone.
      7. Try it on the drive home (screen stays on, phone mounted).
         Report whether it heard you over road noise, how long answers
         took, and anything confusing.
- [ ] **Live check of MIA's conversation skills** (see
      `docs/ASSISTANT_AUDIT.md`). With Ollama running:
      `python tests/live_model_check.py`. It uses fake data and never
      runs the tools it's testing. Send Claude the FAIL lines.
- [ ] **Try "Talk it out".** In MIA: Notes → 🔒 Private Journal →
      Set Up… and pick a passphrase (you can reuse your Plaid vault
      passphrase; if you forget it, the journal can't be read). Then
      in chat or on the phone: "I want to journal", talk, "I'm done
      journaling"; check the entry in the Private Journal tab. Also try
      "just listen", "no bullshit", "hype me up", "off the record".
      Optional: Settings → Support & Safety → a trusted person.
- [ ] **Install the Android app.** On your phone: GitHub → the MIA
      repo → Releases → "MIA Companion (Android)" → tap
      MIA-Companion.apk (full steps: `android/README.md`). Needs the
      phone voice setup at home done first. Tell Claude what works and
      what doesn't: locked-screen listening, the headset button, the
      Bluetooth mic option, signing back in after MIA restarts.
- [ ] **Try the textbook tutor and the document inbox**
      (`docs/SETUP_GUIDE.md`, Part 10): add a textbook and study from
      it; send the mower's manual and a receipt to the inbox and file
      them. Install `tesseract-ocr` (Part 1a) and try a photo of a
      paper receipt, and Share → **MIA inbox** from the Android app.
      Tell Claude how well real receipts read (which digits it gets
      wrong, if any). Email intake is optional (a separate Gmail address with an
      app password; never paste the app password into a chat).
- [ ] **Claude Design pass.** Upload `docs/design_handoff/` (or the zip
      Claude sent) plus your inspiration pictures to Claude Design and
      paste the prompt at the top of its README. Bring the 3 directions
      back here; Claude builds the one you pick as a new MIA theme.

## 2. Build queue (Claude), in order

*History since 2026-11-03: open work is in `work/tasks/`.*

**Connecting apps (Zac, 2026-11-08):** the audit and plan are in the doc
https://claude.ai/artifact/H8gYSX2rvneRMp5mgA4qFa: one connector framework on `core/imports.py` and
`core/record_import.py` (read-only, preview, approve, one Undo, keys in the encrypted vault); no-sign-in sources
first (Airbnb calendar links and CSV, the TurboTax PDF, Sheets as CSV), then Hostaway and OwnerRez keys, then
Google and QuickBooks OAuth. Waits on Zac's order and on disk encryption / DEC-0126 before tax data.
**Claimed by the design session (2026-11-08 overnight, Zac asleep, "work on everything decided"): screens for
the engine session's new pieces:** My Directions (DEC-0141/0143: web/directions.html, `direction.*` actions),
How MIA Answers and Talk's "this one or this one?" (DEC-0138: `style.*`), Living Worlds Phase 1 (DEC-0134:
web/worlds.html, creation through actions; play waits on Phase 2's approval), About MIA (DEC-0142); then the
Theme Studio's mix and the glasses' accent, Trail Maps and the conversation history on the web. The engine
session keeps core logic; ask in this file before building one of these twice.
**Claimed by the design session (2026-11-08 overnight): DEC-0146's "don't bring that up"** (a Connections page in
Personal and a voice tool; `ConnectionBook.decline`/`allow`, a quiet list the finder respects). Built 2026-11-08.
**Claimed by the parity session (2026-11-08): the Connect Apps page** (web/connect.html, core/connectors.py): file
imports on the web (calendar, contacts, bank CSV; only in the Qt Settings until now) and calendar links (Airbnb,
VRBO, Hostaway) as check-ins and check-outs, previewed and approved.
**Claimed by the parity session (2026-11-08): the Sign-ins page** (web/signins.html, core/security_log.py,
Settings → Sign-ins and Security): the security log, new-device and wrong-password alerts, sign out everywhere
(docs/SECURITY.md step 3).
**Claimed by the parity session (2026-11-08): the Your Data page** (web/yourdata.html, core/your_data.py,
Settings → Your Data): what MIA keeps about you, store by store (how many, sealed or not), what she read for your
recent answers, and export / delete account on the web (only in the Qt Settings until now; docs/SECURITY.md step 8).
**Claimed by the engine session (2026-11-08 overnight, Zac asleep), core logic only:** (1) more sources for the
capability reminders (DEC-0143: a built-in plan whose materials are on the shelf, a skill with its tools owned) in
`core/capability_reminders.py`; (2) DEC-0137's next step, real-life surfaces reading `environment == real` only
(`core/presence.py`, the Life State); (3) knowledge entries (DEC-0105) for the engine's 2026-11-08 builds; (4)
derived link kinds `connections.unlinked` points at (`core/links.py`). Screens and voice for these stay the design
and parity sessions'. Note for the design session: the Greenhouse's **What's Next** tab (`web/grow.js`,
`web/equipment.js`, data `grow_page()["next"]`, DEC-0144) went in before I saw "Who builds what"; restyle or redo it
freely. `get_homestead_next_step` is its voice twin.
**Ready for a screen and a voice tool (from the engine session, 2026-11-08 overnight): playing a Living Worlds turn.**
DEC-0134 Phase 2 was approved by Zac when it was offered ("Lets build it and continue"); the DECISIONS record had
wrongly still said it waited, now corrected. The core is `core/dungeon_master.take_turn(book, campaign_id, version_id,
action, model_proposer(context))` → `TurnResult(narration, committed, failed)`, fictional events only.
**Claimed by the engine session (2026-11-08 overnight), core only:** (5) Living Worlds turn history: each turn kept
in the campaign (action, narration, what changed) and the last few fed to the DM for continuity (`living_worlds`,
`dungeon_master`), so a play screen can show the story so far; (6) DEC-0146's "research before raising one": a held
connection carries what MIA found about it in her own offline sources (a built-in plan, a specialist's sourced note,
what's on the shelf), said with it (`core/connections.py`).
**Claimed by the engine session (2026-11-08, Zac's ask), core only:** (7) deep next-step reasoning in
`core/development_engine.py`: a seed-starting chain (toilet-roll cups, a seed shelf, a first batch as proof, a stand),
path-to-goal look-ahead, readiness checks shown with each recommendation, made-first; `plan()` gains `path` and
`checks` for the What's Next screen. (8) The Woodworking Studio audit and proposal (docs only, no build). **(7) built:** for the
design session, `grow_page()["next"]["next"]` now also has `goal` ({id, name}), `path` (each step {id, name, cost,
made}) and `checks` (each {check, ok, line}; ok None is information): What's Next can show "step 1 of 6 on the way to …".
**Claimed by the engine session (2026-11-08), core only:** (9) the development profile's budget read from the
person's own Building Materials and Tools & Equipment targets, what's left of them this month (read-only; never edits
`core/budget_manager.py`); (10) connection research also searching the offline reference library when packs exist.
**Claimed by the engine session (2026-11-08), core only:** (11) DEC-0126's remaining personal stores sealed
(game stores, classroom, ratings, creations, record sets, online reminders, art, the loop, training and cooking
sessions, the saga's moments); (12) DEC-0057's status per capability; (13) DEC-0142's self-knowledge in how-to answers
about MIA. **(11) and (12) built.** **Claimed (engine), core only:** (14) deeper homestead chains in
`core/development_engine.py`, the same rules as the seed-starting chain: a coop, then a feed bin and a small laying flock
in spring, eggs before selling them; a compost bin's first finished compost as made seed mix, months later. **(14) built.** **(15) claimed (engine):** preserving the harvest (a canning setup, a first batch
put up, selling preserves only after a cottage-food rules check, eggs too) and a greenhouse's level, drained site before
the frame. **(15) built.** **(16) claimed (engine): T-0020**, a read-only repository subject for
`core/inspection.py`: docs checked against the repo (files a doc names that aren't there, decisions marked built whose
files are missing), findings as tasks. Ready for a voice tool (parity session): "what isn't working?" / "what's
broken?" -> `core.capabilities.status_summary(context, here)`. **(16) built**, with T-0021, T-0022, T-0025 and T-0023
(engine, 2026-11-08 afternoon, core only). **Ready for the design session's screens on the development dashboard
(`web/dev.js`, data `/api/dev`):** `disagreements` (each {subject, kind decision/design/task, status open/answered/zac,
raised_by, why, answer, next, command}, Zac's first: core/disagreements.py) and `evolution` ({months: each {month,
decisions, commits, tasks_done, capabilities, tools, screens, bugs_found, bugs_fixed, merged, undone, new_parts,
benchmarks {kind: {answered, from_code}}}, milestones, totals}: core/dev_evolution.py, DEC-0071's timeline).
`python -m tools.work history <words>` now also searches decisions, commits, failures and experiments
(core/dev_history.py), and every agent's briefing carries what the history says about its task's files.

**Who builds what (2026-11-07 night, after Power and Recent Changes were each built twice at once):** screens
(web pages, the canvas's look, the review's missing screens: Waiting For You, a plan's page, the Browser in the
canvas look) are the canvas-build session's. The parity session keeps to voice tools, routing, glasses asks and
`core/parity.py`. Claim a screen in this file before starting it.

**Parity (DEC-0125) is nearly whole (2026-11-07 night).** Voice 50 of 50 apps but Passwords (on purpose), phone
50, glasses 46: the only open gap is Look on the glasses (the glasses' own camera). Stage 1 of
`docs/DEVELOPMENT_PLAN.md` is done (Talk's mic, humor in Settings, the four phone pages with the canvas session,
"Say: ..." on every screen). Next: stage 2's glasses cards drawn for the apps that only have an ask; the design
review back to Claude Design (`docs/design/CORE_SCREENS_REVIEW.md`, partly overtaken by the canvas build).
Rules that hold it: a new app needs voice, phone and glasses or a decided gap (`work/parity.json`); its ask must
reach its own tools (tests/test_parity.py); a glasses ask too (tests/test_glasses.py); new tools go in both
`core/application.py` and `core/core_runtime.py` (K-0069); run the new questions against the live model
(`python tests/live_model_check.py`, K-0080).

**Every session, ongoing (DEC-0104): document what you touch, and work the backlog.**
`.venv\Scripts\python -m tools.docs next 15` lists the files with the most undocumented definitions (engine
first); `show <file>` prints each with its code; write the docstrings by reading the code (what it is, what it
does, how when that isn't plain; check any claim you aren't sure of), put them in a JSON
`{"core/x.py": {"func": "...", "Cls.meth": "..."}}` and `apply` it (inserts them, lowers the ratchet,
regenerates `docs/ATLAS.md`). Skip `core/budget_manager.py` and `core/plaid_manager.py` while Zac's Plaid work is
uncommitted. 6,863 of 13,808 documented on 2026-11-07: every core/, server/ and tools/ file is done (but those two); every modules/ and gui/ file is done too. In tests/ a test named as a sentence counts as documented (DEC-0116); 13,146 of 13,816 are documented, and what's left is test helpers and short-named tests (`tools.docs next` lists them). A docstring may now end in a quote (`apply` adds a space).

**Her own models (DEC-0106, build plan step 19):** the model forge (`core/model_forge.py`, `python -m tools.model_forge router` / `list`) made her first model 2026-11-07, a tool router trained on her tools' own words and the person's record names: 80% first pick, 95% top five on requests it never saw (card in `data/models/router/`, not in use). Each model is assigned to an issue (a slipping loop) or a project and judged by it; the playbook of five kinds and `python -m tools.model_forge needs` say where one could help. The router now runs in the shadow on every traced turn (its top five in the trace, the `models.router_shadow` loop); once it has 20 turns with a tool called, read how it did before deciding anything. Next: build plan step 19 (d) onward. `self_docs` (get_mia_docs, the council) now answers from her code's docstrings and the Knowledge Vault too.

**Her specialists (DEC-0109, `docs/specialists/`):** nine workers (construction, homesteading, radio, strategy, maker, outdoors, research, testing, engineering) with sourced workbooks; study hall gives one a night new notes (`python -m tools.specialists study <id>` by hand); notes stay derived until Zac confirms. Add a specialist by adding it to `SPECIALISTS`.

**Her weekly self-audit (DEC-0108):** `python -m tools.audit` (report), `code`, `connections`, `run`. Night School runs it weekly and opens one task each for the top code and interconnection finding (first: T-0052, T-0053). Her best practices are `docs/practices/` (written by `core/practices.py`: edit principles there, lessons come from the vault). Life events, links and the life state's new `areas` section (`core/life_areas.py`) were done 2026-11-07: 49% to 76% connected. What's left (boss book, dungeon, recreation, fitness, quests...) comes up one a week as an audit task.

**Her curriculum (DEC-0107, `docs/CURRICULUM.md`):** ten computing tracks, one Night School lesson a night for the next objective (`python -m tools.night_school curriculum`). Nothing run yet: the first real night with it is the next one. Grow it in `core/curriculum.py` when her teacher's lessons point at a gap.

**The Highest Self (H-0089 → H-0090, DEC-0114 PROPOSED):** the doctrine is `docs/design/MIA_HIGHEST_SELF.md`; its core is in `core/personality.py` (two CHARACTER clauses, a tone example, the faith-and-meaning line, the integrity rules, the values pinned by `tests/test_personality_values.py`). Measured on the corpus (`pc-check/conversation-highest-self-*`): routing fixed, doubt and grand plans better, "is God real" still deflected, dependency uneven, answers six words longer. Next, after Zac's ratings and decision: the three modes (Intellectual, Counselor, Creative), then tune on his ratings.

**Experience Maturity (DEC-0113 APPROVED 2026-11-07, amended):** the design canvas "MIA Core Screens" (H-0092, `docs/design/MIA_DESIGN_STANDARDS.md` §13) is the reference; the build runs in order: shared pieces (`web/ui.css`, the orb), Home and Talk, Workout, Kitchen, then every other app. Progress is tracked in the "Canvas build" list below.

**Learning paths (DEC-0112):** any desire runs through `core/paths.py` (guitar is its first program; anything else is drafted and started on the person's say-so). Don't build a parallel learn-a-skill feature: add a `Program`. MIA's own curriculum is ten Programs on her own PathBook (`core/curriculum.mia_book()`, `data/dev/mia_paths`); `python -m tools.night_school curriculum` shows it. **Guitar (DEC-0111):** when Zac has tried it, read his heard-check attempts (his folder's `paths.json`, path `guitar`): if real chords fail that should pass, adjust `CHORD_TONE`/`STRAY` in `core/guitar_ear.py` from those numbers (they were set on synthesized strings).

**Every commit, ongoing (DEC-0110): docs change with the code.** Run `.venv\Scripts\python -m tools.docs stale` before committing: it lists every definition whose code changed while its docstring didn't (changed parameters first). Read each and fix the words that no longer hold; lab reviewers get the same list.

**Every session, ongoing (DEC-0105): write MIA knowledge entries for what you build** (`work/knowledge/`, via `core.dev_knowledge.add`, by claude, citing the commit, task or decision): what you did, how, why that way, and what went wrong. K-0038 to K-0042 are the first (the documentation method and its lessons).

**The mission system is locked in (DEC-0047, `docs/MISSION_SYSTEM.md`).**
Build order (Zac said begin, 2026-10-27): 1) the Loop ✅ built
(`core/the_loop.py`), 2) the Sunday check-in ✅ built
(`core/weekly_checkin.py`). 3) the **Fix-It Log** ✅ built (DEC-0049, `docs/FAILURE_LOG.md`).
**Claude on the PC, every session: read the fix report first
(`python -m tools.fix_report`: it's sealed on disk since 2026-11-08; or Apps → Fix-It Log), turn the worst open issues into failing
tests and bench cases, fix, mark fixed.** **2026-10-27, Zac + Chat's direction:
the Brain, the Body, the Relationship.** The audit and the order are in
`docs/BODY_AND_RELATIONSHIP_PLAN.md` (section 8), with four questions
for Zac (section 9), answered (DEC-0050). **At the PC first: run
`python tests/live_model_check.py` (its new PERSON_CASES check MIA never
dead-ends with "I don't know") on the 14b; fix any FAIL before going on.**
Then plan step 1, the About Me page. Was: the Sunday morning
check-in, 3) adventures from the day's project with real-gain rewards
(the craft, the recipe unlock) and guild ranks, 4) pattern noticing,
titles, the emergent class, 5) the Codex, seasons as quarters,
cutscenes. **Zac, at the PC:** The Dungeon → Loop → Change on your
work: Sun–Thu (or your days), 9:30 pm to 6 am, and in Setup the
30-minute unpaid break; Chores: 2:30 pm. Or just
tell MIA. Reminders come from the PC app (it has to be running).

**Zac, at the PC (2026-10-27, DEC-0046):** Apps → The Dungeon → Set Up
Your Dungeon: the job, pay an hour, when overtime starts, the day the pay
week starts, and the words the paycheck shows in the bank (look at one
deposit under Money). Then clear today's run and try "GM this" in Talk
after a rough shift. Live-model check of Game Master mode on the 14b is
owed (tone, no invented numbers).

**Zac, 2026-10-24 (DEC-0045): the apps stay the layout; make MIA smarter
at using them.** The five-places frame is undone. Next AI work: MIA
working the apps for you in Talk and by voice (understand what you mean,
do it across apps, say what she did), not new navigation. Then Muse's
H-0070 Freedom look pass.

**Game layer (DEC-0028, `docs/GAME_LAYER.md`), 2026-10-17:** all built
except the watch HUD (waits for the watch): Reward Shop, gear bars,
bosses, stats, buffs, the Chronicle, and (DEC-0032) questlines, kitchen
blueprints, world map, party, sound, location quests. Possible next
steps there: more seasonal starters, a basemap under the world map
(offline tiles). Location quests in the background are built
(2026-10-19, `Places.kt`). **ALICE picks built (DEC-0029):** What I Used, MIA Remembers,
one conversation everywhere, the voice guide. **Expansion audit**
(`docs/EXPANSION_AUDIT.md`, DEC-0030 approved): phase B crafting is
built (Workshop → Recipes / Builds). DEC-0030 approved (2026-10-17). Built since: the phone side of DEC-0022 (`docs/HOME_COMPUTER_SETUP.md`), phase C Orders & Quotes, phase D Grow Lab, and show-off mode (DEC-0031). Next:
DEC-0022 on the real PC (model comparison; two-way sync with photos, files, conversations and the journal, heavy jobs and the **memory vault (phase E)** are built, 2026-10-18; vault next: copying while MIA is closed via an Android foreground service; near-duplicates (offered like bursts) and search and captions on the PC are built, 2026-11-06: `core/vault_captions.py`), then phase C (quotes from a recipe, customers and orders, a portfolio page),
D (grow lab), E (memory vault, after DEC-0022's phone↔PC link). Receiving
from a scanned receipt into a recipe's materials is a small follow-up.

**The phone spike passed (2026-10-07, `docs/PHONE_SPIKE.md`)**, and Zac
has it on his phone (first start under 8 s). His feedback is fixed:
account menu, no Apps tile, every card the phone's width, Garage spacing.

**Next build (DEC-0022, approved 2026-10-15): supercharged online.**
When the phone can reach Zac's PC (same Wi-Fi, or Tailscale), Talk uses
the PC's bigger model and falls back to the phone's 1.5B mid-
conversation; MIA shows which level she's on. Then heavy jobs on the PC
(voice, OCR, textbooks, email, bank sync), then two-way sync. Cloud AI
stays off unless switched on. **Zac's PC: Radeon RX 7900 XTX, 24 GB
(AMD: Ollama's ROCm support on Windows, or llama.cpp's Vulkan build).**
Plan: measure Qwen 2.5 14B (~9 GB, fast) and 32B (~19 GB, fits the card)
on the golden set in CI (accuracy only; CI has no GPU), pick one, then
build: the phone finds the PC at home (same Wi-Fi) **and from anywhere through Tailscale from the start** (Zac, 2026-10-15: from work Wi-Fi too),
Talk uses it with the phone's 1.5B as fallback, and the shell shows the
level (PHONE / HOME PC / ONLINE, Muse's H-0035 §5). Then presence-page
frame and the dashboard saying card as a readout (H-0035 §3).

**Glasses Heads-Up screen (2026-10-18):** swipe down on the orb; clear until a win or notification, then a card for 6 s. **Glasses quick action menus (2026-10-16, H-0042)** work in the preview
for every app (`core/glasses.py`); pins are the person's favorites
(DEC-0024); Household, People and Inbox panels and line icons are in
(H-0045). Phase 3 voice is built (2026-10-19, `core/glasses_voice.py`, `Voice.kt`: the phone listens through the glasses as a Bluetooth headset). Then: Phase 4 on-device
test when the Display arrives (~Nov 16: Funnel URL, revocable
glasses-only link limited to `/api/glasses` and `GLASSES_KINDS`).

**The Stark interface (DEC-0023, 2026-10-15)** is built; Muse reviews
(H-0034). Follow-ups: workshop-style header images, more line icons,
the presence page and character art in the new language.

**Fitness screens built (2026-10-14, DEC-0021, H-0029).** Next for
them: Muse's look review; recipe photos; a reps field on the practice
timer if Muse wants it; the 1.5B's remaining misses (questions with no
unique trigger: "What bills do I have?" reaches inventory through "do I
have"; debts, chores, the budget summary; completion phrasing).

**Next, in order (`docs/design/CONCEPT_AUDIT.md`'s build list):**
1. Onboarding (create your account on first start), Profile and Settings
   pages. This is Phase 2's first step.
2. Photos of things (assets, recipes, properties).
3. Skills and Missions like the concept.
4. The Real Estate detail panel.
5. Strip icons.
6. Weather (needs Zac's OK).
7. The net-worth trend.

Then the rest of Phase 2 (`docs/PHONE_FIRST_PLAN.md`): Android notifications, speech and battery, background checks, backup, an on-phone model for Talk, faster starts. Keep the iPhone path open.

**Now (2026-10-06, DEC-0017, approved): the web becomes all of MIA.**
Track it in `docs/WEB_PARITY.md`. Done: the shared frame (`web/shell.js`)
the Dashboard (`core/web_surfaces.py`, `/api/shell`,
`/api/dashboard`), the Apps page (`/api/apps`), Home as MIA herself
(Muse's orb + chat) and the ⋯ menu. Next, each one a full engine API (every read and every
add/edit/delete/complete as an action kind in `core/actions.py`) plus a
working screen on the frame, for Muse to restyle:
1. ~~Money~~ **done 2026-10-06** (`web/money.html`; bank connect/sync
   stays on the PC: it needs the vault passphrase).
2. ~~Garage + Maintenance~~ **done 2026-10-06** (plus Property,
   Greenhouse and the asset page; sensor graphs on its reading tiles and parts per asset done 2026-11-07).
3. ~~Missions, Skills, Character~~ **done 2026-10-06** (closes H-0013;
   still to do: character art; the tree's lines were drawn 2026-11-07).
4. ~~Kitchen, Workout, Real Estate~~ **done 2026-10-06** (Zac asked for
   them next; still to do: recipe ratings and photos, rest timer and
   guided sessions, depreciation and selling a property).
5. Photo fields for assets, recipes and properties (Q-0014, Muse said yes; recipes 2026-10-16, assets and properties 2026-11-07: done),
   stored in each person's data folder, never `web/img/` (that's the public repo).
6. Calendar, Notes, Inbox, full Assistant chat; then the rest of the 59 rows.
Ctrl+K search on the web: built 2026-11-07 (core/web_search.py).

**Direction (2026-10-01):** keep perfecting MIA for personal use, but
built for any person or household, not just you. The youth/school
initiative is parked (`docs/future/MIA_YOUTH_INITIATIVE.md`). Then
(2026-10-01) you asked to approach MIA as if hundreds of people may use
it, and went with Claude's recommendations. The plan, in order:

- **Stage 1, accounts and households: built** (ROADMAP "People and
  ownership", steps 1 and 2). Email sign-in with a recovery code,
  each account its own household, joining with a member's password,
  per-person settings, notifications, workouts and Classroom.
- **Stage 2, MIA asks and each person's Apps screen: built** (ROADMAP
  step 3). New accounts get MIA's setup questions; focuses (Personal,
  Home & Family, Homestead, Business, Student) order and tuck away apps
  per person without blocking any. Settings → My Apps; Modules → Hide
  from my Apps; or ask MIA ("switch me to student mode").
- **Stage 3, email drafts: built** (ROADMAP step 4). "Write an email to
  pat@example.com about the faucet": a draft window with Send (only when
  you press it), Copy, or your mail app; a card on the phone's web app.
  Sending is optional and per person (Settings → Sending Email; your own
  address, not the inbox mailbox). Follow-ups **built** (2026-10-01): the
  Android app's "Email drafts" (Send, Copy, Mail app, Discard), and
  addressing by name (People & Pets has an email field; household members
  by their sign-in email; "Pat's email is ..." remembers it).
- **Stage 4, country-aware crisis lines and currency: built** (ROADMAP
  step 5). US, Canada, UK, Ireland, Australia, New Zealand; elsewhere
  general advice and findahelpline.com. Settings → Support & Safety.
- **Stage 5, your data and undo: built** (ROADMAP step 6). Export and
  delete your account, "undo that", "why did you tell me that?", "stop
  telling me about ...", and Settings → Check My Setup. The accounts plan
  is complete.
- **MIA's installer: built** (ROADMAP step 7): `bash install.sh` on
  Linux/Pi (`--kiosk` for a Pi), double-click `install.bat` on Windows.
- **Imports: built** (2026-10-01): Settings → Import from Another App
  (.ics calendars, .vcf contacts, bank .csv statements).
- **Today: built** (2026-10-01): a Today card on Home, a Today tab on
  the phone, "what's on today?".
- **Quick capture: built** (2026-10-01): the "✚" in the header or
  Ctrl+Shift+Space.
- **Private budget: built** (2026-10-01): Budget → "Keep my money
  private...".
- **Ownership marks: built** (2026-10-01): "Belongs to" on vehicles,
  tools and appliances; "the truck is mine", "whose mower is it?".
- **Accessibility: built** (2026-10-01): Settings → Accessibility (text
  size, high contrast), Ctrl+Shift+R reads the screen aloud.
- **Child accounts: built** (2026-10-01): Add User → "This is a
  child's account"; kid-friendly apps only, no money or admin tools,
  the Assistant speaks simply, the safety reply also asks them to tell
  an adult. A child's journal stays private to them.
- **Open question for the owner:** should MIA also tell a child's
  parent when the safety floor triggers for the child? Today it does
  not (it tells the child to talk to an adult right away). Decide and
  tell Claude.
- **Starter sets: built** (2026-10-01): Home & Family, Homestead,
  Student, Personal, Business, Fitness; offered at the end of the setup
  questions, in Settings → My Apps, and by asking MIA.
- **Next in this line:** a real Habits module.


1. **Fix whatever the Plaid and phone-voice tests turn up.** Both were
   built without being able to reach Plaid or a real phone.
2. **Phone voice, phase 2, the rest.** Built (2026-09-28): phone
   conversations in the desktop's History, desktop screens refreshing
   after phone-made changes, and per-turn timings ("heard 1.2s ·
   thought 3.4s · spoke 0.8s"). **Left: faster replies**, waiting on your
   timings from a real drive: the slow stage decides the fix (streaming
   the model's words, speaking the first sentence early, or a faster
   speech-to-text model). Plus whatever your first real use turns up.
   Also built today: **sorting bank charges to your businesses** (Budget →
   Bank Sync → Review Business Tags; set up your businesses under Summary
   → Manage Entities first).
3. ~~Cognitive Extension, slice B: "Remember Why"~~ **built**
   (2026-09-27). Try it: Part 6 of `docs/SETUP_GUIDE.md`. Both follow-ups
   are **built** (2026-09-28): MIA asks which kind of support you want
   when you sound worn down (and learns your usual answer), and "remind
   me why" works on the headless Core voice loop too.
4. ~~Cognitive Extension, slice C: "Know when to speak"~~ **built**
   (2026-09-27): one gate for every unprompted message, 5/day, no quiet
   hours. The opt-in weekly journal reflection is **built** (Settings →
   When MIA Speaks Up), and so are offline/back-online notices with "remind
   me when we're back online" (2026-09-28). "Learning from being ignored"
   is **built** too: 3 of the last 4 of a kind dismissed → a 2-week break
   from that kind (Settings or "you can tell me about ... again" ends it).
   Slice C is complete.
5. **Fix what the live conversation check turns up** (now 215 cases,
   including Workout, People & Pets, Household, Classroom, and 7
   personal-mode cases). ("Propose, you confirm" updates from things
   mentioned in passing are **built**, 2026-09-28: try "the mower got a
   new battery today, $120" and answer "yes".)
6. **Cognitive Extension, slice D: Contextual Presence** (after the
   Android app): Places, geofenced transitions sent from the phone,
   Welcome Home, "you're at Lowe's, want the materials list?". Then
   slice E, Life Runway.
7. **Claude Design direction → new theme** (after you bring designs back).
8. ~~Finance, #2: homestead build and tool costs~~ **built**
   (2026-09-28): expenses tagged to builds and tools, build budgets,
   tool cost of ownership and cost per hour, Budget → Builds & Tools,
   five Assistant tools. Try it: Part 7 of `docs/SETUP_GUIDE.md`.
9. ~~Finance, #3: mower business-use write-off~~ **built**
   (2026-09-28): business-use log, hour-meter totals, worksheet with PDF
   (Budget → Builds & Tools). Follow-ups **built** (2026-09-28): the
   Business Report's "Equipment business use" section, and vehicles in
   miles with the standard mileage figure (enter each year's IRS rate
   in the worksheet).
10. ~~Finance, #4: money on your phone~~ **built** (2026-09-28):
   `/api/finance/summary`, a Money tab in the web app, Show money in the
   Android app. Read-only by design. Your finance sequence (debts →
   builds and tools → business use → phone) is complete.
11. ~~Textbook tutor and document inbox~~ **built** (2026-09-28). Try
   them: Part 10 of `docs/SETUP_GUIDE.md`. Follow-ups, roughly in order:
   - ~~reading photos and scans~~ and ~~"Share to MIA" on Android~~
     **built** (2026-09-28): Tesseract OCR in the background (install
     `tesseract-ocr`, Part 1a), Share → MIA inbox in the Android app;
   - the model's help on messy manuals (propose extra schedule steps,
     still confirmed by you), and updating an item's details (model,
     serial, warranty end) from its documents;
   - meaning-based search for textbooks (embeddings), so "why do
     breakers trip" finds a passage that never uses those words;
   - ~~a receipt's line items~~ **built** (2026-09-28): kept on the
     expense; "what did I buy for the greenhouse?". Later: splitting one
     receipt across two builds.

## 3. Ideas parked for later (need their own planning pass)

- **MIA on Zac's Amazon Echo** (Zac, 2026-11-08: "connect to my amazon echo later over wifi or something and wipe it
  and put MIA on it"). Device identified 2026-11-08: a **1st-gen Echo Show** (the 7" screen model, 2017; "Snow" is
  the white colour), Fire OS 5.5.6.9, serial G000 MW04 7422 0PPK. Findings:
  - **Model confirmed by Zac 2026-11-08: the 7" rectangular wedge = the original 2017 Echo Show, Intel Atom
    x5-Z8350.** This is the dead-end chip. The only Echo unlock that exists (amonet, a MediaTek bootrom exploit) does
    not touch Intel, and no root or custom ROM has ever been published for this model — the XDA request thread is
    only speculation. Its locked, signed Intel bootloader means there's no exploit to run even if bricking is fine.
  - **Wiping it / custom ROM is not realistic for this model.** The sideload exploits that exist (XDA "Checkers"/
    "Crown", amonet) are for the MediaTek 2019 Echo Show 5/8, Echo Spot and Echo Dot 2nd gen — not this one.
  - **Stock sideload is blocked too.** The 1st-gen Echo Show has a hidden developer menu (tap the serial in Device
    Options), but community reports say it has no ADB option and no "unknown sources" toggle, so you can't even
    install an APK the normal way.
  - **Its browser is too old for MIA's web UI.** Fire OS 5 ships Amazon Silk on an Android 5.1 engine; MIA's front
    end (modern JS/CSS) won't render on it, so a browser-kiosk pointed at the PC won't work here.
  - **What does work, ranked:** (1) pair it as a **Bluetooth speaker** for MIA on the PC/phone so she speaks through
    it (simple, reversible, no risk; its far-field mic likely won't come back to MIA, only the speaker); (2) retire
    it and give MIA her own voice on the **Raspberry Pi** with a mic array — the clean local-first path (DEC-0015
    step 4). An Alexa skill is out: it sends speech to Amazon's cloud, against local-first.
  - **Three honest paths, Zac to pick (2026-11-08):** (A) use it as-is — pair it as a Bluetooth speaker so MIA speaks
    through it (works today, output only, its far-field mic won't come back to MIA); (B) gut it — since Zac is fine
    bricking it, harvest the 7" panel + speaker + shell and drive them with a Raspberry Pi running MIA's web UI (the
    Echo becomes MIA's body; the salvaged LCD's driver board is the hard part); (C) buy the right chassis — a used
    MediaTek Echo Show 5 or 8 (2019) for ~$30, then amonet → LineageOS → MIA kiosk is the reliable "wall MIA screen".
  - **MIA-side work that helps B and C (and a cheap tablet):** a kiosk/panel view of the web UI — full-screen, big
    clock, due items, Talk — that runs on whatever screen wins. Worth building regardless of the Echo's fate.



- **The ideas list: `docs/future/IDEAS.md`** (Zac, 2026-10-18): future
  features that automate life and save money, each written up the same
  way. First one: an insurance check-up (compare and save). Zac adds to
  it over time; nothing there is approved until he picks it.


## 4. Known loose ends

- **DEC-0126 next stages (Claude):** people are sealed (relationships_people.json, checked 2026-11-09); money waits on the PC's Plaid work (core/budget_manager.py). Was: seal money and people next (add the file names to `at_rest.SEALED`, make their `_load` use `open_text`, grep for other readers of the names first: K-0105), then the rest of PERSONAL_STORES; the phone's Android Keystore; a Settings line showing sealing on/off and the recovery key behind the password. The optional passphrase waits on Zac.
- **1,382 "Finished a book" life events (2026-11-08)** in data/life_events.jsonl from the decorator bug (fixed in 9bb99d47). History is never rewritten, so they stay unless Zac says to clear them.

- **On Zac's PC (2026-10-20):** `pytest` used to save into the real
  `config\config.json`: one run left 49 test profiles (Alex, Faith) and
  made a Faith the active one. Fixed in `tests/conftest.py` (a temp
  config, and the end-of-run guard now covers config.json too); the
  leftover profiles are removed. Windows Update restarted the PC
  overnight (12:22 to 3:01 AM) and MIA only starts at sign-in, so it
  stayed down until Zac signed in. Fix (Zac chose both):
  `pc_stay_up.ps1` (also setup step 6): no restart while signed in or
  6 AM to midnight, and Windows signs in by itself (Sysinternals
  Autologon). Done 2026-10-20: zacrh is now a local account (it was
  a Microsoft account Zac doesn't use) and signs in by itself. Two tests
  fail only here, on unchanged code too: `test_ocr.py::test_unavailable_without_tesseract`
  (Tesseract really is installed) and
  `test_phone_server.py::test_mia_gives_herself_a_console_when_there_is_none`
  (stdout is Windows' `nul`, which says it's a terminal). Something loaded
  llama3.2 onto the graphics card forever earlier that day (the default
  config's model with keep_alive -1), costing ~1 s an answer; it was
  unloaded, and `ollama ps` should show only qwen2.5:14b. Git on the PC
  has no name/email set (Claude commits with `-c user.name=Claude -c
  user.email=noreply@anthropic.com`) and no auto-push hook.

- ~~`tests/test_reference_library_manager.py` fails now and then on Zac's PC~~: found 2026-11-06 (a just-written file's timestamp can run a few milliseconds ahead of time.time() on Windows; the test's quiet period is below zero now).
- Cloud sessions have no auto-push git hook: Claude pushes manually
  after each commit (working as intended).
- ~~`tests/run_module.py` can't open **Household**~~: it wires `recurring_missions` now (2026-11-09).
- One test fails in Claude's cloud sandbox (UTC clock) and looks
  timezone-dependent:
  `tests/test_navigation_module.py::test_sun_moon_summary_for_real_coordinates_has_sensible_shape`.
  It predates this session and probably passes on your computer.
- Accounts: the inbox's email mailbox, the field kit's expedition sync,
  backups and reports still read the device's first household (the main
  `data/` folder). Deleting a profile doesn't tidy an emptied household.
- Plaid: auto/personal loans and lines of credit now become Debts too
  (2026-09-28), but the bank doesn't report their rate or minimum: fill
  those in on the Debts tab. Card payments may show both as an expense
  and on the card; watch for double counting once real accounts sync.
- The Bank Sync tab's intro text about Fidelity needing a support
  ticket may be outdated under Plaid's Trial plan.
