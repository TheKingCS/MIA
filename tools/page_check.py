"""
tools.page_check
==================

Every page of the web front end opened once, to catch the page that fails
to load before a person does (roadmap 2.8, 2026-11-10). Serves `web/` on
a local port, opens each `*.html` in demo mode (`?demo`, the placeholder
example, no MIA needed) in headless Edge through Playwright, waits for it
to settle, and lists any page whose scripts threw or that logged an error
to the console. Exit 1 when one did.

    python -m tools.page_check            # every page
    python -m tools.page_check notes.html # just these

A tool, not a test: the suite never starts a browser (no test starts a
real process). CI runs it on Windows, where Edge is installed.
"""

from __future__ import annotations

import functools
import http.server
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SCHEMA = ROOT / "docs" / "schema"
SETTLE_MS = 1500
# Console lines that aren't a page's fault in demo mode: no server behind it, no favicon, no sign-in.
IGNORED = ("favicon", "Failed to load resource", "net::ERR_", "401", "404")


class _Pages(http.server.SimpleHTTPRequestHandler):
    """web/ as the server serves it: /schema/ from docs/schema (the demo's examples), and no line per request."""

    def translate_path(self, path: str) -> str:
        """/schema/... from docs/schema, as server/app.py mounts it; everything else from web/."""
        if path.split("?", 1)[0].startswith("/schema/"):
            return str(SCHEMA / path.split("?", 1)[0][len("/schema/"):])
        return super().translate_path(path)

    def log_message(self, *args) -> None:
        """Quiet."""


def pages(names: list[str]) -> list[str]:
    """The pages to open: those named, else every .html in web/ (not vendor/)."""
    return names or sorted(p.name for p in WEB.glob("*.html"))


def check(names: list[str]) -> dict[str, list[str]]:
    """Each page's problems (not answering 200, thrown errors, console errors), by page; a page with none isn't
    listed."""
    from playwright.sync_api import sync_playwright

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Pages, directory=str(WEB)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    found: dict[str, list[str]] = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            for name in pages(names):
                problems: list[str] = []
                page = browser.new_page()
                page.on("pageerror", lambda error, p=problems: p.append(f"threw: {error}"))
                page.on("console", lambda msg, p=problems: p.append(f"console: {msg.text}")
                        if msg.type == "error" and not any(i in msg.text for i in IGNORED) else None)
                try:
                    answer = page.goto(f"http://127.0.0.1:{server.server_port}/{name}?demo", wait_until="load",
                                       timeout=15000)
                    if answer is None or answer.status != 200:
                        problems.append(f"answered {answer.status if answer is not None else 'nothing'}")
                    page.wait_for_timeout(SETTLE_MS)
                except Exception as problem:
                    problems.append(f"didn't load: {problem}")
                page.close()
                if problems:
                    found[name] = problems
            browser.close()
    finally:
        server.shutdown()
    return found


def main(argv: list[str]) -> int:
    """Prints each page with a problem (and, on GitHub, an annotation for it); 1 when any had one."""
    import os

    names = pages(argv)
    found = check(argv)
    for name, problems in found.items():
        print(f"{name}:")
        for problem in problems[:5]:
            print(f"  {problem[:300]}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title=Page check: {name}::" + " | ".join(problems[:3])[:600].replace("\n", " "))
    print(f"{len(names) - len(found)} of {len(names)} pages opened without an error.")
    return 1 if found else 0


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    sys.exit(main(sys.argv[1:]))
