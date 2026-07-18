"""
core
====

The MIA kernel.

This package contains everything the rest of the system depends on, and
depends on nothing else in the project (no GUI imports, no module imports).
That rule is intentional and should be preserved as the project grows:

    core/    <- knows about nothing
    modules/ <- knows about core only
    gui/     <- knows about core only (talks to modules via ModuleBase)

If you ever find yourself wanting to `import gui` or `import modules`
from inside `core/`, that's a sign the functionality belongs somewhere else.
"""
