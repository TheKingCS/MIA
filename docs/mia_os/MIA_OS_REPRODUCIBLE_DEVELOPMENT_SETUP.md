# MIA OS: a reproducible setup (Prompt 15; DEC-0263)

*Claude (Opus), 2026-11-18. Planning only.*

| Piece | Today | Plan |
|---|---|---|
| Python dependencies | `requirements.txt`, versions | a lock file with hashes (uv or pip-tools); CI installs with `--require-hashes` |
| Python itself | the venv's version | pinned (`.python-version`) |
| System packages | `install.ps1`; `deploy/install_runtime.sh` | the toolbox's Containerfile (Fedora, the image's packages) |
| The phone | Gradle wrapper, pinned plugin versions | the same; Gradle's dependency verification |
| Models | pulled by name | recorded by digest (`ollama show --modelfile`) |
| Data for tests | fixtures in `tests/` | never his real data |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-013 | Python dependencies shall be locked with hashes and CI shall install with hash checking. | Should | R1 | All | New | T | DEC-0263 → 15, 13 |
