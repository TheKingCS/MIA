---
id: K-0263
kind: test-procedure
title: MIA OS proofs of concept on GitHub's Linux machines: what they showed
status: confirmed
by: claude
created: 2026-11-16T09:36:01+00:00
concerns: os/Containerfile, os/poc/landlock_probe.py, os/poc/gpu_bench.py, .github/workflows/mia-os-poc.yml, core/voice_manager.py, deploy/install_runtime.sh
from: dec:DEC-0189, dec:DEC-0194, dec:DEC-0155
---
What: .github/workflows/mia-os-poc.yml runs, on changes to os/, the runtime's unit and installer, four jobs: landlock (os/poc/landlock_probe.py: a worker restricts itself with Landlock through ctypes syscalls 444 to 446, then tries paths), runtime-service (deploy/install_runtime.sh on a runner with lingering, then waits for 'The MIA Runtime is up' in MIA_HOME/logs/mia.log and stops it with systemctl), suite-linux (the whole suite on Python 3.13), image (podman builds os/Containerfile from a git archive of tracked files, then lists the packages). The graphics card test is os/poc/gpu_bench.py with steps in os/poc/README.md, for Zac at the PC.

Results 2026-11-16: Landlock ABI 8 on kernel 7.0, every check as promised, 6% slower opens. Fedora 45's quay.io/fedora-ostree-desktops/kinoite:45 builds with python3.13, ollama 0.24.0, ollama-rocm (ROCm 7.2.2; it pulls ollama-vulkan in too), cage 0.3.1, kernel 7.3.3, and passes bootc container lint. The runtime came up as a user service with 95 services, 429 tools, 11 jobs.

What went wrong: (1) sounddevice raises PortAudioError (a plain Exception subclass) at import when PortAudio is present but no sound server runs; core/voice_manager.py caught only ImportError and OSError, so the runtime and fourteen test files failed to import on Linux. Now any exception there means no voice. (2) A sun-time test assumed an American time zone; the runner is UTC. (3) The image's import check ran from / instead of /usr/lib/mia. (4) Job logs: gh run view --log is unavailable until the whole run ends; fetch a finished job's log with curl and gh auth token from the API's /actions/jobs/<id>/logs.

Never build the image from a working folder: it may hold personal data that git ignores but a container build copies into a layer. The workflow builds from git archive, and .containerignore guards a second time.
