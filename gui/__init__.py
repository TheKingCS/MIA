"""
gui
===

Presentation layer only. Everything in this package talks to the rest of
the system through core.app_context.AppContext and modules.module_base.
ModuleBase — never by importing module internals or reaching into core
services directly beyond what AppContext exposes.

Keeping this boundary strict is what allows the animated character panel
(gui/character_panel.py) to be swapped out for a real implementation
later without touching core/ or modules/ at all.
"""
