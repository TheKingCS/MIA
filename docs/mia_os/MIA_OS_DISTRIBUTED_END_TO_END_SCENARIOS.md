# MIA OS: end-to-end scenarios (Prompt 12 §25)

*Claude (Opus), 2026-11-18. Each scenario: devices, services, path, data, security, failures, what he sees.*

### A. PC to phone conversation
- **Devices:** PC, phone. **Services:** conversations store, sync, the link.
- **Path:** he talks at the desk; the conversation is saved on the PC; the phone (linked, home Wi-Fi or Tailscale) asks
  for conversations updated recently, then syncs; he continues in Talk on the phone; the turn goes to the PC's model.
- **Security:** the phone's device key; private-mode conversations never leave the PC.
- **Failure:** PC unreachable: the phone shows its last synced copy and answers on its own model, saying so.
- **He sees:** the conversation where he left it; "answered on your PC".

### B. Smart glasses
- **Devices:** glasses, phone, (PC). **Path:** glasses → the phone app (DAT, Bluetooth) → the phone's engine → the
  PC's model if reachable → cards back to the glasses.
- **Permissions:** the phone holds the camera and microphone permissions; the glasses show nothing private.
- **Latency:** speech on the phone; one model turn; cards are small. **Failure:** phone app closed: the glasses show
  "open MIA on your phone"; PC away: the phone's model.

### C. Offline phone
- **Devices:** phone. **Works:** every record, action, reminder, alarm, Talk on the small model, voice, the glasses.
- **Gone:** the big model, web lookups, sync. **Reconnecting:** sync's three-way merge; deferred messages re-offered.

### D. Greenhouse monitoring
- **Devices:** the homestead node (Pi), its sensors and safety MCU, PC, phone.
- **Path:** sensors → the node's loop (thresholds, deterministic) → its export → the PC pulls it on the home network →
  MIA explains and alerts through the gate → the phone and desktop show it.
- **Security:** the node only exports; the PC only fetches from his own network. **Failure:** PC off: the node runs on;
  alerts wait; the node's own dashboard still works.

### E. Distributed AI task
- **Devices:** phone, PC. **Path:** he asks the construction specialist from the phone; the phone sends the turn to
  the PC; the GPU queue runs it on qwen2.5:32b (conversation first); the answer returns; long jobs return when done
  ("I'll tell you when it's ready").
- **Failure:** PC unreachable: the phone says the specialist needs the PC and offers a short answer on its own model.

### F. Device loss
- Unlink the phone from the PC's Sign-ins (or "sign out everywhere"); its key stops working; its MIA data is sealed
  with its own key. When it next connects it's told to erase (Q-90). A new phone: install, sign in, pair, sync.

### G. Primary PC unavailable
- The phone and glasses keep working on the phone's engine; the household display (an endpoint of the PC) shows
  "MIA's computer is off"; the greenhouse runs itself. Gone: big models, specialists, Night School, sync.

### H. Conflicting offline changes
- The PC and the phone both edit a shopping item while apart. On sync: changed fields from both kept; the same field
  on both: the newer wins, the other kept in the history and told to him (REQ-DST-023). Two new items: both kept.

### I. Multi-device mission
- **Devices:** PC, phone, the greenhouse node. A run on the PC ("get the greenhouse ready for frost") plans steps; one
  step is an action to the node (raise the heater setpoint), approved on his phone; the node applies it through its
  own safety checks; the PC reads it back; the run's record (owned by the PC) shows each step, who did it and when.

### J. Network failure
- Internet down: the home network still links the phone, PC and node; weather and lookups say they're offline. Home
  network down: each device alone; the node's loop unaffected; everything syncs and re-offers when it's back.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-033 | Scenarios A, C, F, G and J shall pass as demonstrations on his real devices before MIA OS is called ready. | Should | R1 | All | New | D | DEC-0241 → 12, 16 |
