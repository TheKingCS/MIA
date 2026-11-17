# MIA OS: security technology evaluation and decision records (Prompt 13 §26)

*Claude (Opus), 2026-11-18. Planning only. DEC-0248 to 0254 are PROPOSED.*

## 1. Technologies

| Need | Options | Recommendation | Why |
|---|---|---|---|
| Password hashing | PBKDF2 (built, 600k), Argon2id, scrypt | **keep PBKDF2 600k; Argon2id when the stores move** | built to OWASP's numbers; Argon2id is stronger against GPUs |
| Store encryption | AES-256-GCM (built), age, SQLCipher | **AES-256-GCM** | built; per-file; nothing new to add |
| Key storage | DPAPI (built), systemd-creds + TPM (built for Linux), Android Keystore, a hardware key | **as built**; a YubiKey optional for the vault | hardware where there is some |
| Disk | LUKS2 + TPM2 (systemd-cryptenroll) | **LUKS2** | Fedora's standard |
| Sandboxing apps | Flatpak/bubblewrap, a separate process per add-on, WebAssembly | **a separate process with only its capabilities**, Flatpak for Linux apps | fits the manifests |
| Service hardening | systemd's options, SELinux | **both** | defaults on Fedora |
| Image signing | cosign/sigstore, GPG | **cosign** (bootc uses it) | |
| Remote access | Tailscale, Headscale | **Tailscale** (Q-88); Headscale if he wants no outside coordinator | |
| Injection defence | marking, structured tool calls, a classifier | **marking + the contract**; a classifier only as an extra signal | authority by design, not detection |
| Audit trail | hash chain, an append-only store | **a hash chain on the security log** | small, checkable |

## 2. Decision records

### DEC-0248: authority comes only from the person
Requirements: REQ-SEC-011, 014, 018, 038. Every change through the one contract; grants only from his acts.

### DEC-0249: everything read from outside is data
Requirements: REQ-SEC-019, 020. Marked at every entry point; no change without a card or his grant.

### DEC-0250: identity in layers; approvals bound and single-use
Requirements: REQ-SEC-012, 013, 016, 017. The OS login, MIA's accounts with two-step away from the PC, device keys,
approvals bound to the proposal, its parameters and the person, used once, expiring.

### DEC-0251: four data classes
Requirements: REQ-SEC-025, 026, 030, 031. Public, personal, sensitive, secret, each with its rules; sensitive never
to a cloud model.

### DEC-0252: encryption in three layers
Requirements: REQ-SEC-028, 029, 037. The drive, each store, each vault; keys in hardware; the recovery key his.

### DEC-0253: least privilege
Requirements: REQ-SEC-015, 021, 022, 023, 036. The runtime unprivileged; the helper; agents read-only; apps by
manifest; add-ons only sandboxed.

### DEC-0254: fail closed for changes; safety outside MIA; an audit trail that can't be rewritten
Requirements: REQ-SEC-033, 034, 035, 039. When a grant or authorization can't be evaluated, the change waits; the
hardware owns safety; the security log is hash-chained; a lockdown in one phrase.
