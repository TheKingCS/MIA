# MIA OS: hardware resource coordination (Prompt 06 §15; DEC-0204)

*Claude (Opus), 2026-11-17. Planning only. Built on Prompt 05's resource management (systemd's control groups,
DEC-0195). Model routing itself is Prompt 07's.*

## 1. Who decides what

| Decision | Linux | MIA |
|---|---|---|
| CPU time, memory limits, I/O priority | **yes**: cgroups per service (the session, the runtime, the model runner, the lab) | sets the services' weights once, in the image |
| Which process gets the GPU | the driver serves whoever asks | **yes**: which model is loaded, and which request waits |
| Power states, frequencies | **yes** (amd-pstate, amdgpu) | none |
| What runs on which device | none | **yes**: from the capability records |
| Killing a runaway | **yes** (systemd-oomd, limits) | notices, reports, restarts its own service |

## 2. MIA's rules for the GPU

1. **One model job per GPU at a time.** Requests queue in the model runner; MIA orders the queue.
2. **Priority:** a conversation he's in, then a specialist answering him, then the Workroom's agents, then
   background work (Night School, the bench, captions). A higher one pre-empts the next one's start, never a
   running answer mid-way.
3. **Keep the everyday model loaded** while there's room; load larger models on demand; unload what hasn't been used
   for ten minutes (the runner's keep-alive).
4. **On another node when it fits better**: a reviewer from another family, a 70B, or anything while this GPU is
   busy for longer than he'd wait (DEC-0202).
5. **Hot or on battery:** background model work waits (REQ-HW-024, 025).

## 3. Measured, not assumed (W1)

How many Workroom agents one 24 GB card can serve, with which small model driving clicks while a larger one plans,
is measured before the Workroom is built (`MIA_OS_SPECIALIST_FORGE.md`, W1).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-029 | A conversation he's in shall never wait behind background model work for more than one model load. | Must | MVP | PC | Exists (FW-12: `core/model_queue.py`, one call at a time, the conversation first; measured at MV-02) | M: a bench running while he asks | DEC-0204 → 06 |
| REQ-HW-030 | The model queue shall be visible ("what's using the card?"), with each job's owner and priority. | Should | R1 | PC | New | T | DEC-0204, → 07 |
