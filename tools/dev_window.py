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


ASKING: set[str] = set()  # council members answering right now
_LOCK = threading.Lock()


def _speaking(name: str, now: bool) -> None:
    """Marks a team member as speaking or done (thread-safe), for the board's who-is-talking light."""
    with _LOCK:
        (ASKING.add if now else ASKING.discard)(name)


def _run(message: dict) -> None:
    """Zac's message worked through the council (core/council_floor.py), in the background: a CLI
    can take minutes, and a debate several turns."""
    from core import council, council_floor

    try:
        council_floor.run(message, on_turn=_speaking)
    except Exception as problem:  # the chat says so rather than going quiet
        council.post("mia", f"(The council stopped: {problem})", reply_to=message["id"], kind="note",
                     thread=message.get("thread", ""), turn=message["id"])


RUNNING: set[str] = set()  # missions this window is working


def _run_mission(mission_id: str) -> None:
    """Step a started mission until it stops, pauses or the window closes; a quiet step waits five minutes."""
    import time

    from core import work_runner
    from core.work_agents import load as load_agents

    with _LOCK:
        if mission_id in RUNNING:
            return
        RUNNING.add(mission_id)
    try:
        while True:
            said = work_runner.step(mission_id, load_agents())
            if said.startswith(("stop", "No mission")) or " is paused" in said or " is done" in said:
                return
            time.sleep(300 if said.startswith(("hold", "idle")) or "usage limit" in said else 5)
    except Exception as problem:  # the history says so rather than the runner going quiet
        from core import work_activity

        work_activity.record("runner", "runner", "", f"{mission_id} stopped: {str(problem)[:200]}")
    finally:
        with _LOCK:
            RUNNING.discard(mission_id)


def handler(key: str, port_of: callable):
    """The dev window's request handler class, bound to its access key and port: it answers only this computer by its own address with the key, sends with no-store, nosniff and a strict content policy, and serves the board, the team's messages and voice samples."""
    class Board(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # quiet; nothing to keep
            pass

        def _send(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind if kind.startswith("audio/") else kind + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            # blob: for media only: a voice sample is fetched with the key, then played from memory.
            self.send_header("Content-Security-Policy", "default-src 'self'; media-src 'self' blob:; frame-ancestors 'none'")
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
                found = page(None, query)
                if found.get("available"):
                    with _LOCK:
                        found["asking"] = sorted(ASKING)
                        for m in found.get("missions", []):
                            m["running_here"] = m["id"] in RUNNING
                    found["writable"] = True
                    from core import council_voices

                    found["voices"] = council_voices.voices()
                return self._send(200, json.dumps(found, default=str).encode("utf-8"), "application/json")
            if url.path == "/api/voice":  # a member's voice sample (core/council_voices.py, DEC-0082)
                if not hmac.compare_digest(self.headers.get("X-Dev-Key", ""), key):
                    return self._send(403, b"{}", "application/json")
                from core import council_voices

                asked = parse_qs(url.query)
                try:
                    wav = council_voices.sample((asked.get("member") or [""])[0][:20], (asked.get("voice") or [""])[0][:40])
                except council_voices.VoiceError as problem:
                    return self._send(400, json.dumps({"error": str(problem)}).encode("utf-8"), "application/json")
                except Exception as problem:  # Kokoro missing or failing: say so
                    return self._send(503, json.dumps({"error": f"No voice here: {problem}"[:300]}).encode("utf-8"),
                                      "application/json")
                return self._send(200, wav, "audio/wav")
            found = FILES.get(url.path)
            if found is None:
                return self._send(404, b"Not here.", "text/plain")
            return self._send(200, (WEB / found[0]).read_bytes(), found[1])

        def do_POST(self) -> None:
            """Zac's message to the council. Same rules as reading, and a message never approves anything."""
            if self.headers.get("Host", "") != f"127.0.0.1:{port_of()}" or \
                    not hmac.compare_digest(self.headers.get("X-Dev-Key", ""), key):
                return self._send(403, b"{}", "application/json")
            where = urlsplit(self.path).path
            if where not in ("/api/council", "/api/saga", "/api/mission", "/api/knowledge", "/api/voice", "/api/ledger",
                             "/api/loops", "/api/night"):
                return self._send(404, b"{}", "application/json")
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 100_000)
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                return self._send(400, b"{}", "application/json")
            if where == "/api/saga":
                return self._saga(body)
            if where == "/api/mission":
                return self._mission(body)
            if where == "/api/loops":  # measure the PC's loops now (core/loops.py)
                from core import loops

                loops.run(None, "device", force=True)
                return self._send(200, b"{}", "application/json")
            if where == "/api/night":  # Zac starting a night of school now (core/night_school.py)
                from core import night_school

                night_school.launch()
                return self._send(200, b"{}", "application/json")
            if where == "/api/ledger":  # Zac confirming a stage the evidence supports (DEC-0075); grants nothing
                from core import dev_ledger

                try:
                    dev_ledger.confirm(str(body.get("provider", "")), str(body.get("skill", "")), int(body.get("stage", 0)))
                except (ValueError, TypeError) as problem:
                    return self._send(400, json.dumps({"error": str(problem)}).encode("utf-8"), "application/json")
                return self._send(200, b"{}", "application/json")
            if where == "/api/voice":  # Zac's pick for a member
                from core import council_voices

                try:
                    chosen = council_voices.choose(str(body.get("member", ""))[:20], str(body.get("voice", ""))[:40])
                except council_voices.VoiceError as problem:
                    return self._send(400, json.dumps({"error": str(problem)}).encode("utf-8"), "application/json")
                return self._send(200, json.dumps(chosen).encode("utf-8"), "application/json")
            if where == "/api/knowledge":  # Zac confirming or withdrawing one of MIA's notes (DEC-0083)
                from core import dev_knowledge

                try:
                    if body.get("act") == "confirm":
                        dev_knowledge.confirm(str(body.get("id", "")), "zac")
                    elif body.get("act") == "withdraw":
                        dev_knowledge.withdraw(str(body.get("id", "")), "zac", str(body.get("why") or "not right")[:300])
                    else:
                        raise dev_knowledge.KnowledgeError("Confirm or withdraw.")
                except dev_knowledge.KnowledgeError as problem:
                    return self._send(400, json.dumps({"error": str(problem)}).encode("utf-8"), "application/json")
                return self._send(200, b"{}", "application/json")
            from core import saga

            said = saga.REMEMBER.match(str(body.get("text", "")))
            if said and (said.group(1) or said.group(2) or "").strip():  # Zac adds to the archive himself
                event = saga.note_idea((said.group(1) or said.group(2)).strip())
                return self._send(200, json.dumps({"saga": event}).encode("utf-8"), "application/json")
            from core import council

            from core import council_floor

            text = str(body.get("text", ""))
            ready = council_floor.ready_members()
            try:
                message = council.post("zac", text, task=str(body.get("task", ""))[:12],
                                       reply_to=str(body.get("reply_to", ""))[:40],
                                       plan=council_floor.plan(text, sorted(ready)))
            except council.CouncilError as problem:
                return self._send(400, json.dumps({"error": str(problem)}).encode("utf-8"), "application/json")
            # Only Zac's messages set the council going, and each within its own budget (DEC-0081).
            from core.council_floor import STOP

            if not STOP.match(message["text"]):
                threading.Thread(target=_run, args=(message,), daemon=True).start()
            return self._send(200, json.dumps(message).encode("utf-8"), "application/json")

        def _mission(self, body: dict) -> None:
            """Zac creating, starting or pausing a mission (core/work_runner.py). This window is his, at this
            PC, holding its own key; a started mission runs here while the window is open."""
            from core import work_runner

            act = str(body.get("act", ""))
            try:
                if act == "new":
                    scope = [s.strip() for s in str(body.get("scope", "")).split(",") if s.strip()]
                    m = work_runner.new(str(body.get("goal", ""))[:300], scope, tasks=int(body.get("tasks") or 5),
                                        hours=float(body.get("hours") or 8))
                elif act in ("start", "pause", "done"):
                    m = work_runner.set_status(str(body.get("id", "")), {"start": "active", "pause": "paused",
                                                                         "done": "done"}[act], "zac")
                    if act == "start":
                        threading.Thread(target=_run_mission, args=(m.id,), daemon=True).start()
                else:
                    raise ValueError("New, start, pause or done.")
            except ValueError as problem:
                return self._send(400, json.dumps({"error": str(problem)}).encode("utf-8"), "application/json")
            return self._send(200, json.dumps({"id": m.id, "status": m.status}).encode("utf-8"), "application/json")

        def _saga(self, body: dict) -> None:
            """Zac deciding on the Chronicle Archive's candidates (core/saga.py)."""
            from core import saga

            act, ref = str(body.get("action", "")), str(body.get("ref", ""))
            try:
                if act in ("accept", "private"):
                    found = next((c for c in saga.candidates() if c["ref"] == ref), None)
                    if found is None:
                        raise ValueError("That one's already been decided.")
                    result = saga.accept(found, privacy="series" if act == "accept" else "private")
                elif act == "drop":
                    saga.drop(ref)
                    result = {"dropped": ref}
                elif act in ("series", "unseries"):
                    result = saga.mark(str(body.get("id", "")), "series" if act == "series" else "private")
                else:
                    raise ValueError("Accept, private or drop.")
            except ValueError as problem:
                return self._send(400, json.dumps({"error": str(problem)}).encode("utf-8"), "application/json")
            return self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

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
