"""The web screens are never served from a stale browser copy (Zac,
2026-10-16: after a phone update the old Dashboard kept showing)."""

from fastapi import FastAPI
from starlette.testclient import TestClient

from server.app import _Fresh


def test_web_files_must_be_rechecked_and_unchanged_ones_are_cheap():
    app = FastAPI()
    app.mount("/web", _Fresh(directory="web", html=True))
    client = TestClient(app)
    first = client.get("/web/dashboard.js")
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-cache"
    again = client.get("/web/dashboard.js", headers={"if-none-match": first.headers["etag"]})
    assert again.status_code == 304
