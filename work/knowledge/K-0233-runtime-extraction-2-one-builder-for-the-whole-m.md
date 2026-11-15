---
id: K-0233
kind: implementation
title: Runtime extraction 2: one builder for the whole MIA, and a headless runtime
status: confirmed
by: claude
created: 2026-11-15T12:49:57+00:00
concerns: core/runtime.py, core/assistant_tools.py, core/application.py, core/sun_moon.py, server/app.py, deploy/mia-runtime.service, deploy/install_runtime.sh
from: dec:DEC-0155, dec:DEC-0168
---
What: (1) core/assistant_tools.py: _register_assistant_actions and all 111 inline handlers (_action_*, _resolve_*), moved unchanged from MIAApplication (application.py went from 6,028 to about 900 lines) as the mixin AssistantTools. (2) core/runtime.build_services(context): the service construction that was inline in MIAApplication.__init__, now one function the desktop calls too. (3) core/runtime.Runtime(BackgroundJobs, AssistantTools): takes the instance lock, applies a pending restore, builds services, registers tools, schedules jobs; start() runs Scheduler.run_forever on a thread and starts PhoneServer when enabled; health(); run_until_stopped() waits for SIGTERM/SIGINT. `python -m core.runtime` was run here: 95 services, 401 tools, 10 jobs, clean stop. (4) /api/runtime/health (the name /api/health was already the personal Health page). (5) deploy/mia-runtime.service and install_runtime.sh.

How it stayed safe: mixin inheritance again, so tests calling MIAApplication._action_x still pass; imports for each moved block found by ast from application.py's own imports; a test asserts the runtime's tool names equal tests.assistant_registry.build_desktop_registry()'s exactly, and that importing core.runtime in a fresh interpreter loads no PySide6 or gui.

What went wrong: (a) the set_theme tool used gui.theme_manager; a lazy import from core tripped tests/test_dev_map's layering rule (core never imports gui). Now AssistantTools.DESKTOP_THEMES is filled by core/application.py at import and is empty headless. (b) get_sun_moon_info imported modules.navigation.module (Qt): its two formatters moved to core/sun_moon.py and are re-exported by the module. (c) tests patching core.application.scan_ports now patch core.assistant_tools. (d) tests/test_history_and_links read application.py's source for "self.context.x ="; it reads runtime.py now. (e) the Qt-only bits of __init__ that were interleaved with construction (_apply_look and its subscriptions, _online_watch, self.module_manager) now run right after build_services.

Findings for the next steps: every store hard-codes _DATA_DIR = <repo>/data (no data-root setting), which a read-only OS image and a per-user service both need changed; tests/test_runtime.py's `elsewhere` fixture re-points every Path under data/ in loaded core modules, which shows how many there are. The calculators (Ohm's law, unit converter) are registered from modules/toolbox with Qt widgets, so the runtime doesn't register them; their math is already in core. The systemd unit hasn't been run on a real machine.
