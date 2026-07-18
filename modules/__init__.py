"""
modules
=======

Every feature of MIA (Assistant, Files, Notes, Maps, etc.) lives here
as an independent package. Each module package must:

    - contain a module.py
    - define exactly one class subclassing modules.module_base.ModuleBase

Modules are discovered automatically by core.module_manager.ModuleManager
at startup — there is no manual registry to edit. See
docs/ADDING_MODULES.md for the full guide.
"""
