# MIA OS: boot integrity and safe recovery (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only. Security: Prompt 13.*

| Control | How |
|---|---|
| Secure Boot | on; Fedora's signed shim, kernel and boot loader |
| The disk key bound to the boot | TPM2 PCR policy (systemd-cryptenroll): a changed boot chain asks for the recovery key |
| A signed image | cosign signature verified before an update is staged |
| Recovery doesn't bypass encryption | safe mode and the previous deployment still need the disk unlocked; a live USB needs the recovery key |
| The recovery key | his, offline; never in chat or the repo |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-034 | An update shall be staged only if its image's signature verifies, and no recovery path shall open his data without the disk key or the recovery key. | Must | MVP | PC | Planned | T | DEC-0252, DEC-0257 → 14, 13 |
