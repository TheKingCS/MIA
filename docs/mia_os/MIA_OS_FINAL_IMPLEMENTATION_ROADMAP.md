# MIA OS: the final implementation roadmap (Prompt 17 §11; 17b §4)

*Claude (Opus), 2026-11-18. Version 1.0. Governs over Prompt 16's milestones and work packages where they differ
(DEC-0275). Prompt 16's stages (DEC-0269, approved), Zac's R1 order (DEC-0270) and the drive swap (DEC-0272) stand.
What changed: a **Foundation** stage of packages proven in a VM comes before anything touches his PC, and every package
has a full specification before it starts (REQ-IMP-012).*

## 1. The order

```
Stage 0 (ongoing)  Windows backlog WP-01..WP-12 ── carries over unchanged
Foundation (VM)    FW-01 build → FW-02 CI → FW-03 session ┬→ FW-04 health/updates → FW-05 disk → FW-06 helper
                                                         ├→ FW-07 migration rehearsal   FW-08 signed releases
                                                         └→ FW-09 USB recovery  FW-10 devices  FW-11 desktop  FW-12 degraded AI
Hardware (Zac)     HW-01 GPU proof (USB stick, any time)   HW-02 Windows from the enclosure (before MV-01)
MVP                MV-01 install and move (needs FW-01..07, 09, 10, HW-01, HW-02, the drive) → MV-02 a week of use
Alpha              FW-08 first signed release; Alpha requirements; R1 PC work begins
Beta               WP-22 R1 PC pieces → WP-20 household display → WP-21 the laptop
```

**The critical path:** FW-01 → FW-03 → FW-04 → FW-05 → FW-07 → MV-01 → MV-02, with HW-01 and HW-02 joining before
MV-01. Everything else runs beside it.

## 2. What was Prompt 16's, now

| Prompt 16 | Now |
|---|---|
| WP-01 to WP-12 (Windows backlog) | unchanged; WP-01 to WP-04 are at the MVP gate, the rest Alpha unless traced otherwise |
| WP-13 PoC 1 | HW-01 (now measures qwen2.5:14b as well) |
| WP-14 image in a VM | **mostly done** headless (VM run 43872077107); the rest is FW-01, FW-02, FW-04 |
| WP-15 sessions | FW-03 |
| WP-16 updates, greenboot, helper | FW-04 (updates, greenboot), FW-06 (helper) |
| WP-17 Secure Boot and TPM | FW-05 |
| WP-18 signed releases | FW-08 |
| WP-19 migration | FW-07 (tooling and rehearsal), MV-01 (the move) |
| WP-20, 21, 22 | unchanged, in Zac's order: 22, 20, 21 |
| — | new: FW-09 USB recovery, FW-10 devices on Linux, FW-11 desktop integration and accessibility, FW-12 degraded intelligence, HW-02, MV-02 |

## 3. Workstreams

| Stream | Packages | Owner |
|---|---|---|
| OS image and build | FW-01, FW-04, FW-05, FW-08 | Claude; Codex reviews |
| Session and desktop | FW-03, FW-11 | Claude (function), Muse (look) |
| System authority | FW-06, WP-01, WP-02 | Claude; Codex security review |
| Data and migration | FW-07, WP-04, WP-09, MV-01 | Claude with Zac |
| Quality and CI | FW-02 | Claude |
| Recovery | FW-04, FW-09 | Claude |
| Devices and Android | FW-10, WP-10, WP-20, WP-21 | Claude |
| Intelligence and models | FW-12, HW-01, WP-08 | Claude; MIA's specialists for benches |
| Memory and recall | WP-22 | Claude |
| Security content | WP-03, WP-05 | Claude; Codex |
| Look and sound | WP-06, WP-07 | Claude, Muse |
| Documentation | every package (its docs are part of done) | the author of each |
| Homestead | W-HOME (Beta) | Claude |

## 4. The foundation packages, specified

Every package below: test-first where a bug is involved; the full suite before each commit; documentation and the
generated maps updated (CLAUDE.md); reviewed by Codex before it counts as done (DEC-0174, DEC-0268); no package
approves itself.

### FW-01 A reproducible image build *(recommended first)*

> **Accepted 2026-11-18** (GitHub run 44297829546, commit 8d10713f): two builds of one commit gave identical RPM and
> Python package lists and no unexplained file difference under `/usr` (four expected ones, the package managers'
> databases); the Linux suite passed. Zac passes the gate (REQ-IMP-004).
>
> **State (2026-11-18): built. The VM test passed on the locked image** (GitHub run 44285161809: installed, booted,
> the runtime up, updated, rolled back). **The first two-build check** (run 44290637615) found the package lists
> identical and 199 file differences, all explained and fixed: compiled-Python caches that `pip freeze` wrote again
> after they'd been removed (the removal is now last) and the RPM database at `/usr/share/rpm` (now listed as
> volatile). Earlier state: built; its CI acceptance runs on the push. Zac said go (Q-109). Built: the base pinned by
> digest; `os/requirements.lock` and `os/requirements-build.lock` with hashes, written by `os/lock_requirements.py`;
> the image installs only from them with `--require-hashes`; the reference PC's model set in the image; the GPU
> bench measuring qwen2.5:14b (70.2 tokens a second on Windows today, bar 63); a second no-cache build compared
> by `os/image_manifest.py`; both image workflows on every change to their inputs and weekly;
> `tests/test_os_image.py`. **Deviations from the specification below, each with its reason:**
> 1. *The model is set in the image's copy of the default config, not in `config/default_config.json`*: that file is
>    shared with the Pi and the general installer, which would then download a 9 GB model the Pi can't run.
> 2. *No `PySide6<6.12` pin*: on his PC, PySide6 6.12.0 installs its separate WebEngine wheel (6.12.0.140) by
>    itself and WebEngine imports, so the technology check's "wheel delayed" was out of date. The lock holds 6.12.0
>    with its WebEngine wheel, and the image build imports `PySide6.QtWebEngineCore`.
> 3. *greenboot and Tailscale aren't added yet*: greenboot installed without its checks configured could reboot or
>    roll back the VM test for reasons of its own, so it moves to FW-04 where its checks are built; Tailscale moves
>    to FW-10 with the devices.
> 4. *Piper is left out of the image* (Zac's Q-108 answer); MIA already falls back without it.
> 5. *Three packages publish no wheel* (`plaid-python`, `http-ece`, `srt`; all pure Python): they're built in the
>    image, with their build tools from their own hash-checked lock, installed first.
> 7. *Codex reviewed the change* (2026-11-18) and found two defects, both fixed before the commit: a differing
>    package list could pass the step (bash doesn't stop on the left side of `&&`), and the workflows' path filters
>    missed most of what the image copies. The build check now runs on every push; the hour-long VM test on changes
>    to how the image is built or started and every day.
> 6. *Fedora's packages float within Fedora 45's updates* (security fixes): the list is recorded in the image
>    (`IMAGE_RPMS.txt`) and compared between the two builds; pinning every RPM would break builds when Fedora
>    replaces a version.

| Field | Specification |
|---|---|
| Objective | Two builds of one commit install the same OS packages and the same Python packages, and the image starts MIA on the right model |
| Requirements | REQ-DX-003, REQ-IMP-010, REQ-ARC-001, REQ-ARC-011 (partly), REQ-FUN-202; fixes C-08, C-17, G-10 |
| Affects | `os/Containerfile`; `requirements.txt`; a new lock file (name settled on inspection: `requirements.lock` beside it, generated); `config/default_config.json` (model); `os/poc/gpu_bench.py` (bar on qwen2.5:14b); `.github/workflows/mia-os-poc.yml` and `mia-os-vm.yml` (triggers); `os/poc/README.md` |
| Prerequisites | none (DEC-0263 and DEC-0279 approved, Q-109) |
| Tasks | 1. Resolve `kinoite:45` to its digest and pin `FROM …@sha256:`, with a comment naming the tag and date. 2. Generate the lock with `uv pip compile --generate-hashes` for Python 3.13 on Linux; install it with `--require-hashes` (no `pip install --upgrade pip`). 3. ~~Pin `PySide6<6.12`~~ (not needed: deviation 2). 4. ~~Add `greenboot` (greenboot-rs) to the image's `dnf install`, and Tailscale from its own repository~~ (moved: deviation 3). 5. Set `qwen2.5:14b`, `num_ctx` 32768 for the reference PC (in the image: deviation 1). 6. Give `gpu_bench.py` the everyday model as its bar and record the Windows figure for it. 7. Build twice in CI from the same commit and compare the installed package lists (`rpm -qa` and `pip freeze`) **and a manifest of the image's files** (path, size and hash of everything under `/usr`, excluding documented timestamp-only differences). 8. Run the VM workflow on changes to how the image is built or started and daily, not only by hand (deviation 7). 9. Correct the Containerfile's header and the PoC README's table |
| Deliverables | a pinned, locked image; a CI job that fails when two builds differ; the VM test on a schedule |
| Security | the lock's hashes stop a changed package; the digest stops a changed base; no secret enters the image |
| Failure and rollback | each change is a commit; reverting it restores the old build. If the lock breaks the Windows install, Windows keeps `requirements.txt` (the lock is Linux-only) |
| Unit tests | a test that `default_config.json`'s model is the everyday model named in `docs/HARDWARE.md`; a test that the Containerfile's `FROM` carries a digest; a test that the lock covers every line of `requirements.txt` |
| Integration tests | the two-build comparison; the VM test passing on the locked image |
| Acceptance | two CI builds of one commit report identical package lists and file manifests (any remaining difference listed and explained); the VM test passes; a fresh image's runtime reports qwen2.5:14b |
| Done | all of the above on master, documented, Codex's review addressed |
| Human approval | Zac approves starting it (Q-109); no other |
| Agent | Claude Code; Codex reviews |
| Size | one session |

### FW-02 CI as the gate

> **State (2026-11-18): built; its acceptance (three green pushes, the suite green inside the image) runs in CI.**
> Built: the Linux suite on every push (since FW-01); every action pinned to the commit its tag named on 2026-11-18,
> the tag kept as a comment; `permissions: contents: read` on every workflow that didn't say (the phone's and the
> food table's keep their own `write`, which they use); the glasses test reads today when each test runs; the whole
> suite runs inside the booted image on the image's own Python and packages, against the repository's tracked files
> (the tests read folders the image leaves out); `tests/test_ci_workflows.py` keeps all of it, and keeps any
> Windows user folder out of code and settings. **Deviations:** 1. *Windows CI stays on Python 3.12*: that's what MIA
> runs on today on his PC, and 3.13 is the image's; each is tested where it runs. 2. *A failure reaches the next
> session by its first step* (`gh run list` at the start, `docs/NEXT_SESSION.md`), not by CI writing into the
> repository, which would need a write token. 3. *Docs and records keep the user folder they were written with*
> (they're history, and some are Zac's own prompts); the test covers code and settings.

| Field | Specification |
|---|---|
| Objective | The full suite on Linux and Windows on every push, the same Python on both, and the suite inside the image |
| Requirements | REQ-DEV-016, REQ-DEV-011, REQ-ARC-003, REQ-FUN-041 (Alpha); fixes G-08, G-09 |
| Affects | `.github/workflows/` (a Linux suite workflow on every push; `windows.yml`'s Python); `tests/test_glasses.py` (fixed clock); a test over workflows |
| Prerequisites | FW-01 |
| Tasks | 1. A `suite-linux` job on every push to master, Python 3.13. 2. Windows CI to 3.13. 3. Pin every action by SHA with `permissions:` on each workflow. 4. Fix the midnight test with a fixed date. 5. In the VM test, run the suite inside the booted image against a throwaway data folder. 6. A test that fails when a workflow uses an unpinned action. 7. A failure writes to the next session's notes (`docs/NEXT_SESSION.md` is read first). 8. A test that no committed file holds a personal path or name (DEV-011) |
| Security | least-permission tokens; pinned actions |
| Failure and rollback | revert the workflow commit |
| Tests | the workflow test; the glasses test at 23:59 and 00:01 UTC |
| Acceptance | three pushes in a row green on Linux and Windows; the suite passes inside the image |
| Approval | none beyond the plan |
| Agent | Claude Code; Codex reviews |
| Size | one session |

### FW-03 MIA's session and the Plasma fallback (PoC 3)

> **State (2026-11-19): done; accepted by the VM run of e1af2147 (CI run 44460432338).** The image's login screen
> (Plasma Login Manager 6.8) defaults to the "MIA" session (`os/files/mia-login.conf`); it runs KWin with her shell
> (`gui/os_shell.py`) as its client, which comes back by itself if it dies (`os/files/mia-shell`) and says what it
> shows with the time (`shell-state`). In the VM, logged in at the real login screen: her front end loaded 2.8 to
> 4.2 s after login; a terminal opened beside her; the shell killed and back; her runtime stopped, the recovery page
> shown and a terminal opened from it by keyboard alone (QEMU `sendkey`); Plasma's desktop, splash gone, 7 to 8 s
> after login; then the update to version 2 and the rollback, his data kept. **Found and fixed on the way:** her
> shell writing its log inside the read-only image (it now uses `MIA_HOME`, and the logger falls back to the
> console); a test reading the VM before its shutdown had finished; and /boot as an automount that let go when
> idle, so ostree couldn't apply an update at shutdown (`os/files/boot-stays-mounted.conf`,
> `finalize-needs-boot.conf`). On his PC the installer writes /boot into fstab; the drop-ins stay as a guard.
> Measured on GitHub's VM, not his PC (MV-02 measures that); Orca is FW-11's.
>
> **Fable's review, 2026-11-20, what the VM run does and doesn't show:** the test logs in automatically into a
> *named* session, so the login screen's own default (`mia-login.conf`'s `DefaultSession`) is **not shown** to be
> a setting Plasma Login Manager reads, and probably isn't one: the run of 74509e62 found no such word in its
> program. Check at the first real login (MV-01) which session the login screen offers first, and set it there if
> it isn't MIA's. Her shell's drawing on the real
> GPU is untested (the VM draws in software). Fixed in the review: the session no longer waits on her runtime
> before KWin starts (`--no-block`); the shell stops relaunching after three quick deaths and opens a terminal
> saying so; it notices when her runtime was restarted and looks for her again; its own links act only from its
> recovery page; the recovery page and the keyboard-opened terminal are now asserted, not only printed.

| Field | Specification |
|---|---|
| Objective | At login, "MIA" (default) shows her front end full screen with ordinary windows beside it; "Plasma" is one choice away; if MIA fails, a recovery page and Plasma still work |
| Requirements | REQ-FUN-001, REQ-UX-002, 011, 020, 022, 023, REQ-DSK-001, 018, 031, REQ-PER-002, REQ-REL-016, REQ-ARC-004 |
| Affects | `os/Containerfile`; new session files under `os/files/` (a `wayland-sessions` entry and its launcher script; exact names on inspection of Plasma Login Manager's session directory); `os/files/mia-runtime.service`; the shell host in `gui/` (the WebEngine window's full-screen mode exists: `gui/main_window.py` web mode); `deploy/install_runtime.sh`'s enabling step moved to first sign-in; the VM workflow |
| Prerequisites | FW-01 |
| Tasks | 1. A session entry that starts `kwin_wayland` with her shell as its client. 2. First sign-in enables the runtime for that person and makes the sealing credential (as `install_runtime.sh` does). 3. The shell shows a recovery page (Plasma, terminal, logs) when the runtime isn't ready in 30 s. 4. Plasma Login Manager's default session set to MIA. 5. In the VM: log in automatically as a test user, screenshot her shell, open Konsole beside it, kill the shell and see it return, stop the runtime and see the recovery page, log in to Plasma. 6. If KWin can't hold one full-screen client with ordinary windows, cage with the shell, and Plasma for everything else (DEC-0191's fallback) |
| Security | the session runs as the person; nothing as root |
| Failure and rollback | the Plasma entry is untouched by everything here; the previous image is one boot away |
| Tests | session-file lint; the VM driven by keyboard through QEMU's monitor (`sendkey`): reach Plasma, a terminal and System Settings from MIA's session by keyboard alone, and log out to the other session; screenshots checked for a known element at each step; window behaviour (a Konsole window opens, moves and closes beside her shell); times from login to Home measured. Orca is FW-11's (Alpha) |
| Acceptance | the VM run shows each step above, with Home within 10 s of login on the VM's hardware noted (his PC is measured in MV-02) |
| Approval | none |
| Agent | Claude Code (needs Linux desktop knowledge: KWin and Plasma Login Manager specifics are A until run); Codex reviews |
| Size | **provisional**: two to four sessions, re-estimated after its first session (the least certain package; a graphical VM test doesn't exist yet and is part of it) |

### FW-04 Health, readiness, updates and rollback

> *Adds from FW-01 (deviation 3): `greenboot` (greenboot-rs) into the image's `dnf install`, configured with this
> package's checks.*
>
> **State (2026-11-20): done; the review's changes accepted by the VM run of 74509e62 (CI run 44699128590).** An
> update staged by the night's service applied at a restart, with its snapshot taken at that shutdown; both broken
> versions booted, failed their check and were rolled back (the test now requires that each did boot); bootc's own
> timer is masked. Accepted before by the VM run of dce4f674 (CI run 44529591174).
>
> **What the review changed (2026-11-20).** MIA OS **never restarts by itself.** The night timer still stages an
> update; it applies when *he* next restarts or shuts down. Why: the apply timer's schedule line was invalid and
> never fired; its idle test couldn't pass in her session; and with the disk's PIN asked at every start (FW-05), a
> restart at night would have left the computer at that prompt with MIA down. The snapshot of the homes is now
> taken at the shutdown that applies an update, whoever started it (`mia-update-snapshot.service`, newest three
> kept). bootc's own fetch-and-restart timer is masked, and the build fails if enabling anything fails. Free disk
> space is an advisory check now (a full disk is not a bad update). The watchdog's ping stops when her schedule
> hasn't come round for half an hour, and nothing on her main loop waits on the network. **For Zac (Q-114):**
> whether he ever wants unattended restarts, knowing each stops at the PIN prompt. **Known and kept:** on an
> encrypted disk a rollback's restarts each ask for his PIN, so "no hand on the keyboard" holds only for an
> unencrypted VM; after a rollback the same broken version is staged again the next night until a fixed one is
> published (it rolls back again each time he restarts). The runtime
> is a `Type=notify` service with `WatchdogSec=120`: `READY=1` once her core is up, `WATCHDOG=1` from the main loop
> only while her schedule runs (`core/sd_notify.py`, `Runtime.readiness`: started, core, models, all, also in
> `/api/runtime/health`). `python -m core.self_test` reruns itself on an empty folder and checks build, tools, the
> schedule, a change and its read-back. Greenboot: required checks (the login screen, `/var/home` writable, 2 GB
> free, since made advisory), wanted ones (network, the model server); the self-test became a required check in
> part B. Updates: `mia-update-stage.timer` stages at 03:00. (The first design also restarted the computer at an
> idle moment; the review of 2026-11-20 removed that: see the State above.)
>
> **Found in the VM (2026-11-19):** the automatic path works (staged at night, applied at an idle restart). A broken
> update was caught by greenboot, but with /boot on the Btrfs root GRUB can't write its environment ("sparse file not
> allowed"), so the boot count never fell back and it rebooted into itself for 25 minutes. **An install of MIA OS
> must have /boot as its own ext4 partition** (FW-05's layout, and Anaconda's default); the VM's disk now has that
> layout, installed with `bootc install to-filesystem`.
>
> **Accepted (2026-11-19):** with that layout both broken updates rolled back with no hand on the keyboard: the one
> whose self-test fails (required check 43) and the one whose login screen can't start (check 40) each booted once,
> failed, and greenboot called `bootc rollback` ("Boot counter exhausted ... initiating rollback"); version 2
> came back and his file was there. The self-test is a **required** check (the spec's task 4 said wanted, its
> task 7 needs a rollback; it reads no one's data and needs no network), run as `nobody` on a fresh folder.
> **The snapshot** (run 44579393224): with `/var/home` its own subvolume, as a Fedora install has it, a read-only
> snapshot was taken before each of the three restarts and held his file. **Loose end:** nothing prunes
> `/var/mia-snapshots` yet (keep the newest few; do it the next time `os/` is touched).

| Field | Specification |
|---|---|
| Objective | The runtime tells systemd when it's ready and pings a watchdog; greenboot checks the OS and MIA's self-test; night updates install by themselves and a broken one rolls back by itself |
| Requirements | REQ-ARC-002, REQ-REL-004, 009, 017, 018, 023, 024, REQ-OPS-001, REQ-SEC-003, REQ-SEC-022; Alpha: REQ-FUN-010, REQ-REL-026, 036 |
| Affects | `core/runtime.py` (`sd_notify`, watchdog pings, the four readiness levels); `os/files/mia-runtime.service` (`Type=notify`, `WatchdogSec`, hardening; unify with `deploy/mia-runtime.service`); new greenboot check scripts under `os/files/`; a MIA self-test entry point (inspect `core/runtime.py` and `/api/runtime/health` for the existing checks); a night-update timer and its idle check; the VM workflow |
| Prerequisites | FW-01, FW-03 |
| Tasks | 1. `READY=1` at "core"; `WATCHDOG=1` from the main loop. 2. One readiness vocabulary (started, core, models, all) in code and docs. 3. **Required** greenboot checks (local only): the login manager reached, `/var/home` mounted, free disk above a floor. **Advisory** (logged, never a rollback): network, the model server running. 4. A wanted check: MIA's self-test as a one-shot under a dynamic user on a throwaway folder. 5. A Btrfs snapshot of `/var/home` before an update applies. 6. bootc's update timer staged at night, applied at an idle restart. 7. In the VM, the **automatic** path end to end: the night timer stages an update, the idle check passes, the snapshot is taken, the restart applies it; then a deliberately broken image (its runtime fails the self-test; another whose login manager fails) rolls back with no command typed; data untouched. The manual `bootc switch` and `rollback` test stays as a separate check |
| Security | the self-test never reads his data |
| Failure and rollback | greenboot's own counter; the previous deployment in the boot menu |
| Tests | unit tests of the readiness states and the notify calls (a fake socket); VM fault injection |
| Acceptance | both broken images roll back without a hand on the keyboard; his test file survives |
| Approval | none |
| Agent | Claude Code; Codex reviews |
| Size | two sessions |

### FW-05 Disk encryption, Secure Boot and recovery keys

> **State (2026-11-20): done; the review's changes accepted by CI run 44699128448 (74509e62):** the first step kept
> the install's passphrase; a wrong recovery key was refused and removed nothing; the right one was accepted and
> the passphrase removed; the PIN alone opened the disk before and after an update; with Secure Boot off the
> recovery key opened it and `again` left one TPM enrolment and the recovery key. Enrolment is now two steps:
> `mia-disk-enrol` makes the recovery key and enrols the TPM and its PIN and **removes nothing**; after a restart
> opened by the PIN, `mia-disk-enrol finish` asks for the recovery key as written down, checks it opens the disk,
> and only then removes the install's passphrase (before, it was removed in the first run, before the PIN had
> opened a real start: a miscopied key and a TPM that behaved differently on real hardware would have lost the
> disk). It refuses an install that doesn't tell the start to use the TPM. `mia-disk-enrol again` enrols the TPM
> afresh after a firmware or Secure Boot list (dbx) update, which change PCR 7 like turning Secure Boot off does:
> **his install guide must say that such an update means one start with the recovery key, then `again`.** The VM
> uses a software TPM on the TIS interface; his PC's firmware TPM (CRB) is first tried at MV-01, with the install's
> passphrase still in place. Earlier state: accepted by CI run 44602462298 (0c9b8cda). Fedora's own boot image already holds
> cryptsetup and the TPM's library (the build checks, and would build it again only if they were missing:
> `os/files/dracut-mia-tpm.conf`), so the image still builds the same twice. The install uses a temporary
> passphrase; `os/files/mia-disk-enrol`, run once as root, makes the recovery key (shown once, for the envelope),
> enrols the TPM bound to PCR 7 with a PIN, and wipes the temporary passphrase. The VM boots OVMF with Secure Boot
> (Microsoft's keys) and a software TPM, types at the disk prompts on its serial line, and checks the three
> outcomes: the PIN opens it; after an update the PIN still does, no recovery key; Secure Boot off, the recovery key.
> /boot is its own ext4 partition (FW-04's finding). MIA's data key stays on the system credential (DEC-0169).
> **Seen in the VM:** Ubuntu's OVMF with Microsoft's keys boots Fedora 45's shim with Secure Boot enabled. Enrolment
> leaves two ways in (slot 1 recovery, slot 2 TPM) and wipes the install's passphrase. With Secure Boot on, a boot
> asks "Please enter LUKS2 token PIN" and nothing else, before and after an update. With it off, the PIN is still
> asked first (systemd can't know the TPM will refuse until it tries), the TPM refuses, and the boot asks "Please
> enter recovery key for disk root"; the recovery key opens it. His install guide (MV-01) should say exactly that.

| Field | Specification |
|---|---|
| Objective | The disk is LUKS2, unlocked by the TPM (PCR 7) with a PIN, opened by a recovery key, under Secure Boot, and an update never asks for the recovery key |
| Requirements | REQ-SEC-001 (with SEC-029 merged), REQ-SEC-013, REQ-FUN-002, REQ-IMP-008 |
| Affects | the VM workflow (OVMF with Secure Boot and a software TPM, `swtpm`); `bootc install to-disk --block-setup tpm2-luks` or an enrolment script under `os/files/`; `docs/mia_os/MIA_OS_ENCRYPTION_AND_KEY_MANAGEMENT.md`; his install guide (MV-01) |
| Prerequisites | FW-04; DEC-0277 approved; Q-106 answered |
| Tasks | 0. Extend the VM workflow (it has neither today): OVMF's Secure Boot firmware with Microsoft's keys enrolled, and a software TPM (`swtpm`). 1. Boot the VM with Secure Boot on. 2. Install with LUKS2 and enrol TPM PCR 7 with a PIN. 3. Generate a recovery key and show the printing step. 4. Apply an update and boot: no recovery prompt. 5. Turn Secure Boot off: the TPM refuses, the recovery key opens. 6. MIA's own data key (sealed stores) on the system credential as today (DEC-0169) |
| Security | the PIN carries most of the protection; the recovery key is printed, never stored in MIA or chat |
| Failure and rollback | in the VM, nothing to roll back; on his PC this runs only in MV-01 |
| Tests | the VM run above |
| Acceptance | each of steps 4 and 5 as stated |
| Approval | Q-106 (a PIN at each boot) |
| Agent | Claude Code; Codex security review |
| Size | two sessions (the VM setup included) |

### FW-06 The system helper (PoC 5)

| Field | Specification |
|---|---|
| Objective | MIA changes the system only through a helper with fixed operations, each confirmed in the OS's own dialog |
| Requirements | REQ-ARC-010, REQ-AGT-024, REQ-SEC-022 (partly) |
| Affects | a new helper (a small D-Bus service; location under `os/` settled on inspection), its polkit policy and unit; an action kind in `core/actions.py` with its tier in a manifest; the VM workflow |
| Prerequisites | FW-03 |
| Tasks | 1. Three operations only for the MVP: apply a staged update now, restart a MIA unit, power off or restart. 2. A polkit action for each, requiring the person's authentication. 3. MIA's action calls the helper; it never runs a shell. 4. In the VM: the operation succeeds after the dialog and is refused without it |
| Security | no free-form commands; parameters checked by the helper itself; Codex reviews it as security-critical |
| Failure and rollback | remove the helper's unit; MIA's action reports "not available" |
| Tests | the helper's own tests; a test that the action kind is act_with_approval |
| Acceptance | the VM shows the dialog and the refusal |
| Approval | none beyond the plan |
| Agent | Claude Code; Codex security review |
| Size | two sessions |

### FW-07 Migration tooling and its rehearsal

| Field | Specification |
|---|---|
| Objective | A tool that records every store's count and content hash and a sample of his files on Windows, restores on MIA OS and compares, rehearsed end to end in the VM on synthetic data |
| Requirements | REQ-CMP-002, REQ-CMP-003, REQ-IMP-002, REQ-IMP-005, REQ-IMP-009 |
| Affects | a new tool under `tools/` (name on inspection); `core/backup_manager.py` and `core/personal_data.py` (store lists); `core/at_rest.py` (open sealed stores on Linux; its dual-boot comment); the phone's re-pair and sync-base reset (inspect `core/phone_link.py` and the sync code); tests |
| Prerequisites | FW-03 (to restore into the image), WP-09 (the restore drill) |
| Tasks | 1. A manifest: for each personal and household store, record count and a hash of its records in a canonical order. 2. A file sample: hashes of N files chosen across his folders. 3. Restore and verify on the image; a report that names any mismatch. 4. The phone resets its sync base after re-pairing. 5. A list of Windows-only programs he uses and each one's Linux answer (REQ-CMP-003). 6. Rehearse the whole move in the VM with a synthetic profile |
| Security | the manifest holds hashes, never contents; the backup stays encrypted |
| Failure and rollback | the Windows drive is untouched throughout |
| Tests | unit tests of the manifest; the rehearsal |
| Acceptance | the rehearsal's report shows every store matched; a deliberately damaged record is caught |
| Approval | none for the tool; MV-01 needs Zac |
| Agent | Claude Code; Codex reviews |
| Size | **split**: FW-07a the store and file inventory and the manifest (tasks 1, 2, 5), one or two sessions; FW-07b restore, verify, the phone's reset and the rehearsal (tasks 3, 4, 6), two sessions; re-estimated once 07a's inventory is concrete |

### FW-08 Signed releases

| Field | Specification |
|---|---|
| Objective | Images signed with a cosign key pair and verified by bootc's policy; an SBOM with each; the phone app signed from secrets |
| Requirements | REQ-REL-034, REQ-ARC-011 |
| Affects | a release workflow; `containers-policy.json` and the public key in the image; `android-phone`'s signing step (waits on DEC-0160's key) |
| Prerequisites | FW-01, FW-04; Zac's signing key for the phone |
| Tasks | 1. Generate the image key pair (the private key in GitHub's secrets only). 2. Sign on release; `syft` SBOM attached. 3. The image's policy requires the signature; `bootc switch --enforce-container-sigpolicy`. 4. In the VM: a signed update applies, an unsigned one is refused |
| Security | the private key never in the repository or chat |
| Acceptance | the VM shows both outcomes |
| Approval | Zac approves each release (Q-101) |
| Agent | Claude Code; Codex reviews |
| Size | one or two sessions |

### FW-09 USB recovery

| Objective | Requirements | Tasks | Acceptance | Size |
|---|---|---|---|---|
| A USB stick reaches a desktop and his data without MIA and without the internal OS | REQ-OPS-002 | the image's installer ISO (bootc's `anaconda-iso` or Fedora's live KDE) documented as the recovery stick; unlocking LUKS with the recovery key from it; mounting `/var/home`; a written procedure in his guide | in the VM: boot the ISO, unlock, read a test file | one session |

### FW-10 Devices against the Linux PC

> *Adds from FW-01 (deviation 3): Tailscale from its own RPM repository in the image.*

| Objective | Requirements | Tasks | Acceptance | Size |
|---|---|---|---|---|
| The phone and glasses work against MIA OS as against Windows; device records with scoped keys; revocation immediate on the hub, erase best effort | REQ-FUN-181, REQ-SEC-004, 024, REQ-DEV-002, 003, REQ-DST-005, 029, REQ-CMP-004 | run the phone server's tests on Linux; a phone emulator against the VM; per-device records (today per profile: `core/phone_link.py`); scopes; a revoked key refused at once (WP-10 builds the Windows side) | the emulator pairs, syncs, is revoked and refused, in the VM | two sessions |

### FW-11 Desktop integration and accessibility

| Objective | Requirements | Tasks | Acceptance | Size |
|---|---|---|---|---|
| Her shell lists Linux apps, opens KDE's settings pages, uses portals for sharing, shows the microphone and camera in use; at Alpha, Orca, full keyboard use, layouts from 1280×720, two monitors | MVP: REQ-ARC-013, REQ-FUN-003, REQ-DSK-007, 023, 025. Alpha: REQ-ACC-004, REQ-DSK-003, 026, 033, REQ-VIS-005, 008, 011, 015, REQ-HW-020, REQ-UX-010 | read `.desktop` entries; `systemsettings` page links; the xdg-desktop-portal screenshot and file chooser; an indicator from her own audio and camera use; Alpha: Orca pass, a keyboard-only pass, two monitors in the VM | VM screenshots for each; Orca reads the approval card (Alpha) | MVP one session; Alpha two |

### FW-12 Degraded intelligence

| Objective | Requirements | Tasks | Acceptance | Size |
|---|---|---|---|---|
| A model failure falls back to the next local model and says so; the conversation never waits behind background work; at Alpha, the CPU fallback, removable models and the capability truth | MVP: REQ-AI-013, REQ-HW-029. Alpha: REQ-HW-004, 012, 014, REQ-FUN-221, 222 | inspect `core/llm*` routing; a fallback chain with a spoken note; the GPU queue gives the conversation priority (DEC-0204); tests with a failing fake backend | tests; in the VM with no GPU: answers from a small CPU model, said so | one session |

### HW-01 The GPU proof (Zac, an hour)

Fedora's live KDE from a USB stick on his PC; `gpu_bench.py` measures qwen2.5:14b and qwen3:14b: tokens a second,
memory, load time, and a one-hour stability run; the bar is qwen2.5:14b at no worse than 90% of its Windows figure.
If it fails: Ollama's Vulkan backend, then upstream Ollama's build, then the Ubuntu comparison (C-16).

### HW-02 Windows from the enclosure (Zac, before MV-01)

With the 1 TB in its USB enclosure and the 4 TB not yet installed: does the PC boot Windows from it? If not (Windows
often refuses to boot from USB), the fallback is the drive back in the slot, about ten minutes with a screwdriver
(Q-107). Either way the Windows drive is never written to.

### MV-01 The install and the move (with Zac)

At least two sessions with him, after FW-01 to FW-07, FW-09, FW-10, HW-01 and HW-02 pass. Backup on Windows, the
manifest, the drive swap, the install (FW-05's encryption), restore, verify (REQ-IMP-009), the phone re-paired.
Stops at the first mismatch.

### MV-02 A week of use

His main system for a week. The 67 MVP-gate requirements re-verified on his PC; Home within 10 s measured; nothing
lost. Zac passes the gate (REQ-IMP-004).

## 4b. The living system packages (Prompt 21)

LS-01 to LS-10 (`MIA_LIVING_SYSTEM_GAP_ANALYSIS.md` §6): LS-02 (provenance on his memories and life notes) at the MVP
gate; LS-01, 03 to 08 in Alpha; LS-09, 10 in Beta. About 14 to 16 sessions, beside the foundation, critical path
first. Each is specified in full before it starts.

## 5. Effort, honestly

| Part | Claude's sessions | Uncertainty | Zac's time |
|---|---|---|---|
| FW-01, FW-02 | 2 | low | none |
| FW-03 | 2 to 4 | **high** (KWin as a one-app session is unproven) | none |
| FW-04 to FW-08 | 9 to 12 | medium | none |
| FW-09 to FW-12 | 5 to 6 | medium | none |
| Stage 0 WP-01 to WP-12 | about 10 | low | trying things |
| HW-01, HW-02 | — | the GPU result could change the base | about two hours |
| MV-01, MV-02 | 2 + support | medium | two sessions, then a week |

About 30 to 35 Claude sessions before the first install, beside the Windows backlog. No date is promised: a session's output
varies, his hands-on steps set the pace of the critical path, and FW-03 may need more. Tasks that need more than AI
coding: Linux desktop specifics (FW-03; verify by running, not by reading), security review (FW-05, FW-06: Codex, and an
experienced person's eyes if Zac knows one), real hardware (HW-01, HW-02, MV-01, MV-02). Safe to defer: everything
listed under Alpha and Beta.
