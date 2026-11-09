"""
MIA Homestead — Read-only export server for MIA (DEC-0150)
v0.1

The node's half of "take over the greenhouse": it serves exactly two exports over HTTP, read-only, on the address
you give it (the node's home-network or Tailscale address): viewer/home_snapshot.json (the glance-level summary) and
viewer/dashboard_state.json (every sensor's latest reading and every open alert). main.py already rewrites
dashboard_state.json every control cycle, so by default this only serves; `--every N` also refreshes both every N
minutes, for when main.py isn't running (never both at once: they'd write the same files). MIA's PC fetches them (MIA's core/greenhouse_link.py); nothing here accepts a
command, a write or any other path. Control stays on this node and its safety MCU (docs/SAFETY_SPEC.md).

Zac chose the transport (2026-11-08, DEC-0150 answer 3): the snapshot by hand still works (drop the file in MIA's
homestead_snapshots/ folder), MIA fetching it over the network now, a live link later.

Usage:
    python viewer/serve_exports.py --bind 100.x.y.z --port 8770              (main.py running: serve its exports)
    python viewer/serve_exports.py --db mia_homestead.db --bind 100.x.y.z --every 5   (no main.py: refresh too)
"""

import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVED = ("home_snapshot.json", "dashboard_state.json")


def allowed(path: str):
    """The one export file a request path names, or None: only the two exports, nothing else, ever."""
    name = (path or "").split("?", 1)[0].lstrip("/")
    return name if name in SERVED else None


def refresh(db_path: str, out_dir: Path) -> None:
    """Writes both exports from the node's database."""
    from export_dashboard_state import export_dashboard_state
    from export_home_snapshot import export_home_snapshot

    export_home_snapshot(db_path, str(out_dir / "home_snapshot.json"))
    export_dashboard_state(db_path, str(out_dir / "dashboard_state.json"))


def make_handler(out_dir: Path):
    """A request handler that serves the two exports from out_dir, and refuses everything else."""
    class Exports(BaseHTTPRequestHandler):
        """GET the two exports; any other method or path is refused."""

        def do_GET(self):  # noqa: N802 (http.server's name)
            """Serves an export, or 404."""
            name = allowed(self.path)
            target = out_dir / name if name else None
            if target is None or not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            """Read-only: refused."""
            self.send_error(405)

        do_PUT = do_DELETE = do_PATCH = do_POST

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
    server = ThreadingHTTPServer((args.bind, args.port), make_handler(out_dir))
    print(f"Serving MIA's exports on http://{args.bind}:{args.port}/ (read-only)")
    server.serve_forever()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(HERE))
    main()
