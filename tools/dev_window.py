"""
tools.dev_window
==================

The development board in its own window (Zac, 2026-11-03: "I want this in a
window that makes it all easy to view and understand the workflow and what
is going on, what is building, who is building it"). The same board as
`web/dev.html` inside MIA (core/work_dashboard.py), without MIA running or a
sign-in: it reads this repo's `work/` folder, which whoever runs this can
read anyway.

    .venv\\Scripts\\python -m tools.dev_window            (its own window)
    .venv\\Scripts\\python -m tools.dev_window --browser  (in the browser instead)

It serves the board on 127.0.0.1 only, on a port picked each time, and the
data only to a page holding this run's key. Read-only: nothing here changes
the work; that stays `python -m tools.work`, and approving stays Zac at the
keyboard.
"""

from __future__ import annotations

import argparse
import hmac
import json
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

WEB = Path(__file__).resolve().parent.parent / "web"
FILES = {"/": ("dev-window.html", "text/html"), "/tokens.css": ("tokens.css", "text/css"),
         "/dev.css": ("dev.css", "text/css"), "/dev.js": ("dev.js", "text/javascript")}


def handler(key: str, port_of: callable):
    class Board(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # quiet; nothing to keep
            pass

        def _send(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            # Only this computer, by its own address (no other site's name pointed here).
            if self.headers.get("Host", "") != f"127.0.0.1:{port_of()}":
                return self._send(403, b"No.", "text/plain")
            url = urlsplit(self.path)
            if url.path == "/api/dev":
                if not hmac.compare_digest(self.headers.get("X-Dev-Key", ""), key):
                    return self._send(403, b"{}", "application/json")
                from core.work_dashboard import page

                query = (parse_qs(url.query).get("q") or [""])[0][:200]
                return self._send(200, json.dumps(page(None, query), default=str).encode("utf-8"), "application/json")
            found = FILES.get(url.path)
            if found is None:
                return self._send(404, b"Not here.", "text/plain")
            return self._send(200, (WEB / found[0]).read_bytes(), found[1])

    return Board


def serve() -> tuple[ThreadingHTTPServer, str]:
    """Start the board's server in the background; returns it and the page's address."""
    key = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(key, lambda: server.server_address[1]))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/#key={key}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="tools.dev_window")
    parser.add_argument("--browser", action="store_true", help="open it in the browser instead of its own window")
    args = parser.parse_args(argv)
    server, address = serve()
    if not args.browser:
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QIcon
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtWidgets import QApplication
        except ImportError:
            args.browser = True
        else:
            app = QApplication(sys.argv[:1])
            app.setApplicationName("MIA Development")
            view = QWebEngineView()
            view.setWindowTitle("MIA Development")
            icon = WEB / "img" / "icon-192.png"
            if icon.exists():
                view.setWindowIcon(QIcon(str(icon)))
            view.resize(1440, 920)
            view.load(QUrl(address))
            view.show()
            code = app.exec()
            server.shutdown()
            return code
    import webbrowser

    webbrowser.open(address)
    print("The board is open in your browser. Leave this running; Ctrl+C closes it.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
