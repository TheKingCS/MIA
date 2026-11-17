# MIA OS: security, privacy and permissions (Prompt 13)

*Claude (Opus), 2026-11-18, on Zac's go ("Let's do Prompt 13"). Planning only: no credential, key, permission or
security control was changed. The prompt is `prompts/13_SECURITY_PRIVACY_PERMISSION_ARCHITECTURE.md`. Twenty-nine
documents sit beside this one (section 9). **The repository is public**: these documents describe the design and its
requirements; specific weaknesses found while auditing are kept on the PC only, in `audit/` (git-ignored), and fixed
before they're described here.*

## 1. The headline

1. **Much of MIA's security is built and measured** (`docs/SECURITY.md`, to OWASP ASVS 4 and NIST SP 800-63B):
   passwords hashed with 600,000 rounds, a doubling wait on wrong guesses, two-step sign-in for every device but the
   PC, sessions that end, a security log with alerts, a Content-Security-Policy, encrypted vaults for passwords,
   the private journal and credentials, 56 store files sealed at rest, a weekly dependency check, tests that keep
   secrets out of logs, and Sign Out Everywhere. **The plan builds on it.**
2. **Authority comes only from the person** (DEC-0248). Everything MIA reads (web pages, documents, email,
   messages, model output, another agent's notes) is data, marked as such, and can't approve, grant or choose a
   change; every change is an action on one contract with a tier, a card and an undo; nothing she reads can grant
   her anything (DEC-0156).
3. **Approvals can't be replayed** (DEC-0250): an approval is bound to one proposal, its exact parameters and its
   person, used once and expiring.
4. **Data has four classes with rules for each** (DEC-0251): public, personal, sensitive (health, money, journal,
   location, relationships), secret (passwords, keys, codes). Sensitive data never goes to a cloud model; personal
   only on his yes for that request, minimised.
5. **Encryption in three layers** (DEC-0252): the drive (LUKS2 on MIA OS), each store sealed (AES-256-GCM, keys in
   the TPM or Windows DPAPI or the Android Keystore), and each vault under its own key; the recovery key held by him,
   offline.
6. **Least privilege everywhere** (DEC-0253): the runtime unprivileged, system changes only through the
   fixed-operation helper with the OS's own password dialog, agents with read-only tools, apps limited to their
   manifest's permissions, third-party add-ons only once sandboxed.
7. **When security can't decide, nothing changes** (DEC-0254): a grant or authorization that can't be evaluated
   means the action waits; physical safety lives in hardware and controllers, never in MIA; the audit trail can't be
   rewritten.

## 2. The audit (2026-11-18)

| Area | Built | Where |
|---|---|---|
| Accounts and sign-in | PBKDF2-SHA256 600k, the guessing wait, two-step (TOTP), recovery codes, sessions ending at 30 days unused / 90 days | `core/profile_manager.py`, `core/sign_in_guard.py`, `core/two_step.py`, `server/app.py` |
| Devices | per-device keys (hash only on the PC), unlink, Sign Out Everywhere | `core/home_link.py`, `core/linked_devices.py` |
| Sensors | one-series keys, rate-limited | `core/sensors.py` |
| Changes | the action contract, tiers in every manifest, grants, Approve From Now On never for money, messages, publishing, deletion outside undo or system changes | `core/actions.py`, `core/grants.py`, `core/kind_grants.py` |
| Her own code | the lab: protected files, suite before and after, automatic revert, Claude's inspection | `core/dev_lab.py`, `core/self_merges.py` |
| Content from outside | web pages marked as data (`untrusted`), commits only on a person's press, secret fields never typed | `core/browser_safety.py` |
| Email | drafted only; Send is a person's press | `core/email_drafts.py`, `core/mail_send.py` |
| Data at rest | 56 store files sealed (AES-256-GCM), the data key under DPAPI / systemd-creds with the TPM; vaults with their own keys | `core/at_rest.py`, `core/key_unlock.py`, `core/password_vault.py`, `core/secrets_manager.py` |
| Logs | append-only security log; tests keep secrets out of every log call | `core/security_log.py`, `tests/test_no_secrets_in_logs.py` |
| Supply chain | weekly OSV check of installed packages | `core/dependency_audit.py` |
| The stop | "stop everything" holds her own work and outreach | `core/stop.py` |
| Safety | the crisis floor in code; the greenhouse's safety MCU | `core/safety_floor.py`, `homestead/` |
| Privacy screens | Your Data: every store, sealed or not, export and delete | `core/your_data.py` |

**Gaps, in general terms** (the specifics are in `audit/`): not every store is sealed yet; this PC's drive isn't
encrypted (`docs/SECURITY.md` §3); add-on modules aren't sandboxed, so only modules written here are installed;
the Android build's dependencies aren't yet checked.

## 3. Trust boundaries (detail in `MIA_OS_SECURITY_TRUST_BOUNDARIES.md`)

The person → his devices → MIA's runtime → her stores; content from outside → the model → proposals → the action
contract → stores, the OS (through the helper), devices (through their own interfaces). Authority crosses only on
the person's side.

## 4. Decisions (records in `MIA_OS_SECURITY_TECHNOLOGY_EVALUATION.md` §2)

| DEC | Decision | Status |
|---|---|---|
| DEC-0248 | Authority comes only from the person; every change through the one contract | PROPOSED |
| DEC-0249 | Everything read from outside is data, marked, and can't steer a change | PROPOSED |
| DEC-0250 | Identity in layers, and approvals bound to one proposal, used once, expiring | PROPOSED |
| DEC-0251 | Four data classes with rules for storage, sync, models, display and voice | PROPOSED |
| DEC-0252 | Encryption in three layers; keys in hardware where there is some; the recovery key his | PROPOSED |
| DEC-0253 | Least privilege for the runtime, agents and apps; add-ons only once sandboxed | PROPOSED |
| DEC-0254 | Fail closed for changes; physical safety outside MIA; an audit trail that can't be rewritten | PROPOSED |

## 5. Questions for Zac

`MIA_OS_SECURITY_OPEN_QUESTIONS.md`: Q-91 (sensitive data never to a cloud model, even on a yes), Q-92 (two-step
required for every device away from the PC), Q-93 (an emergency lockdown phrase), Q-94 (add-ons only from MIA's
own repository until sandboxing).

## 6. Boundaries

Prompt 14 updates, boot and recovery; Prompt 15 build and signing infrastructure; Prompt 16 the order.

## 7. Sources

`docs/SECURITY.md`; the repository, read 2026-11-18; DEC-0126, 0156, 0158, 0169, 0181, 0185, 0194, 0215, 0225,
0242; OWASP ASVS 4, OWASP LLM Top 10 (2025), NIST SP 800-63B, NIST SP 800-207 (zero trust).

## 8. What it means for him

Nothing MIA reads can make her act; everything she does on her own is a change he can see and undo; his private
things stay on his devices, encrypted, and never go to a cloud model; a lost device is cut off from anywhere.

## 9. The documents

`MIA_OS_THREAT_MODEL.md`, `MIA_OS_SECURITY_TRUST_BOUNDARIES.md`, `MIA_OS_IDENTITY_AND_AUTHENTICATION.md`,
`MIA_OS_AUTHORIZATION_AND_PERMISSION_FRAMEWORK.md`, `MIA_OS_ACTION_RISK_AND_APPROVAL_FRAMEWORK.md`,
`MIA_OS_CONSENT_AND_DELEGATED_AUTHORITY.md`, `MIA_OS_AI_SECURITY_AND_PROMPT_INJECTION_DEFENSE.md`,
`MIA_OS_AGENT_SECURITY_AND_EXECUTION_BOUNDARIES.md`, `MIA_OS_LINUX_PRIVILEGE_AND_SYSTEM_SECURITY.md`,
`MIA_OS_APPLICATION_AND_PLUGIN_SECURITY.md`, `MIA_OS_DISTRIBUTED_DEVICE_SECURITY.md`,
`MIA_OS_DATA_CLASSIFICATION_AND_PRIVACY.md`, `MIA_OS_MEMORY_PRIVACY_AND_USER_CONTROL.md`,
`MIA_OS_ENCRYPTION_AND_KEY_MANAGEMENT.md`, `MIA_OS_SECRETS_AND_CREDENTIAL_MANAGEMENT.md`,
`MIA_OS_SENSOR_AND_PHYSICAL_PRIVACY.md`, `MIA_OS_HOUSEHOLD_PRIVACY_AND_ACCESS_CONTROL.md`,
`MIA_OS_PHYSICAL_DEVICE_SAFETY_ARCHITECTURE.md`, `MIA_OS_SECURITY_AUDIT_AND_ACCOUNTABILITY.md`,
`MIA_OS_SECURITY_MONITORING_AND_INCIDENT_RESPONSE.md`, `MIA_OS_SECURE_SUPPLY_CHAIN_REQUIREMENTS.md`,
`MIA_OS_BACKUP_AND_DATA_PROTECTION_REQUIREMENTS.md`, `MIA_OS_SECURITY_TESTING_AND_VERIFICATION.md`,
`MIA_OS_SECURITY_TECHNOLOGY_EVALUATION.md`, `MIA_OS_SECURITY_ARCHITECTURE_DIAGRAMS.md`,
`MIA_OS_SECURITY_SCENARIO_ANALYSIS.md`, `MIA_OS_SECURITY_ACCEPTANCE_CRITERIA.md`, `MIA_OS_SECURITY_OPEN_QUESTIONS.md`,
`MIA_OS_SECURITY_RISK_REGISTER.md`.
