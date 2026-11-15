# MIA OS: existing security assessment (Prompt 01 §11)

*Claude, 2026-11-15, at `c0a71610`.*

**Public-repository rule.** The repository is public (CLAUDE.md:
"never commit ... a description of a weakness that isn't fixed yet").
This report describes only:
- controls that are in place;
- gaps that are already public in `docs/SECURITY.md` or in code
  docstrings;
- architecture-level gaps that matter for planning.

Specific weaknesses found in this audit were reported to Zac in
conversation and are tracked privately until fixed. **One such finding
(about Android release signing) was reported on 2026-11-15.** No
secrets, tokens or personal data appear here.

## 1. Controls in place

Code-level evidence:

| Control | Evidence | Status |
|---|---|---|
| Password hashing (PBKDF2, 600k) | `core/profile_manager.py`, `docs/SECURITY.md` | Verified (tests) |
| Sign-in guard (lockout) | `core/sign_in_guard.py` | Verified |
| Session tokens, Bearer auth on the API | `server/app.py` `require_profile_id`; of the 265 routes, 7 sit outside the profile dependency (sign-in, setup status and setup, model link, push key, sensor readings, live updates); setup's refusal and live's own token check were read, and the rest weren't reviewed line by line here | Verified (tests) |
| Accounts made only on the device, not over the network | `/api/setup` refuses remote creation ("Accounts are made in MIA on this device.") | Verified |
| Two-step sign-in | `core/two_step.py` | Verified |
| Security log | `core/security_log.py` | Verified |
| Content Security Policy on the web front end | `server/app.py` | Implemented |
| Encryption at rest (AES-256-GCM, key under DPAPI) | `core/at_rest.py` | Verified on the Windows code path; **plain files on Linux and Android** |
| Encrypted password vault, journal, secrets vault | `core/password_vault.py`, `secrets_manager.py` | Verified |
| No secrets in logs | test-enforced | Verified |
| Dependency audit (OSV) | `core/dependency_audit.py` | Implemented |
| MIA drafts email, never sends | `core/email_drafts.py`, `mail_send.py` | Verified |
| Bank access read-only | Plaid | Implemented |
| Browser commit gate; secret fields never typed; page text marked untrusted | `core/browser_safety.py` (`classify`, `untrusted`) | Verified (tests) |
| Network exposure | server on 127.0.0.1; phone through `tailscale serve` | Implemented |
| Development agents: permission tiers, worktree lab, can't merge | DEC-0058, DEC-0069, `core/dev_lab.py` | Implemented |
| Child gating of tools and apps | `core/child_accounts.py` | Verified |

## 2. Where permission is enforced: code or model?

**In code.**
- Tools are attached by code. Actions go through `core/actions.py`, which needs a person's approval for anything sensitive.
- The browser's commit step is approved only by a person.
- The safety floor and the communication gate never consult the model.
- The model can only pick among tools it was given.

This is the right foundation for Prompt 08 and Prompt 13.

## 3. Gaps that matter for MIA OS

Each of these is already public:

1. **Modules and Field Kit scripts run with full app privileges and no sandbox.** This is a documented simplification (CLAUDE.md; the `core/script_runner.py` docstring).
2. **The PC's drive isn't encrypted** (`docs/SECURITY.md`).
3. **No key backend on Linux or Android** (`core/at_rest.py` docstring).
4. **No per-capability grants.** Permission today means the action contract, the person's approval and child gating. There is no general capability or grant model for system-level actions.
5. **No device identity beyond sign-in tokens and the home-link token.** There are no device certificates and no device revocation list as such.
6. **There is no software bill of materials (SBOM), signed artefact or build provenance.**

## 4. Needs further investigation

- Whether the API server's thread restarts safely after an exception (reliability rather than security, but it touches availability).
- A full review of process execution: around 20 core files call `subprocess`, mostly fixed commands. It is planned for Prompt 13 and was not done here.
- The relay's key handling under Meta's toolkit terms.
