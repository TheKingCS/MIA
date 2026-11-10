"""
MIA Homestead — Read-only export server for MIA (DEC-0150)
v0.2

The node's half of "take over the greenhouse": it serves exactly two exports over HTTP, read-only, on the address
you give it (the node's home-network or Tailscale address): viewer/home_snapshot.json (the glance-level summary) and
viewer/dashboard_state.json (every sensor's latest reading and every open alert). main.py already rewrites
dashboard_state.json every control cycle, so by default this only serves; `--every N` also refreshes both every N
minutes, for when main.py isn't running (never both at once: they'd write the same files). MIA's PC fetches them (MIA's core/greenhouse_link.py); nothing here accepts a
command, a write or any other path. Control stays on this node and its safety MCU (docs/SAFETY_SPEC.md).

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


def make_handler(out_dir: Path):
    """A request handler that serves the two exports from out_dir and the live link's pages, and refuses everything
    else."""
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
