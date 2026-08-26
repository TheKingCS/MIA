# MIA Homestead — Capability Registration (Mandatory Process)

## The problem this solves

The failure mode: you build ten modules over six months, the assistant's
system prompt was written on day one describing three of them, and now
you're manually rewriting prompt text every time something changes —
and it's always a little behind. Eventually the assistant confidently
tells you it can't do something it actually can, or doesn't mention a
new capability at all because nobody remembered to update its "brief."

## The rule

**Every module and service must implement `describe_capabilities()` AND
`describe_hardware_requirements()`.** Neither is a style guideline —
both are enforced by Python's ABC mechanism. A `MiaHomesteadModule`
subclass (control modules) or a class implementing `Describable`
(services like inventory, maintenance, notifications) literally cannot
be instantiated without both. Forgetting either isn't a silent gap in
the assistant's knowledge or the hardware shopping list — it's a crash
at startup, caught immediately.

`describe_hardware_requirements()` can validly return `[]` — pure
software services (inventory, maintenance, notifications) do exactly
that. What it can't do is not exist. This is the same discipline
applied to the hardware BOM as to capabilities: declared once, at the
same time the module is written, never reconstructed later from memory
or scattered notes.

## What goes in a Capability

```python
Capability(
    module_id="...",             # matches the module's own id
    display_name="...",          # human-readable name
    purpose="...",                # 1-2 sentences: what and why
    data_produced=[...],          # what it reads/generates
    actions_possible=[...],       # what it can actually DO
    limits_and_safety="...",      # constraints, failsafes, what it WON'T do
    example_questions=[...],      # sample things a user might ask
)
```

`limits_and_safety` matters as much as `actions_possible` — the
assistant needs to know what a module refuses to do (inventory never
places real orders, the aquaponics module never auto-dilutes high EC)
just as clearly as what it does do. An assistant that only knows
capabilities and not limits will confidently promise things the system
won't actually do.

## How it flows into the assistant

1. At startup, `main.py` calls `CapabilityRegistry.register_all()` on
   every loaded module and service.
2. Each one's `describe_capabilities()` gets persisted to the
   `system_capabilities` table — overwriting any prior entry for that
   module_id, so it's always current as of the last restart.
3. The assistant's system prompt includes a compact, auto-generated
   summary of every registered module (`render_compact()`) — built
   fresh every session, never hand-written.
4. For anything requiring more depth, the assistant calls
   `get_system_capabilities` to pull full detail — actions, limits,
   example questions — for one module or all of them.

The result: add a new module, write its `describe_capabilities()` as
part of writing the module (not as a follow-up task), restart the
system, and the assistant already knows about it. Nobody teaches it
anything by hand.

## When you're building a new module

Checklist, in order:
1. Implement the module's actual logic (`read_sensors`/`evaluate`, or
   whatever the service does).
2. Implement `describe_capabilities()` and `describe_hardware_requirements()`
   in the same sitting — not after, not "later once it's stable." If you
   can't yet describe what it does in a sentence, the module's purpose
   probably isn't well-defined yet.
3. Register it in `config/modules.yaml` (control modules) or add it to
   the `all_describables` list in `main.py` (standalone services).
4. **Run `python3 core/self_audit.py`.** This is not optional — it's
   the check that catches exactly the failure mode of steps 1-2 done
   correctly and step 3 forgotten: real code with a real
   `describe_capabilities()` that nobody wired into registration,
   silently invisible to the assistant. It also re-runs the full
   safety scenario suite as a final gate.
5. Restart and confirm the module shows up via `get_system_capabilities`,
   and that if you changed anything about an EXISTING module,
   `get_self_change_history` shows a real entry — not silence, and not
   noise on an unrelated restart with no code changes.

If you skip step 2, the module won't run at all — Python enforces this
before you can even get to step 3. If you skip step 3, step 4 catches
it before you ship it.

## How the system's self-understanding tracks its own development

Every time `CapabilityRegistry` or `HardwareRegistry` registers a
module, it diffs the new declaration against what was stored last
time. Three outcomes:

- **First time seeing this module** → logged as `first_registered`.
- **Nothing changed** → nothing logged. A restart with no code changes
  produces zero changelog noise — this was verified directly: two
  identical registrations in a row produced no entries, then an actual
  edit produced exactly two precise, field-level entries.
- **Something changed** → logged with the specific field, old value,
  and new value, timestamped.

This is what "the system's understanding of itself changes as it's
developed" actually means in practice — not a vibe, a table
(`system_changelog`) you can query, and a tool (`get_self_change_history`)
the assistant uses to answer honestly instead of guessing.
