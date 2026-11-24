"""
MIA Homestead — Read-only export server for MIA (DEC-0150)
v0.2

The node's half of "take over the greenhouse": it serves exactly two exports over HTTP, read-only, on the address
you give it (the node's home-network or Tailscale address): viewer/home_snapshot.json (the glance-level summary) and
viewer/dashboard_state.json (every sensor's latest reading and every open alert). main.py already rewrites
dashboard_state.json every control cycle, so by default this only serves; `--every N` also refreshes both every N
minutes, for when main.py isn't running (never both at once: they'd write the same files). MIA's PC fetches them (MIA's core/greenhouse_link.py). Control stays on this node and its safety MCU
(docs/SAFETY_SPEC.md).

The one write (v0.3, 2026-11-24, DEC-0185, docs/MIA_COMMAND_INTERFACE.md step 2): `POST /mia/command`, one
direction from MIA (a target change), signed with the key provisioned for this node (core/command_auth.py: a fresh
timestamp, a one-time nonce, HMAC-SHA256). An unsigned, wrongly signed, stale or replayed request is refused (401)
before anything reads it; one that passes goes to core/mia_commands.py, which checks it against
config/command_limits.yaml and stages or applies it. Only with `--db` (the node's database); no key file means every
direction is refused. Every other method and path is still refused.

Zac chose the transport (2026-11-08, DEC-0150 answer 3): the snapshot by hand still works (drop the file in MIA's
homestead_snapshots/ folder), MIA fetching it over the network, and (v0.2, 2026-11-09) the live link: the node's own
read-only viewer pages served the same way (`PAGES`: the dashboard, the digital twin, their shared nav, and the twin's
layout file), so "show me the greenhouse live" opens the node's dashboard on its own data from any device on the
network. Each is an exact file named in code; no request path is ever joined to a folder, and config/ is never
served except layout.json (the greenhouse's shape, nothing secret).

Usage:
    python viewer/serve_exports.py --bind 100.x.y.z --port 8770              (main.py running: serve its exports)
    python viewer/serve_exports.py --db mia_homestead.db --bind 100.x.y.z --every 5   (no main.py: refresh too)
"""

import argparse
import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVED = ("home_snapshot.json", "dashboard_state.json")
# The live link's read-only pages: request path -> (the file, under this node, and its type). Exact files only.
PAGES = {
    "dashboard.html": (HERE / "dashboard.html", "text/html; charset=utf-8"),
    "digital_twin.html": (HERE / "digital_twin.html", "text/html; charset=utf-8"),
    "nav.js": (HERE / "nav.js", "application/javascript; charset=utf-8"),
    "config/layout.json": (HERE.parent / "config" / "layout.json", "application/json"),
}


def allowed(path: str):
    """The one export file a request path names, or None: only the two exports, nothing else, ever."""
    name = (path or "").split("?", 1)[0].lstrip("/")
    return name if name in SERVED else None


def page(path: str):
    """The live link's page a request path names, as (file, content type), or None. "/" is the dashboard."""
    name = (path or "").split("?", 1)[0].lstrip("/") or "dashboard.html"
    return PAGES.get(name)


def refresh(db_path: str, out_dir: Path) -> None:
    """Writes both exports from the node's database."""
    from export_dashboard_state import export_dashboard_state
    from export_home_snapshot import export_home_snapshot

    export_home_snapshot(db_path, str(out_dir / "home_snapshot.json"))
    export_dashboard_state(db_path, str(out_dir / "dashboard_state.json"))


COMMAND_PATH = "/mia/command"


def take_command(db_path: str, key_path: Path, headers, body: bytes) -> tuple[int, dict]:
    """One signed direction from MIA: (HTTP status, what to answer). Checked for its signature first
    (core/command_auth.verify), then by the node's own check (core/mia_commands.MiaCommands.submit)."""
    from core import command_auth
    from core.experiment_manager import ExperimentManager
    from core.mia_commands import MiaCommands

    db = sqlite3.connect(db_path)
    try:
        ok, why = command_auth.verify(db, command_auth.load_key(key_path), headers, body)
        if not ok:
            return 401, {"state": "refused", "reason": why}
        try:
            command = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return 400, {"state": "refused", "reason": "not JSON"}
        if not isinstance(command, dict):
            return 400, {"state": "refused", "reason": "not one direction"}
        return 200, MiaCommands(db, ExperimentManager(db)).submit(command)
    finally:
        db.close()


def make_handler(out_dir: Path, db_path: str | None = None, key_path: Path | None = None):
    """A request handler that serves the two exports from out_dir and the live link's pages, takes MIA's signed
    directions at COMMAND_PATH when given the node's database, and refuses everything else."""
    class Exports(BaseHTTPRequestHandler):
        """GET the two exports or a live-link page; any other method or path is refused."""

        def do_GET(self):  # noqa: N802 (http.server's name)
            """Serves an export or a live-link page, or 404."""
            name = allowed(self.path)
            target, kind = (out_dir / name, "application/json") if name else (page(self.path) or (None, ""))
            if target is None or not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            """MIA's signed direction at COMMAND_PATH (with --db); anything else refused."""
            from core import command_auth

            if db_path is None or self.path.split("?", 1)[0] != COMMAND_PATH:
                self.send_error(405)
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 < length <= command_auth.MAX_BODY:
                self.send_error(413 if length > command_auth.MAX_BODY else 400)
                return
            status, answer = take_command(db_path, key_path or command_auth.KEY_PATH, self.headers,
                                          self.rfile.read(length))
            body = json.dumps(answer).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_PUT(self):  # noqa: N802
            """Refused: the one write is a POST."""
            self.send_error(405)

        do_DELETE = do_PATCH = do_PUT

        def log_message(self, *_args):
            """Quiet: the node's own logs are enough."""

    return Exports


def main() -> None:
    """Refreshes the exports on a timer and serves them until stopped."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--bind", default="127.0.0.1", help="the node's home-network or Tailscale address")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--every", type=float, default=0.0,
                        help="minutes between refreshes (0: main.py is running and keeps them fresh)")
    args = parser.parse_args()
    out_dir = HERE

    def loop():
        while True:
            try:
                refresh(args.db, out_dir)
            except Exception as problem:  # the server keeps serving the last good export
                print(f"Export refresh failed: {problem}")
            time.sleep(max(1.0, args.every) * 60)

    if args.every > 0:
        threading.Thread(target=loop, daemon=True).start()
    server = ThreadingHTTPServer((args.bind, args.port), make_handler(out_dir, db_path=args.db))
    print(f"Serving MIA's exports on http://{args.bind}:{args.port}/ (read-only, and MIA's signed directions "
          f"at {COMMAND_PATH})")
    server.serve_forever()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent))  # the node's core/, for MIA's directions
    main()
