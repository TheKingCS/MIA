# MIA OS: Linux privilege and system security (Prompt 13 §11)

*Claude (Opus), 2026-11-18. Planning only. The OS: DEC-0189 to 0195.*

| Control | On MIA OS |
|---|---|
| The runtime | a systemd **user** service, unprivileged; `ProtectSystem=strict`, `ProtectHome=read-only` except his MIA folders, `NoNewPrivileges`, `PrivateTmp`, a seccomp filter |
| System changes | only through the fixed-operation helper (DEC-0194): a short list of operations, each confirmed in the OS's own polkit dialog |
| The image | Fedora Atomic, read-only `/usr`, updated whole, signed (Prompt 14) |
| SELinux | enforcing (Fedora's default) |
| Firewall | firewalld: nothing listening on the outside; Tailscale's interface for his devices |
| Flatpak apps | their own sandboxes and portals |
| Secrets | systemd credentials (TPM-bound) for the data key |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-022 | MIA's runtime shall run unprivileged with systemd's sandboxing, and change the system only through the helper's fixed operations, each confirmed in the OS's own dialog. | Must | MVP | PC | Partial (FW-06's helper checked in the VM; the runtime's own sandboxing is PoC 6) | D: PoC 5, 6 | DEC-0194, DEC-0253 → 13, 05 |
