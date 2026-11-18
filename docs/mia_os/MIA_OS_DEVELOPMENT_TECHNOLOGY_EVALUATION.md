# MIA OS: development technology evaluation and decision records (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only. DEC-0262 to 0268 are PROPOSED.*

## 1. Technologies

| Need | Options | Recommendation | Why |
|---|---|---|---|
| Repository | one repo (exists), several | **one** | the layers are enforced; one history |
| Python locking | uv, pip-tools, Poetry | **uv** (`uv pip compile --generate-hashes`) | fast, hashes, plain requirements output |
| Dev containers | Fedora toolbox, devcontainers | **toolbox** on MIA OS; a devcontainer optional | matches the image |
| CI | GitHub Actions (exists) | **GitHub Actions** | already used; free while public |
| Image build | podman + bootc, bootc-image-builder for ISOs | **as planned** | DEC-0189 |
| Signing | cosign (sigstore) | **cosign** | bootc verifies it |
| SBOM | syft | **syft** | standard |
| Provenance | GitHub artifact attestations (SLSA) | **attestations** | built into Actions |
| Parallel tests | pytest-xdist | **xdist**, once tests are checked for shared state | his 16 threads |
| Versioning | CalVer, SemVer | **CalVer** (`2026.11.1`) | releases are monthly snapshots, not APIs |

## 2. Decision records

### DEC-0262: one repository, its layers enforced
Requirements: REQ-DEV-010, 011, 027, 030.

### DEC-0263: a reproducible setup
Requirements: REQ-DEV-012, 013. Hashes, the setup scripts, a toolbox.

### DEC-0264: CI on every push is the gate
Requirements: REQ-DEV-014, 016, 023, 029. Linux and Windows suites, the phone, the image, her changes included.

### DEC-0265: releases built, signed, recorded with an SBOM; versions by date
Requirements: REQ-DEV-021, 022. The phone app's key from secrets (DEC-0160).

### DEC-0266: tests in layers, AI quality included
Requirements: REQ-DEV-015, 017, 018, 019, 026, 028.

### DEC-0267: store formats change additively; otherwise a versioned migration
Requirements: REQ-DEV-020.

### DEC-0268: several models build MIA; independent review; Zac approves decisions
Requirements: REQ-DEV-024, 025.
