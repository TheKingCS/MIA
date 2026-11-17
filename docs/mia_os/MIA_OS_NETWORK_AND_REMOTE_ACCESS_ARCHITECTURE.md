# MIA OS: the network and reaching home from away (Prompt 12 §11)

*Claude (Opus), 2026-11-18. Planning only.*

| Situation | Path | Exists |
|---|---|---|
| At home | the home network, the PC's local address | yes |
| Away | Tailscale (WireGuard), the PC's Tailscale address; no port forwarding, no public address | yes |
| No internet at home | the home network still works; Tailscale peers on the same network still reach each other | yes |
| No network at all | each full engine alone | yes |

**Rules:** the server refuses forwarded requests when phone access is off (`server.enabled`); nothing listens on the
public internet; the greenhouse link only fetches from an address on his own network (`greenhouse_link`). **Tailscale
is a tool, not a dependency**: MIA works on the home network without it, and a phone away from home without it uses
its own model.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-014 | MIA shall never listen on the public internet; away from home it shall be reached only through Tailscale. | Must | MVP | All | Exists | T | DEC-0244 (Q-88) → 12, 13 |
| REQ-DST-015 | With no internet, devices on the home network shall still reach each other and sync. | Must | MVP | All | Exists | D | DEC-0244 → 12 |
