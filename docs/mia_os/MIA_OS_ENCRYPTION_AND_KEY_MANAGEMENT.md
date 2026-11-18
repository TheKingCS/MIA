# MIA OS: encryption and keys (Prompt 13 §16; DEC-0252)

> **Prompt 17 (2026-11-18):** the disk unlock is LUKS2 with the TPM bound to PCR 7 plus a PIN and a printed LUKS recovery key (DEC-0277); "MIA's recovery key" means only the data key's backup. The phone seals nothing at rest yet (`core/at_rest.py`): its Keystore step is planned (WP-10), not built.

*Claude (Opus), 2026-11-18. Planning only.*

| Layer | What | Key held by | State |
|---|---|---|---|
| Drive | LUKS2 (MIA OS); Device Encryption or BitLocker on Windows; the phone's own | TPM (PC), Android | planned (MIA OS); Windows: his step (`docs/SECURITY.md` §4) |
| Stores | AES-256-GCM per file (`core/at_rest.py`) | the data key, wrapped by DPAPI (Windows), systemd-creds with the TPM (Linux), the Android Keystore | built (56 files; the rest to follow) |
| Vaults | passwords (AES-256-GCM, scrypt-wrapped), credentials (Fernet, PBKDF2), the private journal (its passphrase) | his master password or passphrase, recovery codes | built |
| Backups | encrypted with a passphrase | his passphrase | built |
| In transit | WireGuard (Tailscale); TLS on the home network | per device | partial |
| The recovery key | the data key's backup | **him, offline** (never in chat, never in the repo) | built |

**Rotation:** the data key re-wrapped on a password or machine change; a vault's key re-wrapped on a new master
password; device keys replaced by re-pairing.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-028 | Every store holding personal, sensitive or secret data shall be sealed at rest. | Must | MVP | All | Partial | T: a test over the classes | DEC-0252, DEC-0126 → 13 |
| REQ-SEC-029 | MIA OS shall encrypt the whole drive with LUKS2, unlocked by the TPM. | Must | MVP | PC | Planned | D | DEC-0193, DEC-0252 → 13, 14 |
