# MIA OS: virtualization and isolation (Prompt 06 §12)

*Claude (Opus), 2026-11-17. Planning only. Sandboxing policy is Prompt 13's; this sets what the hardware supports.*

| Need | Mechanism | Hardware support | Status |
|---|---|---|---|
| Test MIA OS images | KVM with QEMU (libvirt or GNOME Boxes) | AMD-V on the 9800X3D (verify it's on in the BIOS) | used in GitHub's runners (PoC 2) |
| The lab's code changes | a git worktree and the test suite (DEC-0058) | none special | built |
| Untrusted app code | Flatpak and bubblewrap; Landlock for her own sub-processes | kernel features | Landlock tested (PoC 6) |
| Model runners | a systemd service with its own cgroup; containers optional | — | PoC 4 (the runtime) |
| The Workroom's parallel browser agents | separate browser contexts in one process, each its own profile directory | none | DEC-0199 (W2) |
| Parallel desktop apps (later) | nested KWin sessions or small VMs, one per agent | KVM; GPU stays with the host | DEC-0199 (W3) |
| GPU in a VM | not recommended: one consumer card can't be shared well (no SR-IOV on the 7900 XTX) | none | rejected |

**Isolation rule:** anything that runs code MIA didn't write runs out of process and sandboxed (DEC-0176); the GPU
stays with the host and is reached through the model runner's API, never passed into a sandbox.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-023 | The PC shall run a MIA OS test machine (KVM) for image updates and the acceptance list before they reach the real install. | Must | R1 | PC | Partial (GitHub's runners) | M: a local VM boots the image | DEC-0189, → 14, 15 |
