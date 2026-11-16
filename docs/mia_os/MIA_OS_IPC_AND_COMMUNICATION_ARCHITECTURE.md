# MIA OS: IPC and communication architecture (Prompt 05, deliverable 6)

*Claude (Fable), 2026-11-16. Planning only. How the parts talk: which mechanism for which kind of conversation, and
the rules every interface follows. Answers T-02 (is the API enough?), T-06 (events across processes) and T-09 (a way
in for conventional apps). Device-to-device protocols are Prompt 12's. Decision: DEC-0192 (proposed).*

## 1. Not one mechanism: one per kind of conversation

| Conversation | Mechanism | Why this one | State |
|---|---|---|---|
| A surface ↔ the runtime (the shell, the phone, the glasses, a browser tab) | **HTTP and server-sent events** (`/api/*`, `/api/live`) | 265 routes exist and every surface uses them; a browser engine speaks it natively; it works identically across the room and on the same machine | Exists |
| A local tool or agent ↔ the runtime (the capture agent, the command line, a browser extension's native host) | **the same HTTP API over a Unix socket** in `$XDG_RUNTIME_DIR/mia/api.sock` | no port, no token to leak: the kernel tells the runtime which user is calling, and the socket's permissions keep other users out | New, small (the server already runs on uvicorn, which serves a socket) |
| The runtime ↔ OS services (logind, NetworkManager, UPower, UDisks2, BlueZ, notifications, portals) | **D-Bus**, system and session buses | it is what those services speak | New (the adapters' Linux halves) |
| The runtime → the system helper | **D-Bus on the system bus, authorised by polkit** | polkit identifies the caller and draws the confirmation; the bus starts the helper on demand | New |
| The runtime ↔ the model server | **HTTP on loopback** | Ollama's and llama.cpp's own interface; already behind `core/llm_manager.py` | Exists |
| The runtime ↔ an extension | **the capability contract over the extension's own socket pair**, JSON messages (DEC-0176) | the sandbox has no network; the socket is its only door | Planned (T-07, T-08) |
| A conventional app → MIA | **a session D-Bus name MIA owns, `org.mia.Capture1`, with one method: offer a capture** | the standard way for desktop apps to talk; a Flatpak app reaches it only if its permissions name it | New, later (T-09) |
| Inside the runtime (store changed, mission completed) | **the in-process event bus** (`core/event_bus.py`), synchronous | exists; nothing crosses a process | Exists |
| The runtime → heavy job children | arguments in, a result file and an exit status out; progress on a pipe | a job is a function with files; it needs no protocol | Partly exists (worker threads today) |
| Device ↔ device (phone, Pi, greenhouse) | HTTPS to the runtime's API over the home network or the tailnet; the sealed relay for the glasses | exists; Prompt 12 | Exists |
| High-volume sensor data | **not the API and not events.** Readings are appended to the owning store's own file by its driver or node and summarised on request | an event stream carrying every reading would make every surface re-read on every sample | Exists (the greenhouse link, sensors) |
| Long-running task coordination | **the run record** (prompt 23's review, G4): state in a store, read by whoever asks | a task that outlives a process can't live in a connection | Proposed |

**Rejected:** gRPC (a second API stack with no client that needs it), a message broker (one machine, one writer),
shared memory (nothing is that hot), and one universal mechanism (the table shows why).

## 2. Is the API enough? (T-02)

**Yes for everything that reads or changes his records. No for talking to the operating system.** The rule:
*anything about his life goes through the runtime's API; anything about the machine goes through the machine's own
D-Bus services.* MIA does not wrap OS services in her own API for other programs, and does not put her records on
D-Bus. The one D-Bus name MIA offers to others (`org.mia.Capture1`) is a mail slot: it can only hand her something
to look at.

## 3. Events across processes (T-06)

Today `/api/live` tells a surface "something changed, read again" with a version number that every write bumps
(`core/live.py`). That design is kept and stated as a rule:

- **An event between processes never carries the truth; it says where the truth changed.** The receiver reads the
  state. So events may arrive twice, late or not at all without harm: a surface that missed one catches up at its
  next read, and re-reading is always safe.
- Delivery is therefore *at least once, best effort*; nothing needs exactly-once.
- The live stream carries a small number of named signals beside the version (today: `state`, `presence`). A new
  one is added only for something a surface must show within a second.
- Where a guarantee *is* needed (a step of a run completed, an approval given), it is a **record** in a store, with
  an id, written atomically; whoever needs it reads the record. The run record is the first of these.

No typed cross-process event system with delivery guarantees is built. If Prompt 08 (agents) or Prompt 12 (devices)
shows a real need, it is an outbox in a store read by id, not a broker.

## 4. Rules for every interface

| Concern | Rule |
|---|---|
| Discovery | Fixed, well-known places: the socket path, the D-Bus names `org.mia.System1` (helper) and `org.mia.Capture1`, the API on loopback at the configured port. No discovery protocol on one machine. Devices finding each other on the network is Prompt 12's |
| Authentication | **Nothing is trusted for being local.** Loopback TCP is reachable by every program of every user on the machine, sandboxed apps included, so every HTTP request carries a session token (the shell's is handed to it through a file only he can read in `$XDG_RUNTIME_DIR/mia`). The Unix socket authenticates by the caller's user id. D-Bus callers are identified by the bus. Devices use their pairing keys (REQ-SEC-004) |
| Authorisation | His records: the action contract and grants, inside the runtime. The system: polkit, inside the helper. A front door never decides; it forwards |
| Listening | Loopback by default (as today: `server.host` is `127.0.0.1`). The home network only when he turns phone access on; the firewall opens that port on trusted networks only. Remote reach through `tailscale serve`, which forwards to loopback |
| Versioning | The API grows by adding; a route's meaning never changes in place. Published shapes live in `docs/schema/` with a test each. `/api/shell` states the contract version a surface can check. D-Bus interface names end in their major version; a breaking change is a new name beside the old |
| Message shapes | JSON with a published schema for anything another process relies on; the helper's methods take typed arguments with fixed choices, never a free string that reaches a command |
| Timeouts | Every call across a process has one. A surface's read: seconds. A model call: its own budget, cancellable. A helper call: the operation's known length, with progress |
| Retries | Only for reads and for operations that say they are safe to repeat. A change is never retried blindly: the caller reads the state and decides |
| Errors | An error says what was attempted, what happened and what is left changed (REQ-TRU-005). A front door shows the runtime's sentence; it never invents one |
| Observability | Each side logs the call with a shared request id; the helper logs every call it receives, allowed or refused |
| Rate limits and resource control | The API limits failed sign-in attempts (`core/sign_in_guard.py`, existing). The capture mail slot accepts one capture at a time per caller and a size ceiling. The helper serialises operations |

## 5. Staying understandable as it grows

- **One door per trust level:** his records (the API), the machine (the helper), captures (the mail slot). A new
  feature picks one; it doesn't get a fourth.
- **New capabilities are tools and action kinds in a manifest**, not new endpoints with their own rules: the
  registry is the catalogue of everything that can be asked of MIA (REQ-ARC-006).
- **Every interface another process depends on has a schema in the repository and a test that fails when the code
  drifts from it.**
