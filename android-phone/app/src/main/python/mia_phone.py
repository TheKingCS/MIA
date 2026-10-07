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


def start(root: str, port: int, native_dir: str = "", last_exit: str = "") -> str:
    """Builds MIA's engine and starts her server. Returns JSON: the session
    token for the screen and how long each step took (milliseconds).
    `native_dir` is where Android put the app's native programs, among
    them llama.cpp's server (libllama_server.so) for MIA's own model.
    `last_exit`: why Android last closed MIA (JSON), shown on the Model test."""
    if _started:
        return json.dumps(_started)
    t0 = time.time()
    sys.path.insert(0, root)
    os.chdir(root)
    from core.config_manager import ConfigManager
    from core.core_runtime import build_core_context
    from core.event_bus import EventBus

    context = build_core_context(ConfigManager(), EventBus())
    from core.local_model import LocalModels

    binary = os.path.join(native_dir, "libllama_server.so") if native_dir else None
    context.local_models = LocalModels(context, binary)
    try:
        context.local_models.last_exit = json.loads(last_exit) if last_exit else {}
    except ValueError:
        pass
    context.local_models.resume()  # Talk's model, if one was running
    t1 = time.time()
    # Who's signed in on this phone (they stay signed in until they log out).
    # Nobody yet: the screen asks them to make their account (/api/setup).
    remembered = context.config.get("phone.signed_in_profile_id")
    me = context.profiles.get_profile(remembered) if remembered else None
    if me is not None:
        context.profiles.set_active_profile(me.profile_id)
        context.personal_data.activate_current()

    import uvicorn

    from server.app import create_app

    app = create_app(context)
    app.state.allow_setup = True  # the phone makes its own first account
    app.state.remember_sign_in = True
    token = ""
    if me is not None:
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
                    python=sys.version.split()[0], profile=me.name if me is not None else "")
    return json.dumps(_started)
