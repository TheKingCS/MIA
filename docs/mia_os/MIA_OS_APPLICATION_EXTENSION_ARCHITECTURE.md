# MIA OS: extensions, plugins and connectors (Prompt 03 §13)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).
DEC-0176 proposed.*

## 1. Which is which

| Thing | Adds | Lives | Example | When to use |
|---|---|---|---|---|
| Independent application | a person-facing bundle | MIA's own: the runtime | World | a new area of life with its own records |
| Extension | capabilities and surfaces to an existing app | its own sandboxed process (proposed) | a new sensor type for Greenhouse | adding to an app without changing its core |
| Plugin | (not used: an extension in MIA's terms) | — | — | — |
| Shared service | something every app uses | the runtime | the gate, storage | when two apps would otherwise each build it |
| Connector | outside data, read-only, previewed | the runtime | a bank CSV import, a feed | bringing data in |
| AI capability | a model-backed capability (summarise, explain) | the runtime, through model access | the UAL's Explain | when the job needs language |
| Agent | a worker with a role, using capabilities | the runtime or the lab | a specialist | ongoing judgement in one area |
| Taught skill | a learned procedure of capabilities | a store (`core/taught_skills.py`) | a weekly routine | the person shows MIA something |

## 2. The extension lifecycle (proposed)

Discover (Zac's own or the lab's) → install (signed bundle, manifest, sandbox profile shown) → grant (its capabilities'
needs, in plain words) → run (started on first use, stopped when idle) → update (same key, changed permissions shown)
→ remove (its data kept, exported or deleted on approval).

## 3. In-process, out-of-process, or through services

| Option | Security | Cost | Verdict |
|---|---|---|---|
| In the parent app's process (today's "Add Module") | none: full privileges | cheapest | first-party only |
| Its own sandboxed process, talking the capability contract | strong: grants at one boundary | a process each (memory on the Pi) | **recommended** for anything not MIA's own |
| Inside a WebAssembly runtime | strong, small | Python in WASM is immature; tooling cost | prototype later |

## 4. Compatibility

An extension declares the contract version it speaks; the host refuses one that's too new and warns on one past its
deprecation date (MIA_OS_APPLICATION_COMPATIBILITY_MODEL.md).

## 5. Proof of concept (proposed, not run without authorization)

One extension (a "hello sensor" that registers one read capability) in a bubblewrap sandbox with no network, calling
the local API with a token: success = it registers, its capability works through the action contract, a call it
wasn't granted is refused, and it can't read MIA's data folder. Measure memory on the Pi.
