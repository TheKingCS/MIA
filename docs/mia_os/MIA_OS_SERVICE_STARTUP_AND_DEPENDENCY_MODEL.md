# MIA OS: services and their order (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only. Services: `MIA_OS_SYSTEM_SERVICE_ARCHITECTURE.md` (Prompt 05).*

| Unit | Kind | Wants / After | Needed by | Without it |
|---|---|---|---|---|
| `ollama.service` | system | network-online (not required) | the runtime's answers in words | everything but words |
| `mia-helper.service` | system, socket-activated | polkit | system changes | none until asked |
| `mia-runtime.service` | his user service (lingering, so it runs signed out) | ollama (Wants, not Requires) | the shell, the phone, the display | the conventional desktop still works |
| `mia-shell.service` | his user service in MIA's session | mia-runtime (Wants; it shows "starting" until ready) | — | Plasma |
| `tailscaled.service` | system | network | away access | home network only |
| `mia-node-link.timer` | his user timer | mia-runtime | the greenhouse view | the greenhouse runs anyway |

**Rule:** "Wants", never "Requires", between MIA's parts and anything optional, so a missing model server or network
never stops the runtime (REQ-REL-001, 002). **Nothing of MIA's in the boot path** before login.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-017 | No MIA unit shall be required for the system to boot or for login, and her units shall only Want, never Require, optional services. | Must | MVP | PC | Planned | T: units checked by a test | DEC-0255 → 14 |
