"""
MIA on the phone (DEC-0019, the Phase 1 spike): start her engine and her
server inside the app, on 127.0.0.1 only, and hand the screen a session.
The engine is the repo's own (core/core_runtime.py), unchanged.
"""

import json
import os
import secrets
import sys
import threading
import time

_started = {}


def start(root: str, port: int) -> str:
    """Builds MIA's engine and starts her server. Returns JSON: the session
    token for the screen and how long each step took (milliseconds)."""
    if _started:
        return json.dumps(_started)
    t0 = time.time()
    sys.path.insert(0, root)
    os.chdir(root)
    from core.config_manager import ConfigManager
    from core.core_runtime import build_core_context
    from core.event_bus import EventBus

    context = build_core_context(ConfigManager(), EventBus())
    t1 = time.time()
    me = context.profiles.get_active_profile()
    if me is None:
        existing = context.profiles.list_profiles()
        # First start. Onboarding (a name, an email) comes in Phase 2.
        me = existing[0] if existing else context.profiles.create_profile("You", make_active=True)
        context.profiles.set_active_profile(me.profile_id)
        context.personal_data.activate_current()

    import uvicorn

    from server.app import create_app

    app = create_app(context)
    token = secrets.token_urlsafe(24)
    app.state.sessions[token] = me.profile_id
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, name="mia-server", daemon=True).start()
    deadline = time.time() + 60
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("MIA's server didn't start.")
    t2 = time.time()
    _started.update(token=token, engine_ms=round((t1 - t0) * 1000), server_ms=round((t2 - t1) * 1000),
                    python=sys.version.split()[0], profile=me.name)
    return json.dumps(_started)
