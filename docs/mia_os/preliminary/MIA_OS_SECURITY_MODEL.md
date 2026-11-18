# MIA OS security model

> **Prompt 17 (2026-11-18):** superseded by Prompts 01 to 17 and kept for history only; `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs.

*Claude, 2026-11-13. Builds on `docs/SECURITY.md` (what's in place
today); this covers what changes when MIA can act on the system.*

## 1. Principles

1. **MIA proposes; code decides; a person approves.** No OS action runs on
   model text alone (DEC-0004, DEC-0009). The model can pick a tool. Only
   code checks the capability and the grant.
2. **Least privilege by layer.**
   - MIA Core runs as the person's user, never as root.
   - Root-level work goes through the System Manager's fixed D-Bus
     methods, authorised by polkit.
3. **Default deny for system capabilities.** Everything starts at
   **observe** or **never**; a person raises it.
4. **Everything is recorded.** Each action goes to the life events and the
   security log. Undo is offered where possible, and an honest "can't
   undo" is shown where it isn't.
5. **Untrusted text stays untrusted.** Web pages, emails, documents and
   tool output reach the model through `untrusted()` and can never grant
   or raise a capability (DEC-0117).

## 2. Identities

| Identity | Runs as | Can |
|---|---|---|
| The person | their OS user | everything they could do by hand |
| MIA Runtime | the person's user (systemd user service) | own the stores, serve the API, run jobs |
| System Manager | root, separate process | only its listed methods, each checked by polkit |
| Agents (council, dev lab, workers) | sandboxed (podman/bubblewrap), no network unless granted | work in their worktree; propose |
| Modules from others | sandboxed (Flatpak-style) | their declared capabilities only |
| Model server | its own system user | serve the model; no data access |

## 3. Capability tiers

These are the tiers used in the target architecture, and they match the
development platform's (DEC-0069):

| Tier | Meaning | Examples |
|---|---|---|
| observe | read-only | list processes, read disk use, see the focused app |
| suggest | propose only | "you have 3 updates" |
| act-with-approval | runs after a tap or a spoken yes | launch an app, stop a process, apply an update |
| act-within-grant | runs inside a standing grant, logged | "always pause updates while I'm gaming" |
| never | no grant can raise it | send email, type a password, buy, change sign-in or security settings, disable the log |

A spoken approval counts only for the person's own voice on their own
device, and never for the "never" tier or for security settings.

## 4. Data at rest and in transit

- Disk: LUKS2, unlocked by TPM2 plus a PIN.
- MIA's sealed stores: AES-256-GCM (as today), with keys under TPM2 via
  systemd-creds on Linux, DPAPI on Windows and Keystore on Android.
- Backups: encrypted with the backup passphrase (as today).
- Network:
  - the API listens on 127.0.0.1 and a local socket;
  - the phone reaches it through Tailscale only;
  - the relay sees only sealed payloads.

## 5. The update chain

- The image is built in CI from files in the repo.
- It is signed (cosign), and bootc verifies the signature before staging.
- Rollback is one command, or automatic on a failed boot.
- MIA can **suggest** updates and, with a grant, **stage** them. She never
  reboots without a person's say.

## 6. Threats and responses

| Threat | Response |
|---|---|
| Prompt injection from a page or email asking MIA to do something | untrusted text can't grant; system tools need approval; "never" tier |
| A bad tool call from the model | code checks capability and grant; undo |
| A malicious module | sandbox; declared capabilities; validator |
| Stolen laptop/PC | LUKS2 + TPM2; sealed stores; sign-in |
| Someone else speaking to MIA | voice approval only for "act-with-approval", only on the person's device; speaker ID later |
| Compromised update | signed images; rollback |
| A compromised agent | sandbox, no network by default, works in a worktree, can't merge (DEC-0058) |
| Root compromise via the helper | small fixed method list; polkit; no shell passthrough; tests per method |

## 7. Open security questions

Listed in `MIA_OS_OPEN_QUESTIONS.md` (PIN vs password at boot, voice
approvals, remote access policy).
