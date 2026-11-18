---
id: K-0295
kind: implementation
title: The MIA OS image's Python packages are hash-locked from requirements.txt
status: confirmed
by: claude
created: 2026-11-18T10:19:04+00:00
concerns: os/Containerfile, os/requirements.lock, requirements.txt
from: task:FW-01, dec:DEC-0263, dec:DEC-0279, file:os/lock_requirements.py
---
FW-01 (2026-11-18). os/lock_requirements.py writes os/requirements.lock and os/requirements-build.lock with uv for Python 3.13 on x86_64-manylinux_2_39 (Fedora 45's glibc is newer; manylinux_2_28 resolved PySide6 back to 6.9.3 because 6.12's Linux wheels need a newer tag). The Containerfile installs the build lock first (setuptools, wheel), then the main lock with --require-hashes, --no-build-isolation and --only-binary :all: except the three packages that publish no wheel (plaid-python, http-ece, srt), so pip never fetches an unchecked build tool. piper-tts is left out (Zac's Q-108: GPL-3.0, not bundled until the repository has a licence); MIA falls back without it. uv's 'via' annotations are turned off because they name a temporary file's path, which once put a Windows user folder into the lock. After changing requirements.txt, run the script; tests/test_os_image.py fails until the lock covers the change.
