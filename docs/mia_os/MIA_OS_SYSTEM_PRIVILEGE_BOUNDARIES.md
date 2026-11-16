# MIA OS: system privilege and trust boundaries (Prompt 05, deliverable 10)

*Claude (Fable), 2026-11-16. Planning only. Who runs as what, where root exists, how a system change gets
authorised, and how the damage from a compromised part is contained. The complete security and privacy architecture
is Prompt 13's; this fixes the component boundaries so that secure operation is possible. Decision: DEC-0194
(proposed), refining DEC-0158.*

## 1. The boundaries

From least to most trusted. A part can reach the part below it only through the door named.

| Part | Runs as | Contained by | Can reach | Through |
|---|---|---|---|---|
| Outside text (pages, mail, captures, feeds) | data, not a process | marked as outside wherever a model sees it; a turn that read it can't change a record (built) | nothing | |
| A conventional application | his user | Flatpak's sandbox for Flatpak apps; nothing extra for ordinary ones (as on any Linux) | his files as its permissions allow; **MIA only by handing her a capture** | the portals; `org.mia.Capture1` |
| An extension, generated code not yet merged | his user, narrowed | bubblewrap: no network, its own data folder only, a system-call filter, resource ceilings (DEC-0176) | exactly the capabilities its manifest declares | the capability contract over its socket |
| An agent or tool worker | his user, narrowed | its own process; file reach limited to granted folders (§5) | the runtime | the runtime's internal call |
| The model server | its own system user | a system unit with its own sandboxing; GPU access by group | nothing of his: it sees only the prompts sent to it | loopback HTTP |
| MIA's shell, the capture agent | his user | separate processes; they hold no records | the runtime | the API with a token; the socket |
| **The MIA Runtime** | **his user, never root** | `NoNewPrivileges`; no capabilities; its slice; the base's mandatory access control | his records (it is their only writer); the OS's services as his user | adapters (D-Bus) |
| **The system helper** | **root** | a fixed interface; a tight unit sandbox; started on demand; polkit before every method | the specific OS services its operations need | their own APIs |
| System services | root or their own users | the distribution's | | |
| The kernel | | Secure Boot, the signed image | | |

**The one-sentence model:** MIA is as powerful as Zac's own signed-in session and no more; anything beyond that goes
through a root helper that can only do a short list of things, and the operating system asks him each time.

## 2. Why the helper can be small

On a stock Linux desktop the signed-in person can already, without a password: suspend and power off, connect to
networks, pair Bluetooth devices, mount a USB drive, set the power profile, install a Flatpak for himself, read
nearly all system state. Those services each carry their own polkit policy for the active user. **MIA, running as
him, uses them as he would; no helper is involved**, and her own tiers and approvals still apply (a network change
is `act_with_approval` because its reach is the system, REQ-AUT-007).

The helper exists only for what stock Linux would ask an administrator's password for:

| Family | Operations (each a method with typed, fixed-choice arguments) | First release |
|---|---|---|
| OS updates | check; stage the next image; apply at next boot; roll back to the previous deployment; pin a deployment | read-only first (check), then the rest |
| System services | restart one of a *listed* set (the model server, the network, audio for the machine); enable or disable one of that set | later |
| Firewall | open or close MIA's own port on a named zone | with phone access |
| Model server | pull or remove a model in the system store (if the model server's own API doesn't allow it for his user) | early |
| Machine settings | hostname, time zone, locale (through the OS's own settings services) | later |
| Firmware | apply an update fwupd has staged | later |
| Diagnostics | collect a system-level snapshot (the parts his user can't read) | early, read-only |

**Not in the helper, ever:** run a command, write a file by path, install an arbitrary package, add a user, change
polkit rules, change the helper's own list. There is no general-purpose operation to escalate through.

## 3. How a system change is authorised

1. MIA proposes the action in code-written words (`core/actions.py`); its tier is `act_with_approval` (system
   reach); irreversible ones say so (REQ-AUT-006).
2. He approves in MIA (screen or voice, on his own device).
3. The runtime calls the helper's method over the system bus.
4. **polkit decides.** Each method is a polkit action (`org.mia.system.update.apply`, …) whose default is
   "authenticate as an administrator". The desktop's authentication dialog appears, naming the action in plain
   words, drawn by the session's polkit agent, **outside MIA's process**.
5. He confirms there (password, or whatever the system uses). The helper validates the arguments again, performs
   the operation through the owning service, reads the result back, logs it and returns it.

**Why two confirmations aren't redundant.** The first is MIA's (he agreed to what she proposed). The second is the
operating system's, and it is the one that holds if MIA is wrong, confused by something she read, or compromised:
nothing running as his user can fake it. For an AI that may act on a computer, this is the property that matters
most, and Linux provides it for free.

**Making it less tiresome, safely.** polkit can remember an authorisation for a few minutes, and a rule can allow a
specific action for his active local session without a password. Such rules are **files in the image**: changing
one is a commit, a rebuild and a reboot, reviewed like code. MIA has no operation that edits them, so nothing she
reads can talk her into widening her own powers (REQ-SEC-006's spirit, at the OS level). Which actions, if any, he
wants without the dialog is Q-50.

**No remote confirmation of a system change.** polkit's defaults distinguish the person at the machine from a
remote session; a request arriving from the phone can propose a system action but the confirmation happens at the
PC. (Whether that should ever relax is Prompt 13's.)

## 4. The helper's own containment

A root service is the one place a mistake is serious, so its unit is as closed as systemd allows: a read-only view
of the system except the paths its operations need, no new privileges, a minimal capability set, a system-call
filter, no network unless an operation needs it (an image pull does, through the update mechanism itself), private
temporary files. It is small enough to read in one sitting, has no dependency on MIA's engine (it doesn't import
`core/`), and is tested by calling every method with hostile arguments. Its language is open (Python for sameness,
or a compiled language for a smaller attack surface): Prompt 13 decides.

## 5. Narrowing MIA's own reach

The runtime runs as him, so by default the OS would let it read everything he can. Three measures bring that down
to what he granted:

| Measure | What it does | State |
|---|---|---|
| MIA's own checks | the files adapter refuses any path outside granted folders; no tool takes a raw path from a model | the rule exists for the Files app; grants for folders are to build (REQ-FUN-006) |
| **Kernel-enforced, per worker (Landlock)** | a process can give up, irreversibly and without root, access to everything except a list of paths. The worker that reads his documents, her browser's helper and tool workers start with only what they need | **to prove (PoC 6)**: whether it fits Python workers cleanly, and what happens when a grant changes (start a new worker) |
| Unit sandboxing | `NoNewPrivileges`, private temporary files (already in the runtime's unit), more where the user manager supports it | part built |

The runtime's main process can't be narrowed to nothing: it must read and write `MIA_HOME`. That is why records
are also sealed at rest and why code that touches untrusted input (pages, files, captures) should run in workers,
not in the process that holds the keys.

**Mandatory access control:** the base's (SELinux on Fedora, enforcing) stays on. MIA's services start in the
default domains; a dedicated policy for the helper and the runtime is worth writing once their behaviour has
settled (Prompt 13). Nothing in the design requires turning it off or permissive.

## 6. What a compromise of each part would get

| If this is compromised | It gets | It doesn't get |
|---|---|---|
| A web page MIA reads | text in front of a model, marked as outside | any action in that turn; any grant |
| An extension | its declared capabilities, its own folder | his stores' files, the network, other apps |
| A conventional Flatpak app | what its permissions give; it can hand MIA a capture | MIA's API (no token), the socket if its sandbox doesn't expose the runtime directory |
| An ordinary (unsandboxed) app of his | everything his user can read, **including MIA's socket and sealed files' ciphertext** | the unsealing key if the credential is bound to MIA's unit **(to verify)**; root; a confirmed system change |
| The shell or capture agent | a session token: what he can do through MIA, still tiered and approved | direct file access to stores beyond his user's; root |
| The runtime | his records; MIA's ability to propose | root; a system change without his confirmation at the OS's dialog |
| The helper | root | this is the case the design minimises: small, fixed, rarely running |

The fourth row is the honest limit of running as the person: an ordinary program he runs can do what he can. That
is true of every desktop. Sealing, Flatpak for what can be sandboxed, and keeping secrets in the credential store
rather than files narrow it; Prompt 13 takes it further.
