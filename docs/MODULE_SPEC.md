# MIA Module Compatibility Specification (v1)

This is the authoritative, checklist-style reference for what a module
must satisfy to be successfully added to MIA — whether you're
writing one by hand or installing one through the **Modules** screen's
"Add Module" feature, which enforces every rule below automatically
before anything is copied into `modules/`.

For a friendlier, walkthrough-style guide, see `docs/ADDING_MODULES.md`.
This document is the precise reference; that one is the tutorial.

## Required folder structure

```
your_module_name/
    __init__.py      (required — may be empty)
    module.py         (required)
```

## Required contents of `module.py`

- Must contain **exactly one** class that subclasses `modules.module_base.ModuleBase`.
  - Zero matching classes → rejected ("no class subclassing ModuleBase was found").
  - More than one matching class → rejected. Split into separate modules instead.

## Required class attributes

| Attribute | Type | Rules |
|---|---|---|
| `module_id` | `str` | Required, non-empty. Must match `^[a-z][a-z0-9_]*$` (lowercase, starts with a letter, only letters/numbers/underscores). Must be unique — rejected if another installed module already uses it. Cannot be `"base"` (reserved — this usually means you forgot to override it). |
| `display_name` | `str` | Required, non-empty. Shown on the module's button and in the Modules list. |

## Recommended (not required) class attributes

| Attribute | Type | Default if omitted |
|---|---|---|
| `description` | `str` | Empty string — shows as a blank tooltip. A warning is raised, not an error. |
| `icon` | `str` | A generic package emoji. A warning is raised, not an error. |
| `version` | `str` | `"0.1.0"` |

## Required method

```python
def get_widget(self) -> Any:
    ...
```

- Must be implemented (enforced by `ModuleBase` being an abstract base class — Python itself refuses to instantiate a subclass that doesn't implement this).
- Called **lazily**, the first time a user opens the module — not at discovery/install time. Don't rely on it being called eagerly.
- Should return a GUI widget usable by the rest of the app. The current GUI layer is PySide6, so in practice this means a `QWidget` (or subclass), but `ModuleBase` itself doesn't import or require PySide6 — the contract is duck-typed on purpose so the GUI toolkit could change later without changing this spec.

## Optional methods

```python
def on_load(self) -> None: ...
def on_unload(self) -> None: ...
```

Called once when the module is first activated / torn down, respectively. Optional — the base class provides harmless defaults.

## Performance contract — read this before writing `__init__`

**`__init__` runs for every discovered module at every app boot — even
disabled ones and ones the user never opens.** `ModuleManager.discover()`
instantiates every module it finds so it can list them, well before any
user clicks anything. This means:

- `__init__` must be cheap: assigning attributes, nothing else.
- Expensive setup (loading files, connecting to hardware, network
  calls) belongs in `on_load()` (called only when the module is
  actually activated) or lazily inside `get_widget()` itself.
- A slow `__init__` in one module slows down *every* boot of the
  entire device, not just that module.

## Security note — read this before installing anything

Installing a module means its code will be imported and executed with
the full privileges of the rest of the app — the same as running any
other local Python script. The "Add Module" installer validates
*structure* (does it implement the contract correctly), not *intent*
(is this code safe/benign). There is no sandboxing. Only install
modules whose code you've written yourself or reviewed and trust —
exactly the same judgment you'd apply to running any other script on
your machine.

## What the automated validator checks, in order

When you use "Add Module" (folder or `.zip`), this exact sequence runs
before anything is copied into `modules/` (see `core/module_validator.py`):

1. Is the source a real folder?
2. Does `__init__.py` exist?
3. Does `module.py` exist?
4. Does `module.py` import without raising an exception?
5. Does it define exactly one `ModuleBase` subclass?
6. Is `module_id` a non-empty string matching the required format?
7. Is `module_id` not `"base"` and not already used by another installed module?
8. Is `display_name` a non-empty string?
9. Can the class actually be instantiated (catches a broken `__init__` or a missing `get_widget` implementation)?
10. Is `get_widget` present and callable on the resulting instance?

Any failure at steps 2–9 stops installation with a specific, readable
error message — nothing is copied into `modules/` unless every check
passes. Missing `description`/`icon` (recommended but not required)
produce warnings shown after a successful install, not a rejection.

## Uninstalling

Delete the module's folder from `modules/`. There's no special
uninstall procedure — the module system has no separate registry to
clean up. Note: `rescan()` (used by "Add Module" and the "Rescan
Modules" button) only detects *additions*; removing a folder requires
a full app restart to disappear from the menu, same limitation
documented in `core/module_manager.py`.
