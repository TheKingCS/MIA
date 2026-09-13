"""
server.app
============

The Mobile access Phase 1 API (see the "Mobile access, Phase 1" plan,
2026-09-12): a small FastAPI app proving the Web Push pipeline
end-to-end (login -> get VAPID public key -> subscribe -> send a test
push), plus a bare static PWA shell. Deliberately minimal — no real
dashboard endpoints yet; that's separate, later scope.

create_app(context) takes the *same*, already-constructed AppContext
core/application.py's MIAApplication is running (not a fresh
build_core_context() call) — this is what lets a future auto-push
integration (subscribing to "notification.created" on context.events)
see events from anywhere in the running app, GUI-triggered included.
See core/application.py's own comment at the call site for the
threading model this implies.

Auth is deliberately simple, matching this project's existing "stdlib
covers it" stance on profile passwords (core/profile_manager.py):
POST /api/login checks a password via
context.profiles.verify_password() and returns an opaque bearer token
(secrets.token_urlsafe()) held in an in-memory dict on the FastAPI
app's own state — no JWT library, no persistence (a server restart
logs everyone out, acceptable for a personal device's first pass).
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.app_context import AppContext
from core.logger import get_logger
from core.web_push import get_or_create_vapid_keys, send_web_push

log = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "static"

_bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    profile_id: str
    password: str = ""


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: PushKeys


def create_app(context: AppContext) -> FastAPI:
    app = FastAPI(title="MIA Mobile API")
    app.state.context = context
    app.state.sessions: dict[str, str] = {}  # token -> profile_id

    def require_profile_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> str:
        if credentials is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token.")
        profile_id = app.state.sessions.get(credentials.credentials)
        if profile_id is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session.")
        return profile_id

    @app.post("/api/login")
    def login(body: LoginRequest) -> dict:
        profile = next((p for p in context.profiles.list_profiles() if p.profile_id == body.profile_id), None)
        if profile is None or not context.profiles.verify_password(body.profile_id, body.password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect profile or password.")
        token = secrets.token_urlsafe(32)
        app.state.sessions[token] = profile.profile_id
        log.info("Mobile login for profile '%s'.", profile.profile_id)
        return {"token": token, "profile_id": profile.profile_id, "name": profile.name}

    @app.get("/api/vapid-public-key")
    def vapid_public_key() -> dict:
        _, public_key_b64 = get_or_create_vapid_keys()
        return {"public_key": public_key_b64}

    @app.post("/api/push/subscribe")
    def push_subscribe(body: SubscribeRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        if context.push_subscriptions is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Push subscriptions are not available.")
        context.push_subscriptions.add_subscription(
            profile_id=profile_id,
            endpoint=body.endpoint,
            p256dh_key=body.keys.p256dh,
            auth_key=body.keys.auth,
        )
        return {"subscribed": True}

    @app.post("/api/push/test")
    def push_test(profile_id: str = Depends(require_profile_id)) -> dict:
        if context.push_subscriptions is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Push subscriptions are not available.")
        subscriptions = context.push_subscriptions.subscriptions_for_profile(profile_id)
        if not subscriptions:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No push subscriptions registered for this profile.")
        sent = sum(
            1 for sub in subscriptions
            if send_web_push(sub, "MIA", "This is a test notification from MIA.", context.push_subscriptions)
        )
        return {"sent": sent, "attempted": len(subscriptions)}

    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app
