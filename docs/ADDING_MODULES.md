# Adding a New Module to M.I.A.

Modules are discovered automatically — there is no registry file to
edit. Follow these steps and your module will appear on the main menu
the next time M.I.A. starts.

## 1. Create the folder

```
modules/your_module_name/
    __init__.py      (can be empty)
    module.py
```

The folder name should be a valid Python identifier (snake_case). It
does not have to match `module_id`, but it's good practice to keep them
similar.

## 2. Write `module.py`

Exactly one class in this file must subclass `ModuleBase`:

```python
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from modules.module_base import ModuleBase


class YourModule(ModuleBase):
    module_id = "your_module_name"      # unique, stable, snake_case
    display_name = "Your Module"        # shown on its button
    description = "One-line description shown as a tooltip."
    icon = "\u2728"                     # placeholder emoji/glyph
    version = "0.1.0"

    def get_widget(self) -> QWidget:
        # Build and return whatever widget represents your module's screen.
        return QLabel("Hello from Your Module!")
```

That's it. `core/module_manager.py` will find it, instantiate it with
the shared `AppContext`, and it will show up on the main menu grid,
sorted alphabetically by `display_name`.

## 3. Test it in isolation (without booting the whole app)

Use the module test harness so you don't have to click through the
splash screen and setup wizard every time you tweak your module:

```bash
python tests/run_module.py your_module_name
```

This boots a minimal Qt application, constructs a real `AppContext`
(backed by your actual `config/config.json`), instantiates only your
module, and shows its widget in a plain window. It's the fastest
feedback loop for module development.

## 4. Conventions to follow

- **Don't import other modules directly.** If your module needs to
  react to something happening in another module, use the event bus:
  `self.context.events.subscribe("some.event", self._handler)`. See
  `core/event_bus.py` for details.
- **Keep GUI-building code out of your logic.** If your module grows
  beyond a trivial widget, consider splitting internal logic (data
  access, computation) into a separate file inside your module's
  folder, and keep `module.py` focused on wiring `ModuleBase` to that
  logic plus building the widget.
- **Use `self.context.config`** for any settings your module needs,
  under a namespaced key, e.g. `self.context.config.get("modules.notes.font_size")`.
  Don't invent a separate config file for your module.
- **Log through `core.logger.get_logger(__name__)`**, not `print()`.
- **`get_widget()` is called lazily** — the first time the user opens
  your module, not at startup. Don't do expensive work in `__init__`;
  do it in `on_load()` or inside `get_widget()` itself if it only
  needs to happen once the user actually opens the module.

## 5. Making your module searchable (optional)

Once your module has real content worth finding (notes, files,
reference articles, etc.), you can register a search provider so
Ctrl+K / the search button can find it, without any changes to core
code:

```python
def on_load(self) -> None:
    self.context.search.register_provider("your_module_id", self._search)

def _search(self, query: str):
    from core.search_manager import SearchResult
    query_lower = query.lower()
    results = []
    for item in self._my_searchable_items():
        if query_lower in item.title.lower():
            results.append(SearchResult(
                title=item.title,
                description=item.summary,
                source=self.display_name,
                action_type="open_module",       # or a custom action_type
                action_target=self.module_id,     # see note below
            ))
    return results
```

If your module needs a more specific action than "just open the
module" (e.g. "open this specific note"), you'll need a new
`action_type` your module recognizes, and `MainWindow._on_search_result_activated`
will need a branch for it — see `gui/main_window.py` for the existing
`"open_module"` / `"switch_profile"` cases as a model.

## 6. Enabling, disabling, and rescanning

Every module can be turned off from the **Modules** screen without
uninstalling it — useful for a module that isn't relevant to a
particular deployment, or one that's mid-development and not ready to
show up on the main menu yet. Disabled state is stored in
`config.json` under `modules.disabled` and persists across restarts.
The **Modules** screen itself can never be disabled — that's enforced
in `core/module_manager.py`, not just a UI restriction — since
disabling it would leave no way back in without hand-editing config.

**"Rescan Modules"** (also on that screen) detects module folders added
*while the app is already running*, without needing a restart. Scope
note: this does not reload changed code in a module that's already
loaded — only brand-new folders are picked up. If you're actively
iterating on an existing module's code, `tests/run_module.py` (see
above) is still the right tool; restart the full app to pick up code
changes to a module you already had running.

## 7. Removing a module

Delete its folder. Nothing else references it by import, so there's
nothing else to clean up (aside from any config keys you may have
added under its namespace, if you want a full cleanup).
