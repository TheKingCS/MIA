# MIA OS: distributed technology evaluation and decision records (Prompt 12 §26)

*Claude (Opus), 2026-11-18. Planning only. DEC-0241 to 0247 are PROPOSED.*

## 1. Technologies

| Need | Options | Recommendation | Why |
|---|---|---|---|
| Remote access | Tailscale (exists), WireGuard by hand, ZeroTier, port forwarding | **Tailscale** | already used; no open ports; Headscale is the self-hosted fallback if he wants no outside coordinator |
| Device-to-device protocol | HTTP + SSE (exists), gRPC, MQTT, WebSockets | **HTTP + SSE** | what every screen already uses; debuggable; MQTT only inside the homestead node if a controller needs it |
| Sync | file-level three-way merge (exists), CRDTs (Automerge, Yjs), CouchDB/PouchDB, Syncthing | **keep the merge** | works, tested, handles his record shapes; CRDTs would mean rewriting every store; Syncthing has no record-level merge |
| Discovery | entered address, Tailscale's list (exists), mDNS/Zeroconf | **Tailscale's list, mDNS offered later** | no surprise pairing |
| Device identity | per-device key with hashed storage (exists), mTLS certificates | **keep keys; add TLS on the home network** | simple, revocable; certificates when Prompt 13 needs them |
| Phone engine | Chaquopy (exists), a rewrite in Kotlin | **Chaquopy** | one codebase (REQ-DST-003) |
| Pi runtime | the Core edition under cage | **as planned** (DEC-0191) | |
| Controllers | the homestead node's own (exists), Home Assistant, ESPHome | **the node's own**; ESPHome for new ESP32 sensors posting to `core/sensors.py` | the safety design already built; HA is a parallel brain |

## 2. Decision records

### DEC-0241: one MIA per person, the PC the hub
Requirements: REQ-DST-001 to 004, 016, 032. Selected: hub, full engines, endpoints, nodes, controllers, sensors as
above. Rejected: a cluster where devices vote on the truth (consensus): far more than one person's devices need.
Reversibility: high. Reconsider if the PC is often away (a laptop as the hub).

### DEC-0242: trust by pairing
Requirements: REQ-DST-005 to 008, 029. One key per device, hashed on the hub, scoped to its kind, listed, revocable.

### DEC-0243: sync stays the three-way merge
Requirements: REQ-DST-011, 018, 023, 024. Driven by the device that travels; one base per device; conflicts kept and
told.

### DEC-0244: HTTP and server-sent events, home network or Tailscale
Requirements: REQ-DST-012 to 015, 026, 028. No open ports, no broker, signals to re-read.

### DEC-0245: thinking on the most capable reachable machine
Requirements: REQ-DST-009, 010, 025. The device's own model the floor; cloud only on his yes.

### DEC-0246: controllers keep their loops and safety
Requirements: REQ-DST-020 to 022. MIA reads, explains and proposes; changes are actions to the node's interface.

### DEC-0247: a lost device is unlinked from anywhere
Requirements: REQ-DST-030, 031. Its data sealed; erased when it next connects (Q-90); a new one paired and filled.
