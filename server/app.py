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
import tempfile
import threading
import wave
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from core.app_context import AppContext
from core.assistant_turn import AssistantTurn, run_assistant_turn
from core.talk_it_out import apply_followup
from core.finance_summary import build_finance_summary
from core.conversation_manager import Conversation
from core.logger import get_logger
from core.web_push import get_or_create_vapid_keys, send_web_push

log = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "static"

_bearer_scheme = HTTPBearer(auto_error=False)

# ~2.5 minutes of 16 kHz mono 16-bit audio — far longer than one spoken turn.
MAX_VOICE_UPLOAD_BYTES = 5 * 1024 * 1024
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
        # Accepts either the real profile_id or the profile's display
        # name (case-insensitive) — a person testing this from a phone
        # has no way to know their own internal profile_id, only their
        # name, matching what the login form itself now asks for.
        identifier = body.profile_id.strip().lower()
        profile = next(
            (p for p in context.profiles.list_profiles() if p.profile_id == body.profile_id or p.name.strip().lower() == identifier),
            None,
        )
        if profile is None or not context.profiles.verify_password(profile.profile_id, body.password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect profile or password.")
        if not profile.has_password:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Set a password for this profile in MIA's Settings before using MIA remotely.",
            )
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

    # ------------------------------------------------------------------
    # Phone voice — see module docstring
    # ------------------------------------------------------------------

    app.state.voice_conversations: dict[str, Conversation] = {}
    app.state.turn_lock = threading.Lock()

    def conversation_for(profile_id: str) -> Conversation:
        conversations = app.state.voice_conversations
        if profile_id not in conversations:
            conversations[profile_id] = Conversation(conversation_id=f"phone-{profile_id}")
        return conversations[profile_id]

    def speak_to_base64(text: str) -> Optional[str]:
        if context.voice is None or not text:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            synthesized = context.voice.synthesize(text, Path(tmp) / "reply.wav")
            if synthesized is None:
                return None
            return base64.b64encode(Path(synthesized).read_bytes()).decode("ascii")

    def followup_locked(conversation: Conversation, followup) -> None:
        # The model call runs outside the lock (it's slow); saving the
        # journal/memories runs inside it, so it can't interleave with
        # the next turn changing the same conversation.
        raw = context.llm.generate(followup.prompt) if context.llm is not None else None
        with app.state.turn_lock:
            apply_followup(context, conversation, followup, raw)

    def respond(profile_id: str, transcript: str, background: BackgroundTasks) -> dict:
        conversation = conversation_for(profile_id)
        with app.state.turn_lock:
            turn: AssistantTurn = run_assistant_turn(context, conversation, transcript)
        if not turn.llm_available:
            replies = turn.replies + [LLM_UNAVAILABLE_REPLY]
        else:
            replies = turn.replies or ["Done."]
        reply_text = " ".join(replies)
        if turn.followup is not None:
            background.add_task(followup_locked, conversation, turn.followup)
        return {
            "transcript": transcript,
            "replies": replies,
            "reply_text": reply_text,
            "audio_wav_base64": speak_to_base64(reply_text),
        }

    def transcribe_bytes(audio: bytes) -> Optional[str]:
        if context.voice is None:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "utterance.wav"
            wav_path.write_bytes(audio)
            return context.voice.transcribe(wav_path)

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

        transcript = await run_in_threadpool(transcribe_bytes, audio)
        if transcript is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Speech-to-text isn't available on MIA's computer.")
        if not transcript.strip():
            return {
                "transcript": "", "replies": [NOT_HEARD_REPLY], "reply_text": NOT_HEARD_REPLY,
                "audio_wav_base64": await run_in_threadpool(speak_to_base64, NOT_HEARD_REPLY),
            }
        return await run_in_threadpool(respond, profile_id, transcript.strip(), background)

    @app.post("/api/voice/text")
    def voice_text(
        body: VoiceTextRequest, background: BackgroundTasks, profile_id: str = Depends(require_profile_id),
    ) -> dict:
        text = body.text.strip()
        if not text:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Say or type something first.")
        return respond(profile_id, text, background)

    # Finance #4 (2026-09-28): read-only money summary for the phone
    # apps. Same numbers as the desktop (core/finance_summary.py); taken
    # under the turn lock so it never reads half of a phone-made change.
    @app.get("/api/finance/summary")
    def finance_summary(profile_id: str = Depends(require_profile_id)) -> dict:
        with app.state.turn_lock:
            return build_finance_summary(context)

    @app.post("/api/voice/reset")
    def voice_reset(profile_id: str = Depends(require_profile_id)) -> dict:
        app.state.voice_conversations.pop(profile_id, None)
        return {"reset": True}

    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app
