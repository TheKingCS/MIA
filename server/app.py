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
build_core_context() call) — this is what lets Phase 2's auto-push
relay (core.web_push.register_notification_relay(), registered
alongside this server in core/application.py) see
"notification.created" events raised from anywhere in the running app,
GUI-triggered included. See core/application.py's own comment at the
call site for the threading model this implies.

Auth is deliberately simple, matching this project's existing "stdlib
covers it" stance on profile passwords (core/profile_manager.py):
POST /api/login checks a password via
context.profiles.verify_password() and returns an opaque bearer token
(secrets.token_urlsafe()) held in an in-memory dict on the FastAPI
app's own state — no JWT library, no persistence (a server restart
logs everyone out, acceptable for a personal device's first pass).

**Phone voice (2026-09-27)**: `/api/voice/*` lets the phone page hold a
spoken conversation with the full desktop MIA. The phone records and
encodes a 16 kHz mono WAV itself (no ffmpeg needed here), this server
transcribes it with the same offline Vosk model the desktop uses,
runs `core.assistant_turn.run_assistant_turn()` (the exact turn logic
the headless voice loop uses), and returns the reply text plus Piper
speech as base64 WAV. One in-memory conversation per logged-in
profile, reset on request or server restart. Turns are serialized
behind a lock, since the managers the Assistant acts on aren't
thread-safe. Memory extraction runs after the response is sent
(BackgroundTasks), so it never delays the spoken answer.

Remote login requires the profile to have a password: this API can
read and change everything MIA knows, so "no password set" (which the
desktop lock screen treats as open) is refused here.
"""

from __future__ import annotations

import base64
import io
import secrets
import time
import tempfile
from urllib.parse import unquote
import threading
import wave
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from core.email_drafts import as_dict as draft_as_dict
from core.today import describe as describe_today, today_items
from core.mail_send import SendError, send_draft, sender_for
from core.app_context import AppContext
from core.assistant_turn import AssistantTurn, run_assistant_turn
from core.talk_it_out import apply_followup
from core.finance_summary import build_finance_summary
from core.conversation_manager import DEFAULT_TITLE, Conversation
from core.logger import get_logger
from core.main_thread import publish as publish_on_main_thread
from core.personal_data import view_for
from core.web_push import get_or_create_vapid_keys, send_web_push

log = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
# Phase 2 (DEC-0012): MIA's one web front end (Muse's), and the published
# schemas it builds against.
_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "docs" / "schema"
LIVE_TICK_SECONDS = 0.5
LIVE_PING_SECONDS = 15.0

_bearer_scheme = HTTPBearer(auto_error=False)

# ~2.5 minutes of 16 kHz mono 16-bit audio — far longer than one spoken turn.
MAX_VOICE_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DOCUMENT_UPLOAD_BYTES = 25 * 1024 * 1024
LLM_UNAVAILABLE_REPLY = "I can't think right now. My language model at home isn't responding."
NOT_HEARD_REPLY = "Sorry, I didn't catch that."


def validate_voice_wav(audio: bytes) -> None:
    """Pure logic — raises ValueError unless `audio` is a mono 16-bit
    PCM WAV, the only shape Vosk transcribes reliably."""
    if not audio:
        raise ValueError("No audio received.")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                raise ValueError("Audio must be mono 16-bit PCM WAV.")
            if wf.getnframes() == 0:
                raise ValueError("Audio is empty.")
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"Not a valid WAV file: {exc or 'too short'}") from exc


class VoiceTextRequest(BaseModel):
    text: str


class ProposeRequest(BaseModel):
    kind: str
    params: dict = {}


class LoginRequest(BaseModel):
    profile_id: str
    password: str = ""


class PasswordChange(BaseModel):
    current: str
    new: str


class PasswordCheck(BaseModel):
    password: str


class SetupRequest(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""
    country: str = "US"
    interests: list[str] = []


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: PushKeys


PHONE_CONVERSATION_IDLE = timedelta(hours=6)


def _idle_too_long(conversation: Conversation, now: Optional[datetime] = None) -> bool:
    try:
        last = datetime.fromisoformat(conversation.updated_at)
    except (TypeError, ValueError):
        return False
    return (now or datetime.now()) - last > PHONE_CONVERSATION_IDLE


def phone_title(prompt: str) -> str:
    """Pure logic. '📱 What's on my schedule today' from the first thing said."""
    words = " ".join(prompt.split())
    return "\U0001F4F1 " + (words[:40].rstrip() + "…" if len(words) > 40 else words or "Phone")


def turn_timings(hearing: Optional[float], thinking: float, speaking: float) -> dict:
    """Pure logic. Where a phone turn's time went, in seconds (one decimal),
    so "MIA is slow on the drive home" can be traced to one stage:
    hearing (speech-to-text), thinking (the model and any tools), speaking
    (making the voice reply)."""
    timings = {"thinking": round(thinking, 1), "speaking": round(speaking, 1)}
    if hearing is not None:
        timings = {"hearing": round(hearing, 1), **timings}
    return timings


def describe_timings(timings: dict) -> str:
    """Pure logic. 'heard 1.2s · thought 3.4s · spoke 0.8s'."""
    words = {"hearing": "heard", "thinking": "thought", "speaking": "spoke"}
    return " · ".join(f"{words[k]} {v:.1f}s" for k, v in timings.items())


def create_app(context: AppContext) -> FastAPI:
    app = FastAPI(title="MIA Mobile API")
    app.state.context = context
    app.state.sessions: dict[str, str] = {}  # token -> profile_id
    # The phone app (android-phone/mia_phone.py) switches these on: making
    # the device's first account, and staying signed in between starts.
    # Never on a computer's server, which other devices can reach.
    app.state.allow_setup = False
    app.state.remember_sign_in = False
    # token -> when that phone last used MIA (Settings shows "phone last connected").
    app.state.last_seen: dict[str, float] = {}

    @app.middleware("http")
    async def phone_access_switch(request: Request, call_next):
        """When phone access is off, the server may still run for the
        desktop's own web view (core/phone_server.py ensure_local()), but
        anything forwarded in from outside (Tailscale serve, a proxy) is
        turned away."""
        server = getattr(context, "phone_server", None)
        forwarded = any(h in request.headers for h in ("x-forwarded-for", "tailscale-user-login", "forwarded"))
        if forwarded and server is not None and not getattr(server, "enabled", True):
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Phone access is off in MIA's Settings."}, status_code=403)
        return await call_next(request)

    def require_profile_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> str:
        if credentials is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token.")
        profile_id = app.state.sessions.get(credentials.credentials)
        if profile_id is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session.")
        app.state.last_seen[credentials.credentials] = time.time()
        return profile_id

    def _remember(profile_id: Optional[str]) -> None:
        """The phone stays signed in between starts until the person logs out."""
        if app.state.remember_sign_in:
            context.config.set("phone.signed_in_profile_id", profile_id)
            context.config.save()

    @app.post("/api/logout")
    def logout(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
        """Ends this session on this device (the web's account menu, 2026-10-07)."""
        if credentials is not None:
            profile_id = app.state.sessions.pop(credentials.credentials, None)
            app.state.last_seen.pop(credentials.credentials, None)
            if profile_id and context.config.get("phone.signed_in_profile_id") == profile_id:
                _remember(None)
        return {"signed_out": True}

    @app.get("/api/setup")
    def setup_status() -> dict:
        """Whether this device still needs its first account (the phone app only)."""
        from core.first_account import setup_page

        if not app.state.allow_setup:
            return {"needed": False}
        with app.state.turn_lock:
            return setup_page(context)

    @app.post("/api/setup")
    def setup(body: SetupRequest) -> dict:
        """Makes the device's first account and signs it in (DEC-0019, the phone)."""
        from core.first_account import create_first_account
        from core.profile_manager import AccountError

        if not app.state.allow_setup:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accounts are made in MIA on this device.")
        with app.state.turn_lock:
            try:
                profile, code = create_first_account(context, body.name, body.email, body.password, body.country,
                                                     body.interests)
            except AccountError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        token = secrets.token_urlsafe(32)
        app.state.sessions[token] = profile.profile_id
        app.state.last_seen[token] = time.time()
        _remember(profile.profile_id)
        log.info("First account made on this device: '%s'.", profile.profile_id)
        return {"token": token, "profile_id": profile.profile_id, "name": profile.name, "recovery_code": code}

    @app.post("/api/login")
    def login(body: LoginRequest) -> dict:
        # Accepts the person's email (accounts, 2026-10-01), or for
        # profiles made before emails their profile_id or display name
        # (case-insensitive, only when no one else has that name).
        profile = context.profiles.find_for_sign_in(body.profile_id)
        if profile is None or not context.profiles.verify_password(profile.profile_id, body.password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect profile or password.")
        if not profile.has_password:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Set a password for this profile in MIA's Settings before using MIA remotely.",
            )
        token = secrets.token_urlsafe(32)
        app.state.sessions[token] = profile.profile_id
        app.state.last_seen[token] = time.time()
        _remember(profile.profile_id)
        log.info("Mobile login for profile '%s'.", profile.profile_id)
        return {"token": token, "profile_id": profile.profile_id, "name": profile.name}

    @app.get("/api/vapid-public-key")
    def vapid_public_key() -> dict:
        try:
            _, public_key_b64 = get_or_create_vapid_keys()
        except RuntimeError as unavailable:  # MIA on a phone (DEC-0019)
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(unavailable)) from None
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

    # ------------------------------------------------------------------
    # Phone voice — see module docstring
    # ------------------------------------------------------------------

    app.state.voice_conversations: dict[str, Conversation] = {}
    app.state.turn_lock = threading.Lock()

    def conversation_for(profile_id: str, view=None) -> Conversation:
        """2026-09-28: phone conversations are saved with the desktop's
        (the Assistant's History, titled "📱 ..."), so a drive-home chat
        can be picked up at the desk. A new one after PHONE_CONVERSATION_IDLE
        of quiet, like starting a new chat. Without a conversation store
        (tests, headless), kept in memory as before."""
        conversations = app.state.voice_conversations
        current = conversations.get(profile_id)
        manager = getattr(view if view is not None else context, "conversations", None)
        if manager is None:
            if current is None:
                current = conversations[profile_id] = Conversation(conversation_id=f"phone-{profile_id}")
            return current
        stored = manager.get_conversation(current.conversation_id) if current is not None else None
        if stored is None or _idle_too_long(stored):
            stored = manager.create_conversation()
            conversations[profile_id] = stored
        return stored

    def after_phone_turn(conversation: Conversation, prompt: str, view=None) -> None:
        """Save the turn and let the desktop's History show it."""
        manager = getattr(view if view is not None else context, "conversations", None)
        if manager is None or manager.get_conversation(conversation.conversation_id) is not conversation:
            return
        if conversation.title == DEFAULT_TITLE and not conversation.current_privacy():
            conversation.title = phone_title(prompt)
        conversation.updated_at = datetime.now().isoformat(timespec="seconds")
        manager.save()
        publish_on_main_thread(context, "conversation.updated", conversation_id=conversation.conversation_id)

    def speak_to_base64(text: str) -> Optional[str]:
        if context.voice is None or not text:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            synthesized = context.voice.synthesize(text, Path(tmp) / "reply.wav")
            if synthesized is None:
                return None
            return base64.b64encode(Path(synthesized).read_bytes()).decode("ascii")

    def followup_locked(conversation: Conversation, followup, view=None) -> None:
        # The model call runs outside the lock (it's slow); saving the
        # journal/memories runs inside it, so it can't interleave with
        # the next turn changing the same conversation.
        view = view if view is not None else context
        raw = context.llm.generate(followup.prompt) if context.llm is not None else None
        with app.state.turn_lock:
            apply_followup(view, conversation, followup, raw)
            manager = getattr(view, "conversations", None)
            if manager is not None and manager.get_conversation(conversation.conversation_id) is conversation:
                manager.save()

    def respond(profile_id: str, transcript: str, background: BackgroundTasks, hearing: Optional[float] = None) -> dict:
        # The phone user's own view: their conversations, memories, journal
        # and reasons, whoever is signed in at the desktop (core/personal_data.py).
        view = view_for(context, profile_id)
        conversation = conversation_for(profile_id, view)
        started = time.monotonic()
        drafts = getattr(view, "email_drafts", None)
        with app.state.turn_lock:
            before = drafts.latest() if drafts is not None else None
            turn: AssistantTurn = run_assistant_turn(view, conversation, transcript)
            after_phone_turn(conversation, transcript, view)
            # An email MIA drafted this turn, shown with Send / Copy / mail app
            # (core/email_drafts.py); sent only when the phone's Send is pressed.
            after = drafts.latest() if drafts is not None else None
            new_draft = draft_as_dict(after) if after is not None and after is not before else None
        thinking = time.monotonic() - started
        if not turn.llm_available:
            replies = turn.replies + [LLM_UNAVAILABLE_REPLY]
        else:
            replies = turn.replies or ["Done."]
        reply_text = " ".join(replies)
        if turn.followup is not None:
            background.add_task(followup_locked, conversation, turn.followup, view)
        started = time.monotonic()
        audio = speak_to_base64(reply_text)
        timings = turn_timings(hearing, thinking, time.monotonic() - started)
        log.info("Phone turn: %s", describe_timings(timings))
        return {
            "transcript": transcript,
            "replies": replies,
            "reply_text": reply_text,
            "audio_wav_base64": audio,
            "timings": timings,
            "draft": new_draft,
        }

    def transcribe_bytes(audio: bytes) -> Optional[str]:
        if context.voice is None:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "utterance.wav"
            wav_path.write_bytes(audio)
            return context.voice.transcribe(wav_path)

    # ---------------------------------------------------------------- email drafts

    def person_drafts(profile_id: str):
        drafts = getattr(view_for(context, profile_id), "email_drafts", None)
        if drafts is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No drafts here.")
        return drafts

    @app.get("/api/email/drafts")
    def email_drafts(profile_id: str = Depends(require_profile_id)) -> dict:
        return {"drafts": [draft_as_dict(d) for d in person_drafts(profile_id).open_drafts()],
                "can_send": sender_for(context, profile_id).configured}

    @app.post("/api/email/drafts/{draft_id}/send")
    def email_send(draft_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """Only the phone's Send button calls this; MIA never sends by herself."""
        sender = sender_for(context, profile_id)
        if sender.configured and not sender.unlocked:
            raise HTTPException(status.HTTP_423_LOCKED,
                                "Sending is locked: press Send once on the computer this session, or use Copy.")
        with app.state.turn_lock:
            try:
                return {"message": send_draft(context, profile_id, draft_id)}
            except SendError as exc:
                raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    @app.post("/api/email/drafts/{draft_id}/discard")
    def email_discard(draft_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        with app.state.turn_lock:
            person_drafts(profile_id).mark(draft_id, "discarded")
        return {"discarded": True}

    @app.get("/api/today")
    def today(profile_id: str = Depends(require_profile_id)) -> dict:
        """Today on the phone (core/today.py): the person's own day."""
        with app.state.turn_lock:
            items = today_items(view_for(context, profile_id))
        return {"items": [i.as_dict() for i in items], "spoken": describe_today(items)}

    @app.get("/api/voice/status")
    def voice_status(profile_id: str = Depends(require_profile_id)) -> dict:
        voice = context.voice
        return {
            "speech_to_text": bool(voice and voice.is_stt_available()),
            "text_to_speech": bool(voice and voice.is_tts_available()),
            "assistant": bool(context.llm and context.llm.is_available()),
        }

    @app.post("/api/voice/turn")
    async def voice_turn(
        request: Request, background: BackgroundTasks, profile_id: str = Depends(require_profile_id),
    ) -> dict:
        audio = await request.body()
        if len(audio) > MAX_VOICE_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Recording too long.")
        try:
            validate_voice_wav(audio)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

        started = time.monotonic()
        transcript = await run_in_threadpool(transcribe_bytes, audio)
        hearing = time.monotonic() - started
        if transcript is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Speech-to-text isn't available on MIA's computer.")
        if not transcript.strip():
            return {
                "transcript": "", "replies": [NOT_HEARD_REPLY], "reply_text": NOT_HEARD_REPLY,
                "audio_wav_base64": await run_in_threadpool(speak_to_base64, NOT_HEARD_REPLY),
            }
        return await run_in_threadpool(respond, profile_id, transcript.strip(), background, hearing)

    @app.post("/api/voice/text")
    def voice_text(
        body: VoiceTextRequest, background: BackgroundTasks, profile_id: str = Depends(require_profile_id),
    ) -> dict:
        text = body.text.strip()
        if not text:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Say or type something first.")
        return respond(profile_id, text, background)

    # Document inbox (core/inbox_manager.py): a file sent from the phone
    # (a receipt photo, a manual PDF). Raw body + X-Filename header, so no
    # multipart parser dependency. Only writes the file; the desktop's
    # inbox scan takes it from there within a minute.
    @app.post("/api/inbox/upload")
    async def inbox_upload(request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        if context.inbox is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The inbox isn't available on MIA's computer.")
        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file received.")
        filename = unquote(request.headers.get("x-filename", "upload"))
        try:
            context.inbox.receive_file(filename, data, source="phone")
        except ValueError as exc:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc
        return {"received": filename, "message": "Got it. It'll be in your inbox in a minute."}

    # Finance #4 (2026-09-28): read-only money summary for the phone
    # apps. Same numbers as the desktop (core/finance_summary.py); taken
    # under the turn lock so it never reads half of a phone-made change.
    @app.get("/api/finance/summary")
    def finance_summary(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.child_accounts import ASK_A_PARENT, is_child

        if is_child(context, profile_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, ASK_A_PARENT)
        with app.state.turn_lock:
            # The phone user's own money: a private budget if they keep one.
            return build_finance_summary(view_for(context, profile_id))

    # Engine Phase 1 (2026-10-05): the person's whole Life State v2
    # (core/context_assembler.py), the one read model every surface
    # uses: this phone app, a mock-up, glasses. Shape:
    # docs/schema/life_state.schema.json. Their own view, so a phone
    # user gets their own picture (a child, no money).
    @app.get("/api/state")
    def life_state(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.context_assembler import assemble_life_state_v2

        with app.state.turn_lock:
            return assemble_life_state_v2(view_for(context, profile_id))

    # DEC-0017 (2026-10-06): the web shell (the person's apps, level and
    # XP), the Dashboard and the Apps page, assembled in core/web_surfaces.py.
    @app.get("/api/shell")
    def web_shell(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_surfaces import shell

        with app.state.turn_lock:
            return shell(view_for(context, profile_id))

    @app.get("/api/apps")
    def web_apps(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_surfaces import apps_page

        with app.state.turn_lock:
            return apps_page(view_for(context, profile_id))

    # The Money screen (DEC-0017): everything the PC's Budget screen shows
    # (core/web_money.py); changes are the money action kinds.
    @app.get("/api/money")
    def web_money(strategy: str = "hybrid", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.child_accounts import ASK_A_PARENT, is_child
        from core.web_money import money_page

        if is_child(context, profile_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, ASK_A_PARENT)
        with app.state.turn_lock:
            return money_page(view_for(context, profile_id), strategy=strategy)

    # Garage, Property, Greenhouse, Maintenance and one page per asset
    # (DEC-0017, core/web_equipment.py). A child reaches only the scopes
    # their apps allow (core/child_accounts.CHILD_APPS: the greenhouse).
    def _equipment_allowed(view, scope: str) -> None:
        from core.child_accounts import ASK_A_PARENT, app_allowed

        if not app_allowed(view, scope):
            raise HTTPException(status.HTTP_403_FORBIDDEN, ASK_A_PARENT)

    def _asset_for(view, asset_id: str):
        from core.web_equipment import scope_of

        maintenance = getattr(view, "maintenance", None)
        asset = maintenance.get_asset(asset_id) if maintenance is not None else None
        if asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That isn't here anymore.")
        _equipment_allowed(view, scope_of(asset.category))
        return asset

    @app.get("/api/equipment")
    def web_equipment(scope: str = "maintenance", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_equipment import SCOPES, equipment_page

        view = view_for(context, profile_id)
        _equipment_allowed(view, scope if scope in SCOPES else "maintenance")
        with app.state.turn_lock:
            return equipment_page(view, scope)

    @app.get("/api/assets/{asset_id}")
    def web_asset(asset_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_equipment import asset_page

        view = view_for(context, profile_id)
        with app.state.turn_lock:
            _asset_for(view, asset_id)
            return asset_page(view, asset_id)

    @app.get("/api/assets/{asset_id}/documents/{filename}")
    def web_asset_document(asset_id: str, filename: str, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        view = view_for(context, profile_id)
        asset = _asset_for(view, asset_id)
        if filename not in asset.documents or Path(filename).name != filename:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such document.")
        path = view.maintenance.document_path(asset_id, filename)
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That file is missing on MIA's computer.")
        return FileResponse(path, filename=filename)

    # A document sent from the phone or browser onto an asset (a manual,
    # a receipt, a warranty): raw body + X-Filename, like the inbox.
    @app.post("/api/assets/{asset_id}/documents")
    async def web_asset_upload(asset_id: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        view = view_for(context, profile_id)
        asset = _asset_for(view, asset_id)
        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file received.")
        if len(data) > MAX_DOCUMENT_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is over 25 MB.")
        name = Path(unquote(request.headers.get("x-filename", "document"))).name.strip() or "document"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / name
            source.write_bytes(data)
            with app.state.turn_lock:
                stored = view.maintenance.add_document(asset.asset_id, source)
        return {"added": stored, "message": f"{stored} is on {asset.name} now."}

    # Kitchen, Workout, Real Estate (DEC-0017/0018, core/web_screens.py).
    def _screen(profile_id: str, app_id: str, build):
        from core.child_accounts import ASK_A_PARENT, app_allowed

        view = view_for(context, profile_id)
        if not app_allowed(view, app_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, ASK_A_PARENT)
        with app.state.turn_lock:
            return build(view)

    @app.get("/api/kitchen")
    def web_kitchen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_screens import kitchen_page

        return _screen(profile_id, "kitchen", kitchen_page)

    @app.get("/api/workout")
    def web_workout(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_screens import workout_page

        return _screen(profile_id, "workout", workout_page)

    @app.get("/api/real-estate")
    def web_real_estate(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_screens import estate_page

        return _screen(profile_id, "real_estate", estate_page)

    # Missions, Skills, Character (DEC-0017/0018, H-0013; core/web_progress.py).
    @app.get("/api/missions")
    def web_missions(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_progress import missions_page

        return _screen(profile_id, "missions", missions_page)

    @app.get("/api/skills")
    def web_skills(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_progress import skills_page

        return _screen(profile_id, "skills", skills_page)

    @app.get("/api/profile")
    def web_profile(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_account import profile_page

        with app.state.turn_lock:
            return profile_page(view_for(context, profile_id))

    @app.get("/api/settings")
    def web_settings(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_account import settings_page

        with app.state.turn_lock:
            return settings_page(view_for(context, profile_id))

    @app.post("/api/account/password")
    def change_password(body: PasswordChange, profile_id: str = Depends(require_profile_id)) -> dict:
        """Not an action: a password never sits in a proposal or the undo log."""
        from core.first_account import MIN_PASSWORD

        if not context.profiles.verify_password(profile_id, body.current):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password isn't right.")
        if len(body.new or "") < MIN_PASSWORD:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Pick a password of at least {MIN_PASSWORD} characters.")
        with app.state.turn_lock:
            context.profiles.set_password(profile_id, body.new)
        log.info("Password changed from the web for profile '%s'.", profile_id)
        return {"changed": True}

    @app.post("/api/account/recovery-code")
    def new_recovery_code(body: PasswordCheck, profile_id: str = Depends(require_profile_id)) -> dict:
        """A new recovery code (the old one stops working), shown once."""
        if not context.profiles.verify_password(profile_id, body.password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That password isn't right.")
        with app.state.turn_lock:
            code = context.profiles.issue_recovery_code(profile_id)
        return {"recovery_code": code}

    @app.get("/api/character")
    def web_character(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_progress import character_page

        return _screen(profile_id, "character", character_page)

    @app.get("/api/dashboard")
    def web_dashboard(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_surfaces import dashboard

        with app.state.turn_lock:
            return dashboard(view_for(context, profile_id))

    # ------------------------------------------------------------------
    # The action contract (core/actions.py, DEC-0013):
    # Propose → Approve → Execute → Record → Undo. Each step runs on the
    # person's own view, under the turn lock like any other change.
    # ------------------------------------------------------------------

    def _actions():
        center = getattr(context, "actions", None)
        if center is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Actions aren't available.")
        return center

    def _decide(step, profile_id: str, proposal_id: str) -> dict:
        from core.actions import ActionError

        try:
            with app.state.turn_lock:
                return step(view_for(context, profile_id), proposal_id).as_dict()
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such proposal.") from None
        except ActionError as problem:
            raise HTTPException(status.HTTP_409_CONFLICT, str(problem)) from None

    @app.get("/api/actions/kinds")
    def action_kinds(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.actions import ACTION_TYPES

        return {"kinds": [a.as_dict() for a in ACTION_TYPES.values()]}

    @app.post("/api/actions/propose")
    def propose_action(body: ProposeRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.actions import ActionError

        try:
            with app.state.turn_lock:
                return _actions().propose(view_for(context, profile_id), body.kind, body.params).as_dict()
        except ActionError as problem:
            raise HTTPException(status.HTTP_409_CONFLICT, str(problem)) from None

    @app.get("/api/actions")
    def pending_actions(profile_id: str = Depends(require_profile_id)) -> dict:
        return {"proposals": [p.as_dict() for p in _actions().pending(profile_id)]}

    @app.post("/api/actions/{proposal_id}/approve")
    def approve_action(proposal_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        return _decide(_actions().approve, profile_id, proposal_id)

    @app.post("/api/actions/{proposal_id}/reject")
    def reject_action(proposal_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        return _decide(_actions().reject, profile_id, proposal_id)

    @app.post("/api/actions/{proposal_id}/undo")
    def undo_action(proposal_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        return _decide(_actions().undo, profile_id, proposal_id)

    # ------------------------------------------------------------------
    # Live updates (core/live.py): the state version, as one read or a
    # stream (Server-Sent Events; EventSource can't send headers, so the
    # stream takes the token as ?token=). A surface re-reads /api/state
    # when the version moves.
    # ------------------------------------------------------------------

    @app.get("/api/live/version")
    def live_version(profile_id: str = Depends(require_profile_id)) -> dict:
        from core import live

        return {"version": live.version()}

    @app.get("/api/live")
    async def live_stream(request: Request, token: str = "", since: int = -1, once: bool = False):
        import asyncio
        import json as json_module

        from fastapi.responses import StreamingResponse

        from core import live

        if app.state.sessions.get(token) is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session.")

        async def events():
            seen, quiet = since, 0.0
            while True:
                current = live.version()
                if current != seen:
                    seen, quiet = current, 0.0
                    yield f"event: state\ndata: {json_module.dumps({'version': current})}\n\n"
                    if once:
                        return
                elif quiet >= LIVE_PING_SECONDS:
                    quiet = 0.0
                    yield ": ping\n\n"
                if await request.is_disconnected():
                    return
                await asyncio.sleep(LIVE_TICK_SECONDS)
                quiet += LIVE_TICK_SECONDS

        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/voice/reset")
    def voice_reset(profile_id: str = Depends(require_profile_id)) -> dict:
        app.state.voice_conversations.pop(profile_id, None)
        return {"reset": True}

    # The web front end (web/, DEC-0012) and the schemas it's built on.
    # Mounted before "/" so the phone app keeps the root.
    if _WEB_DIR.is_dir():
        app.mount("/web", StaticFiles(directory=_WEB_DIR, html=True), name="web")
    if _SCHEMA_DIR.is_dir():  # the preview's examples; MIA on a phone ships without them (DEC-0019)
        app.mount("/schema", StaticFiles(directory=_SCHEMA_DIR), name="schema")
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app
