# MIA OS: tasks for the first packages (Prompt 16)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18. The rest are broken down when their package starts, on the task board.*

| Package | Tasks |
|---|---|
| WP-01 Lockdown | the phrase in `core/stop.py`'s words; sign out every session and device key; lock the vaults; pause outreach and the lab; a Settings button; unlock with his password; tests |
| WP-02 Approval binding | store a hash of the card's parameters at propose; check it at approve; refuse a changed proposal; tests for replay and edits |
| WP-03 Injection | mark email, documents, the UAL selection, workspace notes like web pages; a test set of 20 poisoned inputs; no change without a card |
| WP-04 Sealing | classify every store (public, personal, sensitive, secret); a test that every personal-or-above store is sealed; add the missing names |
| WP-09 Restore drill | restore into a scratch folder; open every store; compare counts; report in Diagnostics; monthly job |
| WP-11 CI | a Linux suite workflow; `uv pip compile --generate-hashes`; actions pinned to SHAs; `permissions:` on each |
| WP-13 PoC 1 | Zac: the USB stick, boot, run `os/poc/gpu_bench.py`; Claude: read the numbers |
| WP-14 Image in a VM | the VM workflow boots the image; checks SDDM, the runtime's readiness, runs the suite inside |
