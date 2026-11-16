# MIA OS: core architecture open questions (Prompt 05, deliverable 15)

*Claude (Fable), 2026-11-16. Planning only. What the core architecture leaves unresolved: Zac's decisions, the
proofs of concept that would settle technical uncertainty (described, **not run**: Prompt 05 authorises none), the
earlier technical questions this prompt answers, and what later prompts inherit. The central list is
[MIA_OS_OPEN_QUESTIONS.md](MIA_OS_OPEN_QUESTIONS.md).*

## 1. For Zac

| ID | The question, in plain words | Recommendation |
|---|---|---|
| **Q-47** | Is the PC's foundation settled as: Fedora's KDE desktop, delivered as an image built from this repository, with Ubuntu 26.04 as the fallback if the graphics card's AI support disappoints on Fedora? (This is DEC-0189. It also needs your yes on three earlier proposals it rests on: DEC-0154, MIA's engine stays independent of any one operating system; DEC-0157, the PC image; DEC-0158, system changes only through a small helper.) | Yes, conditional on the two tests in Q-49 |
| **Q-48** | On the PC, should MIA's session run on KDE's own window manager instead of the single-app kiosk in the earlier proposal? In plain terms: with the kiosk, MIA's session shows only MIA, and any ordinary program means switching to the desktop; with KDE's window manager, an ordinary program's window can open inside MIA's session beside her. The second fits where your handoffs are heading and is less proven. (DEC-0191.) | Test both (Q-49, test 3) and choose on the result; lean to KDE's window manager |
| **Q-49** | May the proofs of concept in section 2 be run? Two happen in a virtual machine and touch nothing. One needs you: starting the PC from a Fedora USB stick (installing nothing) to measure the graphics card running MIA's models. | Yes to all; the USB test first, because it decides the foundation |
| **Q-50** | When MIA makes a system change (an update, a firewall port), the operating system itself will ask you to confirm, in its own dialog, after you've approved her proposal. Should it always ask for your password, or may some named changes pass with one click? (DEC-0194.) | Always the password at first. Loosen named actions later, each as a reviewed change to the image, never by MIA |
| **Q-51** | Should MIA's services keep running on the PC when you're signed out (as on the Pi), so reminders and the phone keep working with nobody at the screen? | Yes: it's what makes her dependable. It means your data is unlocked on the machine while it's on, as on any signed-in computer |

## 2. Proofs of concept (proposed; none run)

Each has what it settles, what it needs and when it passes. None changes the PC's Windows install.

| # | Settles | What is done | Needs | Passes when |
|---|---|---|---|---|
| **PoC 1** GPU compute on Fedora | the foundation (DEC-0189; REQ-HW-002; T-10, T-11) | Boot Fedora 45 KDE from a USB stick; install `ollama` with its ROCm backend into the live session; run the 3B, 14B and 32B models; repeat with the Vulkan backend; note Wi-Fi, Bluetooth, TPM, suspend | Zac at the PC, a USB stick, an hour. Nothing is installed to a drive | the 14B model writes at 65 tokens a second or more (Windows: 73) on either backend, and the display, audio and network work. Below that on both: Ubuntu 26.04 gets the same test |
| **PoC 2** the image | DEC-0189's delivery (REQ-ARC-011, REQ-REL-009, REQ-SEC-008) | In a virtual machine: a `Containerfile` deriving from Fedora's KDE image adding one MIA unit; build; install; switch to it; update; roll back; verify a signature is required | a VM on the PC or a cloud runner | the VM boots the built image, an update applies atomically, the previous deployment boots from the menu, an unsigned image is refused |
| **PoC 3** the session | DEC-0191 (REQ-FUN-001, REQ-UX-023; T-13, T-14) | In PoC 2's VM: MIA's session once on KWin with the shell as its client and once on cage; run the list in the session document §3 | PoC 2 | the list passes on one of them; if both, KWin |
| **PoC 4** the runtime as a service | DEC-0155's Linux half (REQ-REL-004, REQ-SEC-002) | In the VM: `deploy/install_runtime.sh`; readiness and watchdog signals; the credential; lingering; her browser on Chromium; the engine's suite | PoC 2 | the suite passes; a hung runtime is restarted; sealed files open only for the unit |
| **PoC 5** the helper | DEC-0194 (REQ-ARC-010) | A helper with two read-only methods and one harmless change, its polkit actions and the dialog | PoC 2 | acceptance checks A6 to A8 pass for those methods |
| **PoC 6** narrowing file reach | DEC-0194 §5 (REQ-FUN-006) | A Python worker that applies Landlock to itself, then tries paths inside and outside its list; the same after a grant changes | any Linux with a current kernel | outside paths fail at the kernel; a changed grant takes effect in a new worker; no measurable slowdown |

Order: 1 first (it can change the base). Then 2, since 3, 4 and 5 build on its VM. 6 is independent.

**Results so far** (Zac said yes on 2026-11-16, Q-49, while away from his PC; run on GitHub's Linux machines by
`.github/workflows/mia-os-poc.yml`; the kit and the steps for test 1 are `os/poc/README.md`):

| Test | Result |
|---|---|
| PoC 6, Landlock | **Passed.** Kernel 7.0 (Landlock version 8): a worker restricted to its granted folder read and wrote there, was refused everything else (another folder, `/etc`, the home folder), still imported Python modules; a second worker with a different grant saw only its own; file opens 6% slower |
| PoC 2, the image (build half) | **Passed.** `os/Containerfile` builds on Fedora 45's KDE Atomic image and passes `bootc container lint`: kernel 7.3.3, Ollama 0.24.0 with **both** GPU paths from Fedora's own repositories (ROCm 7.2.2 and Vulkan), cage 0.3.1, MIA in a Python 3.13.18 environment under `/usr/lib/mia`, her user unit in place. Booting it, updating and rolling back is still to do (a VM) |
| PoC 4, the runtime as a service (first half) | **Passed** after one fix: `deploy/install_runtime.sh` installed and started it as a systemd user service; it came up (95 services, 429 tools, 11 jobs), ran with no restarts and stopped cleanly on systemd's signal. The fix: on Linux with no sound server, the audio library's own error at import stopped the whole runtime (`core/voice_manager.py` now treats any audio failure as "no voice") |
| The engine's suite on Linux | **Passes** (rerun 2026-11-16 after fixing a test that assumed an American time zone; the code was right). All four jobs green in the same run |
| PoC 1, the graphics card | Ready; needs Zac at the PC with a Fedora USB stick |
| PoC 2, the image (boot half), and PoC 4 from the image | **Passed** (2026-11-16, `.github/workflows/mia-os-vm.yml`, run 43872077107, in a KVM virtual machine on GitHub's Linux machines): the image installed itself onto a disk (`bootc install to-disk`, btrfs), booted, and bootc reported the deployment; MIA's runtime ran as a person's service from the image; an update to a second version was fetched from a registry and booted; a rollback to the first version booted with the person's data untouched. Not shown: that an unsigned image is refused (signature checking wasn't switched on in this test), and `bootc-image-builder` could not run on those machines, so the installer image path is untested. |
| PoC 3, PoC 5 | Not yet (the VM they need now exists) |

## 3. Earlier technical questions, answered or moved

| ID | Question | Answer here |
|---|---|---|
| T-02 | Is the API with its live stream enough, or D-Bus or a socket too? | Enough for his records. D-Bus for the OS's own services and the helper; a Unix socket carrying the same API for local tools. [IPC](MIA_OS_IPC_AND_COMMUNICATION_ARCHITECTURE.md) §2 |
| T-06 | Typed events across processes: guarantees? | None needed: an event says where the truth changed, the receiver reads it; what needs a guarantee is a record. IPC §3 |
| T-09 | A portal for conventional apps to offer capabilities | Start with a one-method D-Bus name that only accepts a capture. Apps *offering* capabilities to MIA waits for a real case; Prompt 10 |
| T-10 | Ubuntu or Fedora on the PC | Fedora, conditionally; decided by PoC 1. The situation changed since `docs/HARDWARE.md` was written: Fedora now packages ROCm and Ollama's ROCm backend itself |
| T-11 | The 32B model's speed | Measured in PoC 1; Prompt 06 and 07 |
| T-12 | Boot time targets | Measurable once PoC 2's image exists, with systemd's own timing; Prompt 14 |
| T-13 | The screen reader in MIA's session | A line of PoC 3; a reason to prefer KDE's window manager, whose accessibility stack is Plasma's |
| T-14 | The shell: a browser engine or native | Provisional: the Qt WebEngine host MIA has; final in Prompt 10 |
| T-03 | A schema and version per store | Not this prompt's; the storage layout leaves it room (07, 15) |

## 4. Technical uncertainties with no test yet

| Uncertainty | Why it matters | Who settles it |
|---|---|---|
| When Fedora ships bootc-native KDE desktops, and whether deriving from the current image stays supported until then | the image's upstream path | watch; PoC 2 shows today's state |
| Whether the unlock credential can be bound so that only the runtime's unit can use it, not any program of his | how much sealing protects against an ordinary program he runs | Prompt 13, with PoC 4 |
| The helper's language | the size of the only root code | Prompt 13 |
| Whether speech should leave the runtime's process | the API's responsiveness while she listens and speaks | measure in PoC 4; Prompt 07 |
| Suspend and resume with a model in the GPU | daily reliability | Prompt 06 |
| A second person on the same PC: where household data lives, one model server for two runtimes | not needed today (DEC-0119) | Prompt 12 if ever |
| How MIA's own apps are packaged inside the image as the registry's per-app packages arrive (M6) | image size and update granularity | Prompt 15 |
| Whether `/etc` changes made through the helper should be recorded for replay on a rebuilt machine | rebuilding the PC from the repository alone | Prompt 14 |

## 5. Inherited by later prompts

| Prompt | Inherits from this architecture |
|---|---|
| 06 Hardware | PoC 1's measurements; no out-of-tree kernel modules; hardware reached only through standard services; the Pi on Raspberry Pi OS |
| 07 Intelligence | the model server as a separate system service on loopback; VRAM can't be limited by the OS, so routing must manage it; the `models` location; the cache location for indexes and embeddings |
| 08 Autonomy | the seven-step path for system actions; the two confirmations; slices for agents' work; the run record as the place long tasks live |
| 09 Self-awareness | the observability sources and the diagnostic snapshot; "report what the system says" |
| 10 Desktop | two sessions sharing user services; the shell as a compositor client; the compositor's own recovery menu; the OS-drawn indicators for microphone and camera; PoC 3's result |
| 11 Visual identity | the shell's host and what the compositor allows (blur, layers) |
| 12 Multi-device | loopback by default, the firewall zone, Tailscale optional; one runtime per person; events as re-read signals |
| 13 Security | the boundary table and what a compromise of each part gets; polkit as the trusted path; Landlock; the helper's containment; SELinux left on |
| 14 Boot and recovery | the boot order and its failure column; the previous deployment; the recovery page; what is and isn't backed up |
| 15 Build | the `Containerfile`, a pinned Python and a locked environment inside the image, signing, a VM test run of the acceptance list |
