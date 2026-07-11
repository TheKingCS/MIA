"""
core.app_context
=================

Defines AppContext: a small bundle of shared services (config, logger
factory, event bus) that gets handed to every module and every GUI
component.

Why this exists: modules and GUI screens need access to core services,
but we don't want them reaching for globals (e.g. `import core.state as
state; state.config`) because that makes testing hard and hides
dependencies. Instead, everything that needs core services receives one
`AppContext` object at construction time. This is a lightweight form of
dependency injection — enough structure to keep things testable, without
pulling in a DI framework this project doesn't need yet.

Any new core-level service (e.g. a future "hardware" service for
robotics, or a "local_ai" service) should be added as an attribute here
and constructed in core/application.py, not scattered as ad-hoc imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from core.config_manager import ConfigManager
from core.event_bus import EventBus

if TYPE_CHECKING:
    from core.notification_manager import NotificationManager
    from core.profile_manager import ProfileManager
    from core.search_manager import SearchManager


@dataclass
class AppContext:
    """Shared services passed to modules and GUI components."""

    config: ConfigManager
    events: EventBus
    # Assigned by MIAApplication right after construction (each of
    # these takes an AppContext, so none can be created in the same
    # dataclass __init__ call — see core/application.py). Optional here
    # so AppContext remains constructible on its own for tests.
    profiles: Optional["ProfileManager"] = field(default=None, repr=False)
    notifications: Optional["NotificationManager"] = field(default=None, repr=False)
    search: Optional["SearchManager"] = field(default=None, repr=False)
