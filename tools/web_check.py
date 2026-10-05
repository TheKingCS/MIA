"""
tools.web_check
=================

The Pi 5 check for the new web front end (Phase 2, DEC-0013: "run the
slice on the Pi 5 before committing to broad migration"). Opens the web
Home (`web/`, in demo mode with the placeholder example) inside the same
built-in browser MIA uses (QtWebEngine) and measures:

- whether this computer's PySide6 has QtWebEngine at all;
- how long the built-in browser takes to start (once, at boot) and how
  long the page then takes to load;
- how much memory the browser adds (MIA plus its web helper processes);
- how smooth the presence orb animates (frames per second over 5 s).

    python -m tools.web_check            # on the Pi, from the MIA folder

Prints a plain report, and the verdict, for Zac to paste into the hub
(`docs/CURRENT_STATE.md` or a reply on H-0006). Touches no data.
"""

from __future__ import annotations

import functools
import http.server
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SMOOTH_FPS = 45  # at or above: smooth enough for the presence animation
MEMORY_BUDGET_MB = 600  # what the web view may add on an 8 GB Pi 5


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Serves web/ at /web/ and docs/schema/ at /schema/, like MIA does."""

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/schema/"):
            return str(ROOT / "docs" / "schema" / path[len("/schema/"):])
        if path.startswith("/web/"):
            rest = path[len("/web/"):] or "index.html"
            return str(ROOT / "web" / rest)
        return str(ROOT / "web" / "index.html")

    def log_message(self, *_args):
        pass


def _serve() -> tuple[http.server.ThreadingHTTPServer, int]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Handler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def _memory_mb() -> float:
    import psutil

    me = psutil.Process()
    total = me.memory_info().rss
    for child in me.children(recursive=True):
        try:
            total += child.memory_info().rss
        except psutil.Error:
            pass
    return total / (1024 * 1024)


def verdict(load_ms: float, added_mb: float, fps: float, start_ms: float = 0.0) -> str:
    """Pure logic. The one-line answer for the hub."""
    problems = []
    if start_ms > 15000:
        problems.append(f"slow browser start ({start_ms / 1000:.0f} s)")
    if load_ms > 3000:
        problems.append(f"slow to load ({load_ms:.0f} ms)")
    if added_mb > MEMORY_BUDGET_MB:
        problems.append(f"heavy ({added_mb:.0f} MB)")
    if fps < SMOOTH_FPS:
        problems.append(f"choppy ({fps:.0f} fps)")
    return "PASS: the web front end runs well here." if not problems else "CHECK: " + ", ".join(problems) + "."


def main(seconds: float = 5.0) -> int:
    try:
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError as problem:
        print(f"QtWebEngine isn't available in this PySide6 ({problem}).")
        print("Fallback: MIA's Home (preview) offers to open the page in the system browser (Chromium on the Pi).")
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    server, port = _serve()
    before = _memory_mb()
    view = QWebEngineView()
    view.resize(1280, 800)
    view.show()
    started = time.monotonic()
    result: dict = {}

    def measure_fps():
        script = ("new Promise(r => { let n = 0; const t0 = performance.now();"
                  f" (function f(t) {{ n++; if (t - t0 < {seconds * 1000:.0f}) requestAnimationFrame(f);"
                  " else r(n * 1000 / (t - t0)); })(t0); }).then(v => document.title = 'fps:' + v.toFixed(1))")
        view.page().runJavaScript(script)

    page_url = QUrl(f"http://127.0.0.1:{port}/web/?demo")

    def on_loaded(ok: bool):
        if "start_ms" not in result:  # the warm-up: starting the browser itself
            result["start_ms"] = (time.monotonic() - started) * 1000
            result["page_started"] = time.monotonic()
            view.setUrl(page_url)
            return
        result["load_ms"] = (time.monotonic() - result["page_started"]) * 1000
        result["ok"] = ok
        QTimer.singleShot(500, measure_fps)

    def on_title(title: str):
        if title.startswith("fps:"):
            result["fps"] = float(title[4:])
            result["added_mb"] = _memory_mb() - before
            app.quit()

    view.loadFinished.connect(on_loaded)
    view.titleChanged.connect(on_title)
    view.setUrl(QUrl("about:blank"))
    QTimer.singleShot(int((seconds + 30) * 1000), app.quit)  # never hang
    app.exec()
    server.shutdown()
    if "fps" not in result:
        print("The page didn't finish (no frame-rate reading). Loaded:", result.get("ok"))
        return 1
    print(f"Browser start {result['start_ms']:.0f} ms (once, at boot) · page load {result['load_ms']:.0f} ms · "
          f"memory added {result['added_mb']:.0f} MB · animation {result['fps']:.0f} fps")
    print(verdict(result["load_ms"], result["added_mb"], result["fps"], result["start_ms"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
