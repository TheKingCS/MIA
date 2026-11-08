# MIA's security: what protects your data, and the plan to go further

*Claude, 2026-11-08, at Zac's ask: "fortify our security measures to industry standards and beyond so that users can
safely trust this AI and the app having access to their most private data." The standards: OWASP's Application
Security Verification Standard (ASVS 4), its Password Storage, Session Management and Secure Headers guidance, and
NIST SP 800-63B for passwords. Keep this file true: a change to how data is protected changes it.*

## 1. What we protect, and from whom

MIA holds a person's whole life: money, health, journals, messages, photos, passwords, where they go. The threats,
most likely first:

1. **Someone on the network guessing their way in** (another device on the Tailscale network, a phone left signed in).
2. **A lost or stolen device or drive**, read directly.
3. **MIA herself doing something unasked** (a model mistake, a web page or email trying to steer her).
4. **Secrets leaking into places they shouldn't** (logs, the repo, chat, the glasses' display, a spoken reply).
5. **A malicious add-on or dependency.**

## 2. In place today

| Area | Protection | Where |
| --- | --- | --- |
| Where data lives | On the person's own PC and phone; the AI model runs locally (Ollama); `data/` and the config never go in the repo | `.gitignore`, `core/llm_manager.py` |
| Who can connect | The server listens on 127.0.0.1 only; the phone comes in through Tailscale; with phone access off, anything forwarded is refused | `core/phone_server.py`, `server/app.py` |
| Account passwords | PBKDF2-HMAC-SHA256, **600,000 rounds** (OWASP 2023), per-password salt, constant-time compare; older hashes upgraded on the next sign-in | `core/profile_manager.py` |
| Guessing | **Five free tries, then a wait that doubles** (30 s up to 15 min), by account and by device, on sign-in, phone linking, password change and new recovery codes | `core/sign_in_guard.py` |
| Sessions | 256-bit random tokens; **end after 30 days unused or 90 days in all**; logging out ends one; **changing the password ends all the others** | `server/app.py`, `core/sign_in_guard.py` |
| Browser protections | **Content-Security-Policy** (only MIA's own scripts, nothing loaded from elsewhere), no framing by other sites, no MIME sniffing, no referrer, camera and microphone for MIA only, API answers never cached | `server/app.py` `SECURITY_HEADERS` |
| Passwords app | AES-256-GCM, a random 256-bit vault key wrapped by the master password and a recovery code (scrypt), each login encrypted on its own, auto-lock, a doubling wait on wrong guesses | `core/password_vault.py` |
| Private journal | Encrypted, opened only by its own passphrase | `core/private_journal.py` |
| Bank and mail credentials | Encrypted vault (Fernet with PBKDF2); never in actions, logs, exports or the undo log | `core/secrets_manager.py` |
| Backups | Encrypted when given a passphrase | `core/backup_manager.py` |
| Secrets never by voice | Passwords, PINs, codes and card numbers are never spoken, heard, shown on the glasses or remembered by voice (DEC-0125) | `core/assistant_more_twins_actions.py` |
| MIA can't act unasked | Email is only drafted (Send is a person's press); bank data is read-only; her browser holds anything that commits for a person's OK and never types into a password field; unprompted messages pass a gate; every change is undoable | `core/email_drafts.py`, `core/browser_safety.py`, `core/communication_gate.py`, `core/undo_log.py` |
| Reach | Files only inside the person's own MIA folder; cameras only on the home network; each person's data in their own folder, shared only by joining a household with approval | `core/my_files.py`, `core/security_cams.py`, `core/personal_data.py` |
| Two-step sign-in | An authenticator app's code after the password, from any device but the PC; codes never reused | `core/two_step.py` |
| Security log | Every sign-in with its device, wrong passwords, account changes; alerts on a new device and repeated wrong passwords; Sign Out Everywhere | `core/security_log.py` |
| Code hygiene | A test keeps control characters out of code (a mangled `\b` once silently disabled a check) | `tests/test_no_control_characters.py` |

## 3. Honest gaps

- **Most data is not encrypted on disk.** Bills, calendar, notes, memories, conversations and the rest are plain
  JSON in `data/`. **This PC's drive isn't encrypted either** (checked 2026-11-08: Windows 11 Home, BitLocker
  protection 0). Anyone who can read the drive or the Windows account can read them.
- **Add-on modules aren't sandboxed**: an installed module runs with full access.
- **Some features talk to outside services by nature**: Plaid (the bank), the email provider, websites her browser
  visits, public news feeds, and the owner-only developer council (cloud AI accounts).
- **Dependencies aren't checked for known vulnerabilities** automatically.

## 4. The plan (in order)

1. **Encrypt the drive (Zac, now).** Settings → Privacy & security → Device encryption, if offered on this PC;
   otherwise Windows 11 Pro's BitLocker (an upgrade) or VeraCrypt (free). The biggest single step, and it covers
   everything at once. ⏸
2. **MIA encrypts her own data at rest (DEC-0126, approved; stage 1 done 2026-11-08).** `core/at_rest.py` seals
   conversations, memories, notes, life notes, people and pets, finances, insurance, GPS tracks and the operating
   journal now (the budget's files next, after the Plaid work); `python -m tools.data_key` shows the state, `recovery` the key
   to keep in a password manager. The plan: every store's file encrypted with AES-256-GCM under
   one data key; the data key protected by Windows DPAPI (tied to the person's Windows sign-in, so nothing to type
   at start) on the PC and by the Android Keystore on the phone, with an optional MIA passphrase for "beyond".
   Done in the one place every store already writes through (`core/atomic_write.py`) plus a matching read, store by
   store, the most private first (journal, conversations, memories, money, people). A copied `data/` folder, a
   backup or a synced file is then unreadable on its own. ⏸
3. ~~**A security log and alerts.**~~ **Done 2026-11-08** (`core/security_log.py`, Settings → Sign-ins and
   Security): every sign-in with its device, wrong passwords, waits, ended sessions, password and recovery code
   changes and phone links, append-only and outside the undo log; an alert on a sign-in from a new device, on
   repeated wrong passwords, a password change and a linked phone; Sign Out Everywhere. Still to add: exports and
   imports in the log.
4. ~~**Two-step sign-in for remote access.**~~ **Done 2026-11-08** (`core/two_step.py`, Settings → Sign-ins and
   Security): TOTP (RFC 6238) codes from any authenticator app, asked after the password for every sign-in that
   isn't the PC itself (and for linking a phone); on only once a code is confirmed; a used code never works twice;
   wrong codes count toward the wait; the recovery code still gets you in and turns it off. Still to add: a QR code
   for setup (no QR library yet; the key and an otpauth link work today).
5. ~~**Dependency checks.**~~ **Done 2026-11-08** for Python (`tools/dependency_audit.py`, `core/dependency_audit.py`):
   every installed package and version is checked against OSV (the database pip-audit uses) once a week in a process
   of its own; findings come through the communication gate with the version that fixes each one. Only package names
   and versions leave the PC. Run it any time: `python -m tools.dependency_audit`. Still to do: the Android build's
   dependency report.
6. ~~**Logs kept clean by test.**~~ **Done 2026-11-08** (`tests/test_no_secrets_in_logs.py`): every logging call in
   MIA is read as code and fails the suite if it passes a value named like a secret; and a run through sign-in, a wrong
   password, two-step setup, a new recovery code and a password change checks that none of those secrets appears in
   any log line (`tests/test_server_app.py`).
7. **Modules signed or reviewed** before they install; until then, only modules written here.
8. **"Beyond"** (Your Data page done 2026-11-08, `core/your_data.py`, `web/yourdata.html`, Settings → Your Data):
   every file MIA keeps about you shown with what it is, how many records and whether it's sealed, plus what she read
   to answer your recent questions (from the traces); export and delete-your-account on the web behind your password,
   real and tested (`core/account_data.py`). Still to do: a yearly review of this file against the latest OWASP ASVS.

⏸ marks a step waiting on Zac.
