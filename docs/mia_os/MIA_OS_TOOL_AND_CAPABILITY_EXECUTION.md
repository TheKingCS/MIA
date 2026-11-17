# MIA OS: tools and capability execution (Prompt 08 §9)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Tools and actions (exists)

- **A tool** (the Assistant's, about 430) answers or proposes; each has a tier in its app's manifest.
- **An action kind** (482) changes something, only through the contract.
- **Discovery:** tools are offered to the model by the question's words (domains, trigger phrases), never all at once;
  the Application Registry answers "what can MIA do?" from the manifests (M2).
- **Capabilities** are the unit of permission (DEC-0156); the registry fails a test on an unclaimed or untiered one.

## 2. Execution path for one action

```
propose(kind, params) → describe() checks it can be done and says what would happen (+ "can't be undone")
  → grants.require(kind, initiator) → his yes (if the tier needs it) → execute() (the store's own code)
  → verify (read back, DEC-0218) → record (history, undo, life event) → said, with Undo
```

**MIA OS adds:** system kinds through the fixed-operation helper (DEC-0194: each one confirmed in the OS's own dialog);
device kinds through their owner (the homestead node, never a relay directly, REQ-HW-017); app automation through
portals and accessibility (Prompt 10/13).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-011 | Every tool and action kind shall have a tier in its app's manifest; a test fails on one without. | Must | MVP | All | Exists | T: test_app_registry | DEC-0156 → 08 |
| REQ-AGT-012 | System and device changes shall be action kinds on the same contract, executed by their owners (the helper, the device's node), never by MIA directly. | Must | R1 | PC | New | T | DEC-0213, DEC-0194 → 08 |
