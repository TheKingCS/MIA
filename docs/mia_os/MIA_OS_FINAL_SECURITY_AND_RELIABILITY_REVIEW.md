# MIA OS: the final security and reliability review (Prompt 17 §3.9, §3.10)

*Claude (Opus), 2026-11-18. Version 1.0. The whole-system review asked for by Prompt 17, after Codex's F-06 ("controls
specified ahead of their implementation"). The rule from now on: **a control counts as present only when code and an
end-to-end test show it on the target it's claimed for.** Specific unfixed weaknesses are not described here (the
repository is public).*

## 1. Every control and its real state

| Control | Built on Windows (tested) | On the image | Package |
|---|---|---|---|
| Five tiers and grants on every action and tool; a test fails on one without | **yes** | via the suite in the image (FW-02) | — |
| Approve Once / From Now On; grants lapse after 90 days | **yes** | FW-02 | — |
| Approval bound to the card's exact parameters, used once | partly (bound to the proposal) | — | WP-02 |
| Outside content marked as data at every entry | partly (web pages, `untrusted()`) | — | WP-03 |
| Email only drafted; buying, bidding and messaging only on his press | **yes** | FW-02 | — |
| Sealed stores at rest | **yes**: 56 names plus 1 line-sealed; the Linux key backend built | FW-07 opens them on the image | WP-04 (every personal store) |
| The phone's stores sealed by its Keystore | **no** (nothing sealed on the phone yet) | — | WP-10 |
| Two-step sign-in offered | planned (DEC-0250 approved) | — | Alpha, specified when scheduled |
| The lockdown phrase | planned (DEC-0254 approved) | — | WP-01 |
| Security log | **yes**, hash-chained with its head kept on the device that views it (WP-05, 2026-11-22) | FW-02 | done |
| Disk encryption, TPM with PIN, recovery key | — | **no** | FW-05 |
| Secure Boot on Fedora's signed chain | — | **no** | FW-05 |
| The runtime unprivileged | **yes** (a user service) | **yes** (the VM run) | — |
| systemd hardening of the runtime | partly (`NoNewPrivileges`, `PrivateTmp`) | partly | FW-04 |
| Landlock on workers | probe only (PoC 6 passes) | — | Alpha |
| The privileged helper with fixed operations | — | **no** | FW-06 |
| Signed images, the signature enforced | — | **no** | FW-08 |
| Device keys stored as hashes; pairing | **yes** | FW-10 | — |
| Per-device records, scopes, immediate revocation | partly (per profile) | — | WP-10, FW-10 |
| Sensitive data never sent to a cloud | partly (no cloud configured; the refusal in the adapter is planned) | — | WP-03 (REQ-SEC-026), REQ-INT-003 at Alpha |
| Crisis handling independent of the model | **yes** | FW-02 | — |

## 2. Trust boundaries, across the whole system

| Boundary | Enforced by | Gap closed by |
|---|---|---|
| The model ↔ MIA's authority | code: tiers, grants, the action contract; the model only proposes | WP-02, WP-03 |
| MIA ↔ the OS | MIA is unprivileged; changes only through the helper and polkit | FW-06 |
| The person ↔ the machine | the OS's login (PAM); the disk unlock | FW-05 |
| Devices ↔ the hub | paired keys, hashes on the hub | WP-10, FW-10 |
| Outside content ↔ the model | marked as data; no proposal runs on its own | WP-03 |
| Updates ↔ the machine | signatures enforced, automatic rollback | FW-04, FW-08 |
| The repository ↔ the public | nothing personal, secret or describing an unfixed weakness committed; `audit/` kept local | a test of committed files for personal paths (FW-02); G-14 fixed |

## 3. Reliability, across the whole system

| Failure | What happens | Proven? |
|---|---|---|
| MIA's runtime crashes | systemd restarts it, at most three times in a row, then the shell's recovery page | restart limits in the unit; the recovery page in FW-03 |
| The shell crashes | it restarts by itself; his other windows stay; Plasma one choice away | FW-03 |
| Models unavailable, cloud unavailable | MIA answers from code-assembled facts and says the model is away; the desktop works | FW-12; the engine's behaviour is tested on Windows |
| A bad update | greenboot rolls it back; the previous deployment in the boot menu | **headless rollback proven** (VM run); automatic rollback in FW-04 |
| A damaged store | atomic writes; the history; nightly backups; the restore drill | WP-09 |
| The disk unlock fails | the recovery key | FW-05 |
| The internal OS won't boot at all | the USB recovery stick | FW-09 |
| Power loss | atomic writes; the UPS when bought | partly |
| The PC lost | the off-PC backup; the phone's own copy | WP-09 |

## 4. Verdict

Security: **ready with conditions.** The model-to-authority boundary is strong and tested. The OS-level controls (disk,
Secure Boot, the helper, signatures) don't exist yet, and the move is gated on FW-05 and FW-06 passing.

Reliability: **ready with conditions.** Rollback is proven headless. Automatic rollback, the graphical fallback and USB
recovery are FW-03, FW-04 and FW-09.
