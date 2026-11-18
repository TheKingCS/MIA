# MIA OS: supply chain security in the build (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only. Requirements: Prompt 13 (REQ-SEC-036).*

| Control | State |
|---|---|
| Dependencies pinned, then pinned by hash | versions yes; hashes to add |
| OSV check weekly (Python) | built; the phone build's to add |
| Workflow actions pinned to commit SHAs | to add |
| Least-privilege CI tokens (`permissions:` per workflow) | to add |
| Signing keys only in GitHub's secrets | the phone app's key waits on Zac's step (DEC-0160) |
| Images signed (cosign) and verified on update | planned |
| SBOM (syft) per artifact | planned |
| Provenance (SLSA level 2 via GitHub's attestations) | planned |
| Commits from known identities; her lab's merges under the owner's identity with the lab's author | built |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-023 | CI workflows shall pin third-party actions to commit hashes and run with the least token permissions they need. | Should | R1 | All | New | T: a test reads the workflows | DEC-0264, DEC-0253 → 15, 13 |
