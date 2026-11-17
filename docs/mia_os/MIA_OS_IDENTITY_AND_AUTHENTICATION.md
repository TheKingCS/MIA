# MIA OS: identity and authentication (Prompt 13 §5; DEC-0250)

*Claude (Opus), 2026-11-18. Planning only.*

| Moment | How | Exists |
|---|---|---|
| Setting up the OS | Linux user and password; the disk unlocked by the TPM (LUKS2) | planned (MIA OS) |
| Logging in | the OS's login (PAM); MIA's own sign-in is a person selector inside it, not a second machine password (REQ-FUN-002) | planned |
| MIA's own accounts | email + password (PBKDF2 600k), two-step (TOTP) away from the PC, recovery codes | yes |
| Pairing a device | his password once → a device key (DEC-0242) | yes |
| Away from home | Tailscale, then MIA's own session | yes |
| An app | runs as him inside MIA, limited by its manifest's permissions | partial |
| An agent | runs as the person who started its run, with read-only tools | yes (DEC-0219) |
| Administration | the OS's own dialog, his Linux password | planned |
| Recovery | recovery codes for MIA; the recovery key for sealed data (kept by him, offline) | yes |
| A new device | pair, sync fills it | yes |

**Sessions:** 256-bit tokens; end after 30 days unused or 90 in all; a password change ends the others. **Approvals**
are their own thing (DEC-0250): see the approval framework.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-012 | Every sign-in away from the PC itself shall need the second step once it's set up. | Must | MVP | All | Exists | T | DEC-0250 → 13 |
| REQ-SEC-013 | On MIA OS, the machine's login shall be the OS's own; MIA shall never keep a second password for the machine. | Must | MVP | PC | Planned | D | DEC-0250, REQ-FUN-002 → 13, 14 |
