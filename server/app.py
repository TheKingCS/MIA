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

**A sensor's own key** (2026-11-09, core/sensors.py): `/api/sensors/reading` takes no sign-in, only
the sensor's key in X-Sensor-Key (`SensorReading`), and can do one thing: log a number to that
sensor's series. Adding a sensor (`SensorAdd`) returns its key once.

**Secrets from the web** (2026-11-07): the inbox's email setup and unlock
(`/api/inbox/email*`) take a password and passphrase in their own request
models (`MailSetupRequest`, `MailUnlockRequest`), handed straight to
core/inbox_mail.py's encrypted vault: never an action (whose parameters
are kept), never logged. The ID wallet's cards (`/api/wallet`, `WalletCard`,
2026-11-08) are the same: a card's number goes only through its own
request to core/id_wallet.py, sealed at rest; lists mask it. MIA paints on this
PC's graphics card (`ArtRequest`, /api/art, core/art_studio.py, DEC-0140) and
serves each person only their own pictures. The Theme Studio
asks MIA to design a theme from a description (`ThemeDesignRequest`, POST
/api/themes/design, core/theme_design.py) or to mix two (`ThemeMixRequest`,
POST /api/themes/mix, core/themes.combine): nothing is kept there; saving is
an action.

**My Directions and How MIA Answers** (2026-11-08): `/api/directions`
(core/web_directions.py, DEC-0141) and `/api/answers` (core/answer_compare.py,
DEC-0138) are read here; changes are direction.* and style.* actions. Now and
then after a reply, `/api/talk/compare` (`CompareRequest`) has the model say it
a second way, outside the turn lock, and code checks no number changed; a
reply in a private conversation is never compared (each turn says whether it
may be: `comparable`).

**Trail maps and past conversations** (2026-11-08): `/api/trail-maps` (a PDF
sent as the raw body to `/upload`, or downloaded from a link the person gave
by `/fetch`, `TrailLinkRequest`, outside the turn lock; core/web_trails.py),
and `/api/talk/conversations` with `/api/talk/continue` (`ContinueRequest`):
the person's own kept conversations, read, picked back up or deleted (an
action); private turns were never kept, so never shown. One conversation
(`current` for the one Talk is in) is also exported as text at
`/api/talk/conversations/{id}/export` and summarised whole at `/summary`
(core/conversation_export.py; the model runs outside the turn lock).

**MIA's browser, live** (2026-11-07): `/api/browser/frame` (a picture of
her browser now) and `/api/browser/input` (the person's click, typing, key
or scroll, `BrowserInputRequest`) skip the turn lock so the live view stays
smooth while she thinks; her browser has its own lock.

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
from urllib.parse import quote, unquote
import threading
import wave
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
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


class _Fresh(StaticFiles):
    """Static files a browser must re-check every time (ETag, so an unchanged
    file costs a 304). Without it the phone's web view kept showing the
    screens of an older app version after an update (Zac, 2026-10-16)."""

    def file_response(self, *args, **kwargs):
        """The file's response with Cache-Control: no-cache, so the browser revalidates it every time."""
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


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
# Said like a person, with a way forward (Zac, 2026-10-27: "avoid her saying I don't know what to do").
LLM_UNAVAILABLE_REPLY = ("I'm having trouble thinking that one through right now: my home computer isn't answering "
                         "(it might be asleep or restarting). Quick things still work, like “add milk to the list” "
                         "or “what's on today”.")
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


class PageErrorRequest(BaseModel):
    """A web page reporting that it broke: which page and the error (both length-capped), for the apps-that-broke loop."""
    page: str = Field(default="", max_length=120)
    message: str = Field(default="", max_length=400)


class NewsHeardRequest(BaseModel):
    """Good News Radio's page saying its episode was played, and in whose voice."""
    personality: str = Field(default="", max_length=40)


class PageOpenedRequest(BaseModel):
    """A web page saying it was opened, for which apps are used."""
    page: str = Field(default="", max_length=120)


class MailSetupRequest(BaseModel):
    """Setting up the inbox's mailbox from the web: the server, address, app password, the passphrase that encrypts it,
    and whether it's the person's everyday mailbox. Never logged or kept beyond the encrypted vault."""
    host: str = Field(default="imap.gmail.com", max_length=200)
    address: str = Field(default="", max_length=200)
    password: str = Field(default="", max_length=400)
    passphrase: str = Field(default="", max_length=400)
    everyday: bool = True


class BrowserInputRequest(BaseModel):
    """The person working MIA's browser from the live view: a click at x, y (the page's own pixels), typing, a key,
    or a scroll."""
    kind: str = Field(default="click", max_length=10)
    x: float = 0
    y: float = 0
    text: str = Field(default="", max_length=2000)
    key: str = Field(default="", max_length=20)
    dy: float = 0


class MailUnlockRequest(BaseModel):
    """Unlocking the stored mailbox password for this run of MIA."""
    passphrase: str = Field(default="", max_length=400)


class VoiceTextRequest(BaseModel):
    """What the phone or glasses heard, as text."""
    text: str


class UserSyncRequest(BaseModel):
    """One step of syncing a person's phone (core/user_sync.py): what they said, their choice (start, approve, drop, skip, continue, later), which item, and what the phone app says it's allowed to read."""
    text: str = ""
    choice: str = ""  # start | approve | drop | skip | continue | later
    index: int = -1
    permissions: Optional[dict] = None  # what the phone app says is allowed


class WelcomeRequest(BaseModel):
    """A choice in the first mission or a tour (core/welcome.py), and the app it's about."""
    choice: str
    app: str = ""


class OrbStateRequest(BaseModel):
    """The state MIA's orb should show (listening, thinking...)."""
    state: str


class ProposeRequest(BaseModel):
    """An action proposed from a page: its kind (core/actions.py) and parameters."""
    kind: str
    params: dict = {}


class SyncFileRequest(BaseModel):
    """A file synced from the phone: its scope and name, the hash it's expected to replace ("" for new), and its contents in base64."""
    scope: str
    name: str
    expect: str = ""
    data: str  # base64


class PasswordVaultRequest(BaseModel):
    """Unlocking or changing the password vault: the master password, the recovery code, or the new master."""
    master: str = ""
    recovery: str = ""
    new: str = ""


class VaultLoginRequest(BaseModel):  # a login in the password vault (not signing in to MIA: LoginRequest)
    """A login kept in the password vault (not signing in to MIA: that's LoginRequest): title, username, password, site, note and folder; keep_password leaves the saved password as it is."""
    entry_id: str = ""
    title: str = ""
    username: str = ""
    password: str = ""
    url: str = ""
    note: str = ""
    folder: str = ""
    keep_password: bool = False


class CsvRequest(BaseModel):
    """CSV text to import (a password export)."""
    text: str


class VaultShasRequest(BaseModel):
    """Photo hashes the phone has, to learn which the vault already keeps."""
    shas: list[str]


class VaultFreeRequest(BaseModel):
    """What to free on the phone because the vault keeps it safely: old photos, copies, or one burst, and the paths."""
    what: str = ""  # "old" | "copies" | "burst:<id>"
    paths: list[str] = []


class CameraRequest(BaseModel):
    """A camera added or changed: name, place, brand, host and stream path, login (None keeps the saved password), and whether a phone is setting it up on the linked home computer."""
    camera_id: Optional[str] = None
    name: str
    location: str = "Other"
    brand: str
    host: str
    path: str = ""
    user: str = ""
    password: Optional[str] = None  # None keeps the one saved
    on_pc: bool = False  # a phone setting up a camera on the linked home computer


class HomeLinkRequest(BaseModel):
    """Linking a phone to the home computer (core/home_link.py): its address, who is linking, their password, and the
    authenticator's code when two-step sign-in is on there."""
    url: str
    who: str
    password: str
    code: str = ""  # the authenticator's code, when two-step sign-in is on there


class ModelChatRequest(BaseModel):
    """A chat turn run on the home computer's model for a linked phone: the messages and the tools."""
    messages: list[dict]
    tools: list[dict] = []


class LoginRequest(BaseModel):
    """Signing in to MIA: the profile and its password, and the authenticator's code when two-step sign-in is on."""
    profile_id: str
    password: str = ""
    code: str = ""


class AccountDataRequest(BaseModel):
    """Exporting or deleting an account: the password; for export, whether the household's files go too; for delete,
    whether the archived folder is erased for good."""
    password: str = ""
    include_household: bool = False
    erase: bool = False


class TwoStepRequest(BaseModel):
    """Setting up or turning off two-step sign-in: the password, and a code from the authenticator app."""
    password: str = ""
    code: str = ""


TWO_STEP_ASK = "Enter the 6-digit code from your authenticator app."


class ModelStep(BaseModel):
    """A step of getting a model ready: which model and how far along."""
    model: str = ""
    count: int = 0


class PasswordChange(BaseModel):
    """Changing a person's MIA password: the current one and the new one."""
    current: str
    new: str


class ArtRequest(BaseModel):
    """Something for MIA to paint (core/art_studio.start): the description, what it's for, whether to put it up when
    it's done, and for a portal picture the area whose portal it goes in."""
    description: str = Field(..., max_length=400)
    use: str = "backdrop"
    apply: bool = False
    area: str = Field("", max_length=40)  # a portal picture: the area whose portal it goes in when done


class CompareRequest(BaseModel):
    """A reply MIA just gave in Talk, for "this way or that way?" (core/answer_compare.py, DEC-0138); private turns
    are never compared."""
    reply: str = Field(..., max_length=6000)
    private: bool = False


class LookupRequest(BaseModel):
    """Words to look up online (core/web_lookup.look, DEC-0053): pressing Search is the person asking."""
    words: str = Field(..., max_length=300)


class TrailLinkRequest(BaseModel):
    """A trail map PDF to download from a direct link (core/web_trails.add_link): the park, its state, the link."""
    park: str = Field(..., max_length=80)
    state: str = Field(..., max_length=40)
    url: str = Field(..., max_length=2000)
    notes: str = Field("", max_length=300)


class ContinueRequest(BaseModel):
    """A past conversation for Talk to pick back up (core/web_conversations.pick_up)."""
    conversation_id: str = Field(..., max_length=40)


class ThemeMixRequest(BaseModel):
    """Two of the person's themes to mix (core/themes.combine): the first, the second, and which parts come from it."""
    first: str = Field(..., max_length=40)
    second: str = Field(..., max_length=40)
    parts: list[str] = Field(default_factory=list, max_length=8)


class ThemeDesignRequest(BaseModel):
    """A description for MIA to design a theme from (core/theme_design.design): nothing is kept, the Studio previews it."""
    description: str = Field(..., max_length=300)


class WalletCard(BaseModel):
    """A card in the ID wallet, added or changed from its own screen: never an action, so its number never sits in a
    proposal, the history or the undo log (core/id_wallet.py)."""
    kind: Optional[str] = None
    name: Optional[str] = None
    issued_by: Optional[str] = None
    number: Optional[str] = None
    issued: Optional[str] = None
    expires: Optional[str] = None
    notes: Optional[str] = None


class VoiceChoice(BaseModel):
    """MIA's voice from Settings: the voice, the AI voice effect and the volume (percent), each only when changed."""
    voice_id: Optional[str] = None
    effect: Optional[bool] = None
    volume: Optional[int] = None


class PackDelete(BaseModel):
    """Deleting a Knowledge pack: its id, and its title typed to confirm (it's gone for good)."""
    id: str
    confirm: str = ""


class SensorAdd(BaseModel):
    """A sensor added from the Sensors page (core/sensors.py): its name, the app it feeds and its target there."""
    name: str
    app: str
    target: dict = Field(default_factory=dict)


class SensorReading(BaseModel):
    """One reading a sensor sends: the number, and an optional note."""
    value: float | str
    note: str = ""


class BackupMake(BaseModel):
    """A backup made from the web: its passphrase, when it should be encrypted (never kept)."""
    passphrase: str = ""


class PasswordCheck(BaseModel):
    """A password to check against the person's own (before something sensitive)."""
    password: str


class SetupRequest(BaseModel):
    """Making the device's first account from the phone: name, email, password, country and interests."""
    name: str = ""
    email: str = ""
    password: str = ""
    country: str = "US"
    interests: list[str] = []


class PushKeys(BaseModel):
    """A web push subscription's keys (p256dh and auth)."""
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    """A web push subscription: where to send and its keys."""
    endpoint: str
    keys: PushKeys


PHONE_CONVERSATION_IDLE = timedelta(hours=6)


def _idle_too_long(conversation: Conversation, now: Optional[datetime] = None) -> bool:
    """Pure logic. Whether a phone conversation has gone quiet longer than PHONE_CONVERSATION_IDLE (6 hours), so the next message starts a new one; False when its time doesn't read."""
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


# Every response's browser protections (security_headers in create_app; docs/SECURITY.md).
SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data: blob:; media-src 'self' data: blob:; connect-src 'self'; "
                                "font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; "
                                "frame-ancestors 'self'"),
    "X-Frame-Options": "SAMEORIGIN",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(self), microphone=(self), geolocation=(self), payment=(), usb=(), interest-cohort=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def create_app(context: AppContext) -> FastAPI:
    """MIA's web server (FastAPI) for the phone, the glasses and the desktop's web view: sign-in sessions by bearer token (or a linked phone's device key), the access switch that turns away forwarded requests when phone access is off, every /api route (each runs on the signed-in person's own view, view_for), and the web front end served fresh at /web/. Your Data (/api/your-data, export and delete) and the sealed-files recovery key sit beside the security log here; the Theme Studio reads /api/themes and asks /api/themes/design (DEC-0136); MIA paints through /api/art (DEC-0140), Portal Pictures is /api/portals, Look It Up Online is /api/lookup (DEC-0053), Trade Master is /api/trades (DEC-0149), Tracks is /api/tracks (DEC-0099), sensors send their readings to
    /api/sensors/reading with their own key (core/sensors.py), and the phone's autofill asks /api/passwords/autofill
    which logins fit a sign-in (core/password_autofill.py). The Sign-ins page lists the phones linked to this
    computer and unlinks one (/api/security/devices/unlink, core/linked_devices.py); sign out everywhere and a
    password change unlink them all. Requests that read or change stores hold app.state.turn_lock (the context's
    store_lock, a core/store_lock.StoreLock, made here when the context has none); a turn lets it go while the model thinks and keeps its conversation's turns in order
    with that conversation's own lock. Good News Radio's page says when it played an episode
    (/api/news/heard, core/good_news.note_listened)."""
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
    # Sign-in protection (core/sign_in_guard.py, docs/SECURITY.md): slow password guessing, sessions that end.
    from core.sign_in_guard import SignInGuard, session_expired

    app.state.guard = SignInGuard()
    app.state.session_started: dict[str, float] = {}  # sessions signed in from another device, by token
    app.state.warned: set = set()  # accounts already told about repeated wrong passwords (core/security_log.py)
    from core.two_step import StepMemory

    app.state.steps = StepMemory()  # codes already used, never accepted twice (core/two_step.py)
    app.state.two_step_pending: dict[str, str] = {}  # a secret being set up, until its first code is entered

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

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        """The standard browser protections on every response (OWASP secure headers, docs/SECURITY.md): pages run
        only MIA's own scripts and load nothing from other sites (Content-Security-Policy), can't be framed by another
        site, aren't sniffed into another type, send no referrer; the camera, microphone and location only for MIA
        herself; and nothing from /api is cached, since it's the person's own data."""
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    def require_profile_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> str:
        if credentials is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token.")
        token = credentials.credentials
        profile_id = app.state.sessions.get(token)
        if profile_id is not None and session_expired(app.state.session_started.get(token),
                                                      app.state.last_seen.get(token), time.time()):
            _end_session(token)  # unused too long, or too old: sign in again
            _security("session_ended", profile_id)
            profile_id = None
        if profile_id is None:
            profile_id = _linked_device(token)
        if profile_id is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session.")
        app.state.last_seen[token] = time.time()
        return profile_id

    def _end_session(token: str) -> None:
        """Forgets a session: its profile, when it was last used and when it began."""
        app.state.sessions.pop(token, None)
        app.state.last_seen.pop(token, None)
        app.state.session_started.pop(token, None)

    def _new_session(profile_id: str) -> str:
        """A session for a sign-in from another device (it ends: core/sign_in_guard.session_expired)."""
        token = secrets.token_urlsafe(32)
        now = time.time()
        app.state.sessions[token] = profile_id
        app.state.last_seen[token] = now
        app.state.session_started[token] = now
        return token

    def _two_step_secret(profile_id: str) -> str:
        """The account's two-step secret, "" when it's off (or this MIA's accounts don't have two-step)."""
        read = getattr(context.profiles, "two_step_secret", None)
        return read(profile_id) if read is not None else ""

    def _second_step(request: Request, who: str, profile_id: str, code: str) -> None:
        """After a right password: when the account has two-step sign-in on, the authenticator's code. No code asks for
        one (401 with X-MIA-Two-Step: required, not counted as a wrong try); a wrong or used code counts like a wrong
        password."""
        secret = _two_step_secret(profile_id)
        if not secret:
            return
        if not (code or "").strip():
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, TWO_STEP_ASK, headers={"X-MIA-Two-Step": "required"})
        if not app.state.steps.accept(profile_id, secret, code):
            app.state.guard.failed(_guard_keys(request, who))
            _security("sign_in_failed", profile_id, request, "wrong code")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That code isn't right. Try the newest one.",
                                headers={"X-MIA-Two-Step": "required"})

    def _signed_in(profile_id: str, request: Request) -> None:
        """Logs a sign-in, and tells the account's owner when it came from a device it hasn't used before."""
        book = getattr(context, "security_log", None)
        device = _device(request)
        new = book is not None and not book.known_device(profile_id, device)
        _security("sign_in", profile_id, request, "a new device" if new else "")
        if new:
            from core.security_log import alert

            alert(context, profile_id, "New sign-in to MIA",
                  f"Your account signed in from {device}. If this was you, there's nothing to do. If it wasn't, "
                  "change your password: that signs every other device out.")

    def _guard_keys(request: Request, who: str) -> list[str]:
        """What a password try counts against: the account named, and the device it came from (the first forwarded
        address when it came in through Tailscale, else the connection's)."""
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        device = forwarded or (request.client.host if request.client else "")
        return [f"who:{(who or '').strip().lower()}", f"from:{device}"]

    def _device(request: Optional[Request]) -> str:
        """The device a request came from, in words and its address (core/security_log.device_of)."""
        from core.security_log import device_of

        if request is None:
            return ""
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        return device_of(request.headers.get("user-agent", ""), forwarded or (request.client.host if request.client else ""))

    def _security(kind: str, profile_id: Optional[str], request: Optional[Request] = None, detail: str = "") -> dict:
        """Writes one event to the security log (when this MIA has one); never fails the request it's about."""
        book = getattr(context, "security_log", None)
        return book.record(kind, profile_id, _device(request), detail) if book is not None else {}

    def _account_of(who: str) -> Optional[str]:
        """The profile a sign-in name points to, or None (a name that matches no account)."""
        try:
            found = context.profiles.find_for_sign_in(who)
        except Exception:
            found = None
        return found.profile_id if found is not None else None

    def _checked(request: Request, who: str, check) -> bool:
        """Runs a password check under the sign-in guard: refused with 429 while a wait is running, the failure
        counted, a success clearing the account's count. Returns the check's answer."""
        keys = _guard_keys(request, who)
        wait = app.state.guard.wait_left(keys)
        if wait:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                f"Too many wrong passwords. Try again in {wait} seconds.",
                                headers={"Retry-After": str(wait)})
        ok = check()
        if ok:
            app.state.guard.succeeded(keys[:1])
            return True
        app.state.guard.failed(keys)
        log.warning("Sign-in refused for '%s' (wrong password).", (who or "").strip().lower()[:60])
        account = _account_of(who) or (who if who in app.state.sessions.values() else None)
        _security("sign_in_failed", account, request, "" if account else f"name tried: {(who or '')[:24]}")
        if account and app.state.guard.wait_left(keys) and account not in app.state.warned:
            from core.security_log import alert

            app.state.warned.add(account)  # once per run of waits; cleared by the next right password
            _security("waiting", account, request)
            alert(context, account, "Wrong passwords on your MIA account",
                  f"Several wrong passwords were tried for your account from {_device(request)}. MIA is making them wait. "
                  "If this wasn't you, change your password.")
        return False

    def _linked_device(key: str) -> Optional[str]:
        """A phone linked to this computer (DEC-0022, core/home_link.py)
        signs in with its device key, kept here only as a hash, so the
        link outlives a restart until the phone disconnects or is unlinked
        from the Sign-ins page (core/linked_devices.py)."""
        from core import linked_devices

        profile_id = linked_devices.for_key(context.config, key)
        if profile_id:
            from core.phone_link import seen

            seen(profile_id)  # for the phone.link loop: when a linked phone last reached this PC
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
            profile_id = app.state.sessions.get(credentials.credentials)
            _end_session(credentials.credentials)
            if profile_id:
                _security("signed_out", profile_id)
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
        token = _new_session(profile.profile_id)
        _remember(profile.profile_id)
        log.info("First account made on this device: '%s'.", profile.profile_id)
        return {"token": token, "profile_id": profile.profile_id, "name": profile.name, "recovery_code": code}

    @app.post("/api/login")
    def login(body: LoginRequest, request: Request) -> dict:
        # Accepts the person's email (accounts, 2026-10-01), or for
        # profiles made before emails their profile_id or display name
        # (case-insensitive, only when no one else has that name).
        # Guarded (core/sign_in_guard.py): guessing slows down after five wrong tries.
        profile = context.profiles.find_for_sign_in(body.profile_id)
        if not _checked(request, body.profile_id, lambda: profile is not None and
                        context.profiles.verify_password(profile.profile_id, body.password)):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect profile or password.")
        _second_step(request, body.profile_id, profile.profile_id, body.code)
        if not profile.has_password:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Set a password for this profile in MIA's Settings before using MIA remotely.",
            )
        token = _new_session(profile.profile_id)
        _remember(profile.profile_id)
        app.state.warned.discard(profile.profile_id)
        _signed_in(profile.profile_id, request)
        log.info("Mobile login for profile '%s'.", profile.profile_id)
        return {"token": token, "profile_id": profile.profile_id, "name": profile.name}

    # ---------------------------------------------------------------- the home computer's model (DEC-0022)

    @app.post("/api/model/link")
    def model_link(body: LoginRequest, request: Request) -> dict:
        """A phone links to MIA on this computer: the person's own sign-in
        (never a new account), and a device key back for Talk to use."""
        profile = context.profiles.find_for_sign_in(body.profile_id)
        if not _checked(request, body.profile_id, lambda: profile is not None and profile.has_password and
                        context.profiles.verify_password(profile.profile_id, body.password)):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect profile or password.")
        _second_step(request, body.profile_id, profile.profile_id, body.code)
        key = secrets.token_urlsafe(32)
        from core import linked_devices

        devices = dict(context.config.get(linked_devices.KEY, {}) or {})
        devices[linked_devices.key_hash(key)] = {"profile_id": profile.profile_id, "linked": linked_devices.linked_at()}
        context.config.set(linked_devices.KEY, devices)
        context.config.save()
        log.info("A phone linked to this computer for '%s'.", profile.profile_id)
        _security("phone_linked", profile.profile_id, request)
        from core.security_log import alert

        alert(context, profile.profile_id, "A phone linked to MIA",
              f"A phone ({_device(request)}) linked to MIA on this computer with your password. If it wasn't you, unlink "
              "it on the Sign-ins and Security page and change your password.")
        return {"key": key, "profile_id": profile.profile_id, "name": profile.name}

    @app.post("/api/model/unlink")
    def model_unlink(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
        import hashlib

        if credentials is not None:
            devices = dict(context.config.get("home_link.devices", {}) or {})
            if devices.pop(hashlib.sha256(credentials.credentials.encode()).hexdigest(), None) is not None:
                context.config.set("home_link.devices", devices)
                context.config.save()
        return {"unlinked": True}

    @app.post("/api/home_pc/connect")
    def home_pc_connect(body: HomeLinkRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """This phone links to MIA on the home computer (core/home_link.py)."""
        from core.child_accounts import is_child
        from core.home_link import HomeLinkError, connect

        if is_child(view_for(context, profile_id)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Ask a parent to link the home computer.")
        try:
            done = connect(context, body.url, body.who, body.password, body.code)
        except HomeLinkError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        model = f" Talk will use {done['model']} there." if done["model"] else ""
        return {"message": f"Linked to MIA at {done['url']}.{model}" + ("" if done["available"] else
                " Its model isn't running right now; the phone's model answers until it is."), **done}

    @app.post("/api/home_pc/disconnect")
    def home_pc_disconnect(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.home_link import disconnect

        disconnect(context)
        return {"message": "Unlinked. Talk uses this phone's model."}

    @app.get("/api/model/info")
    def model_info(profile_id: str = Depends(require_profile_id)) -> dict:
        llm = context.llm
        backend = getattr(llm, "backend", None)
        from core.model_registry import runtime_info

        return {"available": bool(llm is not None and llm.is_available()),
                "model": getattr(backend, "_model", "") or "",
                # 2026-10-21: what the runtime says about it, for the phone's "what model are you?"
                "details": runtime_info(context)}

    @app.post("/api/model/chat")
    def model_chat(body: ModelChatRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """One model call for a linked phone: its messages and tools in, the
        reply out. The phone's own MIA did everything else (facts, actions)."""
        from core.llm_manager import LLMUnavailableError

        llm = context.llm
        if llm is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "There's no model on this computer.")
        try:
            reply = llm.backend.chat(body.messages, body.tools, timeout=llm._timeout)
        except LLMUnavailableError as problem:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(problem)) from None
        return {"content": reply.content, "tool_calls": [{"name": c.name, "arguments": c.arguments} for c in reply.tool_calls],
                "model": getattr(llm.backend, "_model", "") or ""}

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
    app.state.fresh_talk: set[str] = set()  # "New chat" asked for: the next turn starts one
    from core.store_lock import StoreLock, conversation_lock

    # Held while a request reads or changes stores; a turn lets it go while the model thinks (core/store_lock.py).
    # The desktop's own lock when there is one, so its timers and the server never write at once.
    if getattr(context, "store_lock", None) is None:
        context.store_lock = StoreLock()
    app.state.turn_lock = context.store_lock

    # Two-way sync with the home computer (core/sync.py): a linked device keeps at it in the background.
    def _start_sync() -> None:
        from core.memory_vault import VaultLoop
        from core.sync import SyncLoop

        app.state.sync_loop = SyncLoop(context, app.state.turn_lock)
        app.state.sync_loop.start()
        # The memory vault (core/memory_vault.py): the phone's photos to the PC, when it's switched on.
        app.state.vault_loop = VaultLoop(context, app.state.turn_lock)
        app.state.vault_loop.start()

    def _stop_sync() -> None:
        for name in ("sync_loop", "vault_loop"):
            loop = getattr(app.state, name, None)
            if loop is not None:
                loop.stop()

    app.router.on_startup.append(_start_sync)
    app.router.on_shutdown.append(_stop_sync)

    def conversation_for(profile_id: str, view=None) -> Conversation:
        """2026-09-28: phone conversations are saved with the desktop's
        (the Assistant's History, titled "📱 ..."), so a drive-home chat
        can be picked up at the desk. A new one after PHONE_CONVERSATION_IDLE
        of quiet, like starting a new chat. Without a conversation store
        (tests, headless), kept in memory as before."""
        conversations = app.state.voice_conversations
        current = conversations.get(profile_id)
        manager = getattr(view if view is not None else context, "conversations", None)
        # One MIA everywhere (DEC-0029, ALICE pick 2): the person signed in at
        # the desktop talks in the desktop's own active conversation from the
        # phone and the glasses too, so a chat started at the desk continues
        # in the truck. A fresh one after a reset or hours of quiet.
        desk = context.profiles.get_active_profile() if getattr(context, "profiles", None) is not None else None
        if manager is not None and manager is getattr(context, "conversations", None) and desk is not None \
                and desk.profile_id == profile_id:
            if profile_id in app.state.fresh_talk:
                app.state.fresh_talk.discard(profile_id)
                active = manager.start_new_active_conversation()
            else:
                active = manager.get_or_create_active_conversation()
                if active.messages and _idle_too_long(active):
                    active = manager.start_new_active_conversation()
            conversations[profile_id] = active
            return active
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
        if not text:
            return None
        if context.voice is None or not context.voice.is_tts_available():
            from core.heavy_jobs import can_use_home, speak

            return speak(context, text) if can_use_home(context) else None  # the home computer's voice
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

    def _private_conversation(conversation) -> bool:
        """Whether this conversation is off the record, the private journal, a private turn or a personal mode."""
        from core.life_notes import _private

        return _private(conversation)

    def respond(profile_id: str, transcript: str, background: BackgroundTasks, hearing: Optional[float] = None,
                surface: str = "phone") -> dict:
        # The phone user's own view: their conversations, memories, journal
        # and reasons, whoever is signed in at the desktop (core/personal_data.py).
        view = view_for(context, profile_id)
        conversation = conversation_for(profile_id, view)
        started = time.monotonic()
        drafts = getattr(view, "email_drafts", None)
        # One conversation's turns in order (its own lock), the store lock let go while the model thinks.
        with conversation_lock((profile_id, conversation.conversation_id)), app.state.turn_lock:
            before = drafts.latest() if drafts is not None else None
            turn: AssistantTurn = run_assistant_turn(view, conversation, transcript, surface)
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
        # Her answer as the phone shows and says it (DEC-0067): no "Sure!" first,
        # no "let me know" last. The glasses compose their own from this.
        from core.response_composer import PHONE, compose

        replies = replies[:-1] + [compose(view, replies[-1], PHONE).say]
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
            "used": turn.used,
            "open": turn.open,
            "level": getattr(context.llm, "level", "") if context.llm is not None and turn.llm_available else "",
            # Whether this reply may be offered a second way (DEC-0138): never after the safety floor or a fixed reply,
            # never in a private or personal conversation (the same line Kept draws, core/life_notes._private).
            "comparable": turn.llm_available and turn.route != "fixed" and not _private_conversation(conversation),
        }

    def transcribe_bytes(audio: bytes) -> Optional[str]:
        if context.voice is None or not context.voice.is_stt_available():
            from core.heavy_jobs import can_use_home, transcribe

            return transcribe(context, audio) if can_use_home(context) else None  # heard on the home computer
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
        from core.heavy_jobs import can_use_home

        home = can_use_home(context)
        return {
            "speech_to_text": bool(voice and voice.is_stt_available()) or home,
            "text_to_speech": bool(voice and voice.is_tts_available()) or home,
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
    # The council from the phone (build plan step 16): the same chat as the dev window (core/council.py), for the
    # PC's owner only (the first account): it spends his providers' usage, and it's his development platform.
    def _owner_only(profile_id: str, what: str = "The council") -> None:
        from core.person_settings import _is_first_account

        if not _is_first_account(context, profile_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"{what} is the PC owner's.")

    # MIA's voice (core/web_voice.py), device-wide, so the PC owner's: the voices installed, and changing one.
    @app.get("/api/settings/voice")
    def voice_settings(profile_id: str = Depends(require_profile_id)) -> dict:
        """The voices on this computer and the one speaking now."""
        from core.web_voice import voice_page

        _owner_only(profile_id, "MIA's voice")
        return voice_page(context)

    @app.post("/api/settings/voice")
    def voice_choose(body: VoiceChoice, profile_id: str = Depends(require_profile_id)) -> dict:
        """Changes the voice, its effect or its volume (not an action: the voice engine is swapped in memory)."""
        from core.web_voice import choose

        _owner_only(profile_id, "MIA's voice")
        with app.state.turn_lock:
            done = choose(context, body.voice_id, body.effect, body.volume)
        if "error" in done:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, done["error"])
        return done

    # Backups (core/web_backups.py), for the PC's owner: the newest ones, and Back Up Now (not an action: a passphrase
    # never sits in a proposal or the undo log). Restoring stays on the PC.
    @app.get("/api/backups")
    def backups_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """Where backups go and the newest ones."""
        from core.web_backups import status as backup_status

        _owner_only(profile_id, "Backups")
        return backup_status(context)

    @app.post("/api/backups")
    async def backup_now(body: BackupMake, profile_id: str = Depends(require_profile_id)) -> dict:
        """Makes one backup into the backups folder, encrypted when a passphrase is given."""
        from core.web_backups import make

        _owner_only(profile_id, "Backups")
        if body.passphrase and len(body.passphrase) < 8:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick a passphrase of at least 8 characters, or none.")

        def run():
            with app.state.turn_lock:
                return make(context, body.passphrase)

        done = await run_in_threadpool(run)
        if "error" in done:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, done["error"])
        log.info("Backup made from the web: %s", done["made"])
        return done

    @app.get("/api/diagnostics")
    def diagnostics_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """The PC's check-ups (core/diagnostics.py), for its owner: they read its drives and network adapters."""
        _owner_only(profile_id, "This PC's check-up")
        from core.diagnostics import screen

        return screen(context)

    @app.get("/api/council")
    def council_read(profile_id: str = Depends(require_profile_id)) -> dict:
        _owner_only(profile_id)
        from core import council, council_floor

        shown = ("id", "at", "who", "text", "reply_to", "thread", "kind", "task")
        return {"messages": [{k: m.get(k, "") for k in shown} for m in council.recent(60)],
                "members": [{"name": name, "role": info.get("role", ""), "ready": name in council_floor.ready_members()}
                            for name, info in sorted(council.members().items())]}

    @app.post("/api/council")
    def council_say(body: dict, background: BackgroundTasks, profile_id: str = Depends(require_profile_id)) -> dict:
        """Zac's message to the council, from the phone. Only his messages set it going (DEC-0081), each within its
        own budget, in the background after the reply: a turn can take minutes."""
        _owner_only(profile_id)
        from core import council, council_floor

        text = str(body.get("text", ""))[:4000]
        try:
            message = council.post("zac", text, reply_to=str(body.get("reply_to", ""))[:40],
                                   plan=council_floor.plan(text, sorted(council_floor.ready_members())))
        except council.CouncilError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from problem
        if not council_floor.STOP.match(message["text"]):
            def turn() -> None:
                try:
                    council_floor.run(message)
                except Exception as problem:  # the chat says so rather than going quiet
                    council.post("mia", f"(The council stopped: {problem})", reply_to=message["id"], kind="note",
                                 thread=message.get("thread", ""), turn=message["id"])
            background.add_task(turn)
        return {"id": message["id"], "thread": message["thread"]}

    # Screens for the Operating Journal (DEC-0097), games played (DEC-0098) and Good News Radio (DEC-0096): read
    # here, assembled in core; every change goes through /api/actions like any screen's (DEC-0017).
    # Projects (core/web_projects.py): builds and jobs of the person's own with their money and tasks.
    @app.get("/api/projects")
    def projects_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """The projects for this person's Projects page."""
        from core.web_projects import projects_page

        with app.state.turn_lock:
            return projects_page(view_for(context, profile_id))

    # My Why (core/web_why.py): the person's chains of reasons with the facts behind each; changes are why.* actions.
    @app.get("/api/why")
    def why_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """The why chains for this person's page (reading never records a checkpoint)."""
        from core.web_why import why_page

        with app.state.turn_lock:
            return why_page(view_for(context, profile_id))

    @app.get("/api/operating-journal")
    def operating_journal_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.operating_journal import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    # Knowledge (the offline reference library, core/reference_library_manager.py): packs, search, an article as
    # plain text. Read only; nothing about the person is in it.
    @app.get("/api/knowledge")
    def knowledge_packs(q: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        library = getattr(context, "reference_library", None)
        if library is None:
            return {"available": False, "packs": [], "hits": [], "root": ""}
        with app.state.turn_lock:
            packs = [{"id": p.pack_id, "title": p.title, "description": p.description, "articles": p.article_count}
                     for p in library.list_packs()]
            hits = library.search_titles(q.strip()[:200]) if q.strip() else []
        return {"available": True, "packs": packs, "hits": hits, "root": str(library.root_path)}

    @app.get("/api/knowledge/picture")
    def knowledge_picture(pack: str, path: str, profile_id: str = Depends(require_profile_id)):
        """A picture from an article in a pack (only images: ReferenceLibraryManager.picture)."""
        from fastapi.responses import Response

        library = getattr(context, "reference_library", None)
        with app.state.turn_lock:
            found = library.picture(pack, path) if library is not None else None
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That picture isn't in the library.")
        return Response(found[0], media_type=found[1], headers={"Cache-Control": "private, max-age=86400"})

    @app.post("/api/knowledge/pack/delete")
    def knowledge_pack_delete(body: PackDelete, profile_id: str = Depends(require_profile_id)) -> dict:
        """Deletes a pack's file for good, for the PC's owner, once its title is typed to confirm (as the desktop asks).
        Not an action: undo can't bring a deleted pack back."""
        from core.reference_library_manager import delete_confirmed

        _owner_only(profile_id, "Deleting a pack")
        with app.state.turn_lock:
            passed, message = delete_confirmed(getattr(context, "reference_library", None), body.id, body.confirm)
        if not passed:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, message)
        log.info("Knowledge pack deleted from the web: %s", body.id)
        return {"deleted": body.id, "message": message}

    # MIA's browser (core/web_browser.py, DEC-0117): what it's on, the steps waiting for the person, the taught tasks,
    # and a waiting step's screenshot (only from her own shots folder).
    @app.get("/api/browser")
    def browser_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_browser import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    # A startup sound to hear before choosing it in Settings (core/boot_sound.py, made on asking).
    @app.get("/api/sounds/startup/{sound_id}")
    def startup_sound(sound_id: str, profile_id: str = Depends(require_profile_id)):
        import io
        import wave

        from fastapi.responses import Response

        try:
            from core.boot_sound import startup_samples

            samples, rate = startup_samples(sound_id)
        except (KeyError, ImportError):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "There's no such startup sound here.") from None
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(samples.tobytes())
        return Response(buffer.getvalue(), media_type="audio/wav", headers={"Cache-Control": "no-store"})

    # Start Here (core/web_guide.py): what MIA does and how, what's new, and which of this person's apps are still
    # empty (counted on their own view). Read only.
    # Connect Apps (core/connectors.py): the sources MIA can import from, and a preview of one import before it's
    # approved (the import itself is an action: connect.file, connect.rental_calendar).
    @app.get("/api/connect")
    def connect_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.connectors import connect_page

        with app.state.turn_lock:
            return connect_page(view_for(context, profile_id))

    @app.post("/api/connect/preview")
    def connect_preview(body: dict, profile_id: str = Depends(require_profile_id)) -> dict:
        """What an import would add, before it's approved: a file (name + text) or a rental calendar link (url +
        property). The link is read here (outside the turn lock: a slow site never holds MIA up) and not kept."""
        from core import connectors

        source = str(body.get("source") or "")
        try:
            if source == "rental_calendar":
                place = " ".join(str(body.get("property") or "").split())
                if not place:
                    raise ValueError("Which property is this calendar for?")
                text = str(body.get("text") or "") or connectors.fetch_link(str(body.get("url") or ""))
                with app.state.turn_lock:
                    preview, _new = connectors.rental_preview(view_for(context, profile_id), text, place)
                return {"kind": "rental_calendar", **preview.as_dict(),
                        "sentence": preview.sentence("check-ins and check-outs")}
            if source == "file":
                with app.state.turn_lock:
                    kind, preview = connectors.file_preview(view_for(context, profile_id), str(body.get("name") or ""),
                                                            str(body.get("text") or ""))
                return {"kind": kind, **preview.as_dict(), "sentence": preview.sentence(
                    {"calendar": "calendar events", "contacts": "people", "bank": "transactions"}[kind])}
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a file or a calendar link.")

    @app.get("/api/guide")
    def guide_page(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_guide import guide

        with app.state.turn_lock:
            return guide(view_for(context, profile_id))

    # The live view: frames and the person's own input skip the turn lock, so it stays smooth while MIA thinks (her
    # browser has its own lock).
    @app.get("/api/browser/frame")
    def browser_frame(profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import Response

        from core.web_browser import live_frame

        data = live_frame(view_for(context, profile_id))
        if data is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "MIA's browser isn't open.")
        return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.post("/api/browser/input")
    def browser_input(body: BrowserInputRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.browser import BrowserError
        from core.web_browser import person_input

        try:
            return person_input(view_for(context, profile_id), body.kind, body.x, body.y, body.text, body.key,
                                body.dy)
        except BrowserError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.get("/api/browser/view")
    def browser_view(profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        from core.web_browser import live_view

        with app.state.turn_lock:
            path = live_view(view_for(context, profile_id))
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "MIA's browser isn't open.")
        return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})

    @app.get("/api/browser/shot")
    def browser_shot(id: str, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        from core.web_browser import shot_path

        with app.state.turn_lock:
            path = shot_path(view_for(context, profile_id), id)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That screenshot isn't there.")
        return FileResponse(path, media_type="image/png")

    # The Library's plans shelf (core/plan_library.py): plans, one plan, and a plan's own file from the plans folder.
    @app.get("/api/knowledge/plans")
    def knowledge_plans(q: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.plan_library import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id), q.strip()[:200])

    @app.get("/api/knowledge/plan")
    def knowledge_plan(id: str, sizes: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """One plan, worked out at the sizes asked ("length_ft=10,width_ft=12"; core/plan_library.detail)."""
        from core.plan_library import detail

        asked = dict(part.split("=", 1) for part in sizes.split(",")[:12] if "=" in part)
        with app.state.turn_lock:
            found = detail(view_for(context, profile_id), id, asked)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That plan isn't on the shelf.")
        return found

    @app.get("/api/knowledge/plan/file")
    def knowledge_plan_file(id: str, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        from core.plan_library import file_path

        with app.state.turn_lock:
            path = file_path(view_for(context, profile_id), id)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That file isn't in the plans folder.")
        return FileResponse(path)

    @app.get("/api/knowledge/article")
    def knowledge_article(pack: str, path: str, profile_id: str = Depends(require_profile_id)) -> dict:
        library = getattr(context, "reference_library", None)
        with app.state.turn_lock:
            found = library.article_text(pack, path) if library is not None else None
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That article isn't in the library.")
        return found

    # Maps (core/maps_web.py): the offline basemap tiles, with the waypoints on top. A tile route only touches the
    # tile cache (it may fetch a tile once, by the cache's rules), so it never holds the turn lock.
    @app.get("/api/maps")
    def maps_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.maps_web import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/maps/tile/{source}/{z}/{x}/{y}")
    def maps_tile(source: str, z: int, x: int, y: int, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        from core.maps_web import tile

        found = tile(context, source, z, x, y)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No tile there (offline, or not allowed).")
        return FileResponse(found, media_type="image/png" if found.suffix == ".png" else "image/jpeg",
                            headers={"Cache-Control": "private, max-age=604800"})

    @app.get("/api/maps/vector/{name}")
    def maps_vector(name: str, profile_id: str = Depends(require_profile_id)):
        """A vector map area (core/offline_maps.py), read in byte ranges by the page's PMTiles reader."""
        from fastapi.responses import FileResponse

        from core.offline_maps import path_of

        found = path_of(name)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No map area by that name on this PC.")
        return FileResponse(found, media_type="application/octet-stream")

    @app.get("/api/memories")
    def memories_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.memories_web import screen  # a recap per expedition, and on this day

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/observations")
    def observations_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.observations_web import screen  # what MIA noticed: findings across apps, insights by source

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/navigation")
    def navigation_screen(start: str = "", end: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.navigation_web import screen  # waypoints, a route between two, the sun and moon

        with app.state.turn_lock:
            return screen(view_for(context, profile_id), start[:40], end[:40])

    @app.get("/api/household")
    def household_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.household_routines import screen  # the household's routines; logging one is routine.log

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/classroom")
    def classroom_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.classroom_manager import screen  # the person's own study; changes go through actions

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    # The Classroom's textbooks (core/web_textbooks.py): where the books talk about something, and adding a book (a PDF
    # or text file sent as a raw body with X-Filename, read and indexed by TextbookManager.add_book).
    @app.get("/api/classroom/textbooks/search")
    def textbook_search(q: str = "", book: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """Passages from the person's textbooks that match the words."""
        from core.web_textbooks import search

        with app.state.turn_lock:
            return search(view_for(context, profile_id), q[:200], book)

    @app.post("/api/classroom/textbook")
    async def textbook_upload(request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """Adds a textbook from an uploaded PDF or text file; says why when it can't be read."""
        view = view_for(context, profile_id)
        library = getattr(view, "textbooks", None)
        if library is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Textbooks aren't on this MIA.")
        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file received.")
        if len(data) > 200 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That book is over 200 MB.")
        name = Path(unquote(request.headers.get("x-filename", "book.pdf"))).name.strip() or "book.pdf"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / name
            source.write_bytes(data)
            def add():
                with app.state.turn_lock:
                    return library.add_book(source)

            try:
                book = await run_in_threadpool(add)
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"id": book.book_id, "title": book.title, "reading": book.reading}

    @app.get("/api/life-notes")
    def life_notes_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.life_notes import screen  # promises, decisions, ideas, goals set aside (DEC-0054)

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/directions")
    def directions_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """My Directions (core/web_directions.py, DEC-0141/0143): the person's standing directions, today's seed and one
        thing within reach; changes go through direction.* actions."""
        from core.web_directions import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/power")
    def power_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """Power (core/web_power.py): this device's battery and the energy sources tracked by hand."""
        from core.web_power import power_page

        with app.state.turn_lock:
            return power_page(view_for(context, profile_id))

    @app.get("/api/toolbox")
    def toolbox_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """The Toolbox (core/web_toolbox.py): the calculators, the alarms and the other tools."""
        from core.web_toolbox import toolbox_page

        with app.state.turn_lock:
            return toolbox_page(view_for(context, profile_id))

    @app.get("/api/lab")
    def lab_screen(series: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """The Lab (core/web_lab.py): the Data Logger's series, and one in full with its readings and chart."""
        from core.web_lab import lab_page

        with app.state.turn_lock:
            return lab_page(view_for(context, profile_id), series[:200])

    @app.get("/api/notifications")
    def notifications_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """Notifications (core/web_notifications.py): newest first, each with why MIA sent it when she did on her own."""
        from core.web_notifications import notifications_page

        with app.state.turn_lock:
            return notifications_page(view_for(context, profile_id))

    @app.get("/api/changes")
    def changes_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """Recent Changes (core/web_changes.py): what MIA can put back, and the last fortnight's history."""
        from core.web_changes import changes_page

        with app.state.turn_lock:
            return changes_page(view_for(context, profile_id))

    @app.get("/api/field-kit")
    def field_kit_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """The Field Kit (core/web_field_kit.py): devices plugged in, the network checks and the script library."""
        from core.web_field_kit import field_kit_page

        with app.state.turn_lock:
            return field_kit_page(view_for(context, profile_id))

    @app.get("/api/field-kit/check")
    def field_kit_check(tool: str, value: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """One network check worked out in core (core/web_field_kit.check) on what was typed; nothing is kept."""
        from core.web_field_kit import check

        return check(tool, value[:300])

    @app.get("/api/toolbox/calc")
    def toolbox_calc(request: Request, id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """One calculator worked out in core (core/web_toolbox.calc) from the query's values; nothing is kept."""
        from core.web_toolbox import calc

        values = {k: v[:60] for k, v in request.query_params.items() if k != "id"}
        return calc(id, values)

    @app.get("/api/play")
    def play_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.recreation import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/news")
    def news_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.good_news import screen

        return screen(view_for(context, profile_id))

    @app.post("/api/news/heard")
    def news_heard(body: NewsHeardRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """The radio's page played its episode (web/news.js): counted as heard once a day, so stories listened
        to there count toward the misleading share like ones asked for (core.good_news.note_listened)."""
        from core.good_news import note_listened

        with app.state.turn_lock:
            return {"counted": note_listened(view_for(context, profile_id), body.personality)}

    @app.post("/api/sight")
    async def sight(request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """Sight (core/sight.py, build plan step 15): a photo from the glasses, the phone or the PC, and the question
        about it in the x-question header ("what is this?", "read this label", "inspect this part"). Answered on this
        PC by its local vision model; the photo isn't kept. Never identifies a person."""
        from core.sight import SightError, look

        data = await request.body()
        question = unquote(request.headers.get("x-question", "what is this?"))[:300]
        try:
            return look(view_for(context, profile_id), data, question)
        except SightError as problem:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(problem)) from problem

    @app.get("/api/paths")
    def learning_paths(profile_id: str = Depends(require_profile_id)) -> dict:
        """Learning paths (core/paths.py, DEC-0112): each path this person has started (`paths.path_card`: its stats,
        what's next, its open checks and how each is verified, the stage's checks with their state, the homework),
        and their drafts; this week's homework is made or brought up to date
        first."""
        from core import paths

        view = view_for(context, profile_id)
        book = getattr(view, "paths", None)
        if book is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Learning paths aren't on this MIA.")
        paths.ensure_homework(view)
        out = []
        for path_id in book.started():
            program = paths.program_of(view, path_id)
            if program is not None:
                out.append(paths.path_card(book, program))
        return {"paths": out, "drafts": [{"id": d["id"], "name": d["name"]} for d in book.drafts.values()
                                         if d["id"] not in book.paths]}

    @app.post("/api/paths/{path_id}/verify")
    async def learning_verify(path_id: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """A check its program verifies (core/paths.py, DEC-0112): for guitar, a short WAV recording, the check in the
        x-check header and, for tuning, the string (6 is the low E) in x-string. Worked out on this PC; nothing sent
        is kept."""
        from core import paths

        view = view_for(context, profile_id)
        program = paths.program_of(view, path_id)
        if program is None or getattr(view, "paths", None) is None or view.paths.path(path_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That path isn't started.")
        data = await request.body()
        string = request.headers.get("x-string")
        try:
            return paths.verify(view, program, unquote(request.headers.get("x-check", "")),
                                {"wav": data, "string": int(string) if string and string.isdigit() else None})
        except ValueError as problem:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(problem)) from problem

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
        return {"received": filename, "message": f"Sent {filename} to your inbox. MIA is reading it."}

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
        """The frame's data for every page (core/web_surfaces.shell); a painting that finished meanwhile is taken in
        first (core/art_studio.settle, DEC-0140), so a new backdrop arrives with it."""
        from core.art_studio import settle
        from core.web_surfaces import shell

        with app.state.turn_lock:
            view = view_for(context, profile_id)
            settle(view)
            return shell(view)

    @app.get("/api/apps")
    def web_apps(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_surfaces import apps_page

        with app.state.turn_lock:
            return apps_page(view_for(context, profile_id))

    # The Calendar (Zac, 2026-10-16): everything with a date, by day
    # (core/calendar_view.py). ?month=YYYY-MM picks the month grid.
    @app.get("/api/calendar")
    def web_calendar(month: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.calendar_view import calendar_page

        return _screen(profile_id, "calendar", lambda view: calendar_page(view, month=month or None))

    # The glasses (Zac 2026-10-16, H-0041 Phase 2): app cards and each
    # app's quick action menu (core/glasses.py). Actions still go through
    # /api/actions; a panel line only carries the glasses-safe kinds.
    @app.get("/api/glasses")
    def glasses_cards(mission: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.glasses import glasses_apps

        with app.state.turn_lock:
            return glasses_apps(view_for(context, profile_id), mission_id=mission or None)

    @app.get("/api/glasses/feed")
    def glasses_feed(since: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """The Heads-Up screen: what's new since the glasses last asked (core/glasses_feed.py)."""
        from urllib.parse import quote

        from core.glasses_feed import feed
        from core.home_link import HomeLinkError, home_call, linked

        if linked(context):
            try:
                return home_call(context, "/api/glasses/feed?since=" + quote(since), method="GET", timeout=3)
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        with app.state.turn_lock:
            return feed(view_for(context, profile_id), since or None)

    # Meeting MIA (core/first_boot.py): what's left for this person.
    # Finishing a part goes through /api/actions (firstboot.advance, .skip).
    @app.get("/api/first-boot")
    def first_boot_state(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.first_boot import state

        with app.state.turn_lock:
            return state(view_for(context, profile_id))

    # User Sync (core/user_sync.py): the same conversation on the glasses and
    # the phone, so a phone linked to the home computer uses the computer's.
    @app.get("/api/user-sync")
    def user_sync_state(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.home_link import HomeLinkError, home_call, linked
        from core.user_sync import state

        if linked(context):
            try:
                return home_call(context, "/api/user-sync", method="GET")
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        with app.state.turn_lock:
            return state(view_for(context, profile_id))

    @app.post("/api/user-sync")
    def user_sync_step(body: UserSyncRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.home_link import HomeLinkError, home_call, linked
        from core.user_sync import choose, reply, report, start

        if linked(context):
            try:
                return home_call(context, "/api/user-sync", body.model_dump(), timeout=90)
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        view = view_for(context, profile_id)
        with app.state.turn_lock:
            if body.permissions is not None:
                return report(view, body.permissions)
            if body.choice == "start":
                return start(view)
            return choose(view, body.choice, body.index) if body.choice else reply(view, body.text)

    # What comes after User Sync (core/welcome.py): the first mission and tours.
    @app.get("/api/welcome")
    def welcome_state(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.home_link import HomeLinkError, home_call, linked
        from core.welcome import state

        if linked(context):
            try:
                return home_call(context, "/api/welcome", method="GET")
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        with app.state.turn_lock:
            return state(view_for(context, profile_id))

    @app.post("/api/welcome")
    def welcome_step(body: WelcomeRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.home_link import HomeLinkError, home_call, linked
        from core.welcome import choose

        if linked(context):
            try:
                return home_call(context, "/api/welcome", body.model_dump())
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        with app.state.turn_lock:
            return choose(view_for(context, profile_id), body.choice, body.app)

    # What her orb is doing (core/glasses_feed.py). No turn lock: the orb
    # has to keep answering "thinking" while a turn holds it.
    @app.get("/api/glasses/orb")
    def glasses_orb(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.glasses_feed import orb

        return orb(profile_id)

    @app.post("/api/glasses/orb")
    def glasses_orb_set(body: OrbStateRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """The phone's listening service: what she's doing now. A phone linked to
        the home computer tells it too: that's where the glasses' screen is served from."""
        from core.glasses_feed import set_orb
        from core.home_link import HomeLinkError, home_call, linked

        done = set_orb(profile_id, body.state)
        if done is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No such orb state.")
        if linked(context):
            try:
                home_call(context, "/api/glasses/orb", {"state": body.state}, timeout=3)
            except HomeLinkError:
                pass  # the computer's out of reach: this phone's screen still follows
        return done

    @app.post("/api/glasses/voice")
    def glasses_voice(body: VoiceTextRequest, background: BackgroundTasks,
                      profile_id: str = Depends(require_profile_id)) -> dict:
        """Words heard through the glasses (the phone app listens through
        them: core/glasses_voice.py). A phone linked to the home computer
        sends them there first, where the glasses' screen is served from."""
        from core.glasses_voice import handle
        from core.home_link import HomeLinkError, home_call, linked

        text = body.text.strip()
        if not text:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Say something first.")
        if linked(context):
            try:
                return {**home_call(context, "/api/glasses/voice", {"text": text}, timeout=90), "where": "home_pc"}
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        view = view_for(context, profile_id)

        def sync(words: str) -> Optional[dict]:
            from core import welcome
            from core.user_sync import hear

            with app.state.turn_lock:
                return hear(view, words) or welcome.hear(view, words)

        return {**handle(view, profile_id, text, lambda words: respond(profile_id, words, background, surface="glasses"),
                         sync), "where": "here"}

    @app.get("/api/glasses/{app_id}/{item_id}")
    def glasses_item(app_id: str, item_id: str, mission: str = "",
                     profile_id: str = Depends(require_profile_id)) -> dict:
        from core.glasses import glasses_panel

        with app.state.turn_lock:
            panel = glasses_panel(view_for(context, profile_id), app_id, item_id, mission_id=mission or None)
        if panel is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such menu item.")
        return panel

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

    @app.get("/api/kitchen/recipe/{recipe_id}")
    def web_recipe(recipe_id: str, servings: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """One recipe, opened from its card (core/web_screens.recipe_page); ?servings= scales its amounts."""
        from core.web_screens import recipe_page

        page = _screen(profile_id, "kitchen", lambda view: recipe_page(view, recipe_id, servings=servings or None))
        if not page["available"]:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "There's no recipe like that.")
        return page

    # A recipe's photo (Zac, 2026-10-16): shown on recipe cards and the
    # glasses; sent from the phone as a raw body, like an asset's document.
    @app.get("/api/kitchen/recipe/{recipe_id}/photo")
    def recipe_photo(recipe_id: str, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        view = view_for(context, profile_id)
        kitchen = getattr(view, "kitchen", None)
        path = kitchen.recipe_photo_path(recipe_id) if kitchen is not None else None
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo for that recipe.")
        return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})

    @app.post("/api/kitchen/recipe/{recipe_id}/photo")
    async def recipe_photo_upload(recipe_id: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        view = view_for(context, profile_id)
        kitchen = getattr(view, "kitchen", None)
        recipe = kitchen.get_recipe(recipe_id) if kitchen is not None else None
        if recipe is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such recipe.")
        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No picture received.")
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That picture is over 10 MB.")
        name = Path(unquote(request.headers.get("x-filename", "photo.jpg"))).name.strip() or "photo.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / name
            source.write_bytes(data)
            try:
                with app.state.turn_lock:
                    kitchen.set_recipe_photo(recipe_id, source)
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"{recipe.name} has a photo now."}

    # An asset's photo (2026-11-07, Q-0014): on its page and its Garage card; sent as a raw body like a recipe's.
    @app.get("/api/garage/asset/{asset_id}/photo")
    def asset_photo(asset_id: str, profile_id: str = Depends(require_profile_id)):
        """The asset's photo file (404 when it has none)."""
        from fastapi.responses import FileResponse

        maintenance = getattr(view_for(context, profile_id), "maintenance", None)
        path = maintenance.asset_photo_path(asset_id) if maintenance is not None else None
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo for that.")
        return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})

    @app.post("/api/garage/asset/{asset_id}/photo")
    async def asset_photo_upload(asset_id: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """Sets the asset's photo from the picture sent (JPG, PNG or WebP, up to 10 MB)."""
        maintenance = getattr(view_for(context, profile_id), "maintenance", None)
        asset = maintenance.get_asset(asset_id) if maintenance is not None else None
        if asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "There's nothing like that in the Garage.")
        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No picture received.")
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That picture is over 10 MB.")
        name = Path(unquote(request.headers.get("x-filename", "photo.jpg"))).name.strip() or "photo.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / name
            source.write_bytes(data)
            try:
                with app.state.turn_lock:
                    maintenance.set_asset_photo(asset_id, source)
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"{asset.name} has a photo now."}

    # A property's photo (2026-11-07, Q-0014): on its Real Estate card.
    @app.get("/api/real-estate/property/{property_id}/photo")
    def property_photo(property_id: str, profile_id: str = Depends(require_profile_id)):
        """The property's photo file (404 when it has none)."""
        from fastapi.responses import FileResponse

        estate = getattr(view_for(context, profile_id), "real_estate", None)
        path = estate.property_photo_path(property_id) if estate is not None else None
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo for that.")
        return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})

    @app.post("/api/real-estate/property/{property_id}/photo")
    async def property_photo_upload(property_id: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """Sets the property's photo from the picture sent (JPG, PNG or WebP, up to 10 MB)."""
        estate = getattr(view_for(context, profile_id), "real_estate", None)
        prop = estate.get_property(property_id) if estate is not None else None
        if prop is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "There's no property like that.")
        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No picture received.")
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That picture is over 10 MB.")
        name = Path(unquote(request.headers.get("x-filename", "photo.jpg"))).name.strip() or "photo.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / name
            source.write_bytes(data)
            try:
                with app.state.turn_lock:
                    estate.set_property_photo(property_id, source)
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"{prop.name} has a photo now."}

    # Journal, Workshop, Expeditions, Music and Files (core/web_more.py,
    # Zac, 2026-10-16: on the phone they only opened a chat).
    @app.get("/api/journal")
    def web_journal(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_more import journal_page

        return _screen(profile_id, "notes", journal_page)

    @app.post("/api/journal/captures/check")
    async def web_check_captures(profile_id: str = Depends(require_profile_id)) -> dict:
        """Looks for new MIA Lite recordings and transcribes them (core/web_proposals.check_captures)."""
        from core.web_proposals import check_captures

        view = view_for(context, profile_id)

        def run() -> dict:
            """Checks under the turn lock, off the event loop (transcribing takes a while)."""
            with app.state.turn_lock:
                return check_captures(view)
        return await run_in_threadpool(run)

    @app.get("/api/workshop")
    def web_workshop(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_more import workshop_page

        return _screen(profile_id, "workshop", workshop_page)

    @app.get("/api/grow")
    def web_grow(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_grow import grow_page

        return _screen(profile_id, "greenhouse", grow_page)  # the Greenhouse's growing tabs

    @app.get("/api/homestead/next")
    def web_homestead_next(budget: Optional[float] = None, profile_id: str = Depends(require_profile_id)) -> dict:
        """The Greenhouse's What's Next weighed with a budget (core/development_engine.plan, DEC-0144): advice only."""
        from core.development_engine import plan

        if budget is not None and not (0 <= budget <= 10_000_000):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A budget from 0 up.")
        with app.state.turn_lock:
            return plan(view_for(context, profile_id), budget)

    @app.get("/api/showoff")
    def web_showoff(profile_id: str = Depends(require_profile_id)) -> dict:
        """Show-off mode's tour (DEC-0031): built from a filtered copy of the
        person's data, never money, the journal, memories, health or people."""
        from core.show_off import tour

        return _screen(profile_id, "web_home", tour)

    @app.get("/api/workshop/receipt_match")
    def web_receipt_match(recipe_id: str, receipt: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """Bought It filled from a scanned receipt (core/receipt_match.py)."""
        from core.receipt_match import find, prefill

        def build(view):
            book = getattr(view, "craft_recipes", None)
            recipe = book.get_recipe(recipe_id) if book is not None else None
            found = find(view, receipt)
            if recipe is None or found is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "That recipe or receipt isn't there anymore.")
            return prefill(recipe, found["items"])

        return _screen(profile_id, "workshop", build)

    @app.get("/api/business")
    def web_business(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_business import business_page

        return _screen(profile_id, "business", business_page)

    @app.get("/api/people")
    def web_people(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_more import people_page

        return _screen(profile_id, "relationships", people_page)

    @app.get("/api/expeditions")
    def web_expeditions(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_more import expeditions_page

        return _screen(profile_id, "expeditions", expeditions_page)

    @app.get("/api/music")
    def web_music(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_more import music_page

        return _screen(profile_id, "music", music_page)

    @app.post("/api/music/upload")
    async def web_music_upload(request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """A song from the phone or computer into the music library (core/music_manager.save_upload)."""
        import time as _time

        from core.music_manager import MAX_UPLOAD_BYTES

        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No song received.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That song is over 200 MB.")
        name = unquote(request.headers.get("x-filename", "song.mp3"))

        def save(view):
            music = getattr(view, "music", None)
            if music is None:
                raise ValueError("Music isn't set up on this MIA.")
            path = music.save_upload(name, data)
            music.scan_library(as_of=_time.time() + 60)  # written whole: take it in now
            return path

        try:
            path = _screen(profile_id, "music", save)
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"Added {path.stem} to your library."}

    @app.get("/api/workshop/builds/{job_id}/media")
    def web_build_media(job_id: str, name: str, profile_id: str = Depends(require_profile_id)):
        """One photo or video of a workshop build (core/build_media.py)."""
        from fastapi.responses import FileResponse

        from core.build_media import path_of

        try:
            path = _screen(profile_id, "workshop", lambda view: path_of(view, job_id, name))
        except ValueError as problem:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(problem)) from None
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That isn't there anymore.")
        return FileResponse(path, filename=path.name, headers={"Cache-Control": "private, max-age=86400"})

    @app.post("/api/workshop/builds/{job_id}/media")
    async def web_build_upload(job_id: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.build_media import MAX_BYTES, save

        data = await request.body()
        if len(data) > MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is over 200 MB.")
        name = unquote(request.headers.get("x-filename", "file"))
        tag = request.headers.get("x-tag", "")
        try:
            saved = _screen(profile_id, "workshop", lambda view: save(view, job_id, name, data, tag))
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"Added {saved}."}

    @app.get("/api/expeditions/{expedition_id}/media")
    def web_expedition_media(expedition_id: str, ref: str, profile_id: str = Depends(require_profile_id)):
        """One photo, video or file on an expedition (core/expedition_media.py)."""
        from fastapi.responses import FileResponse

        from core.expedition_media import path_of

        try:
            path = _screen(profile_id, "expeditions", lambda view: path_of(view, expedition_id, ref))
        except ValueError as problem:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(problem)) from None
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That isn't there anymore.")
        return FileResponse(path, filename=path.name, headers={"Cache-Control": "private, max-age=86400"})

    @app.post("/api/expeditions/{expedition_id}/media")
    async def web_expedition_upload(expedition_id: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.expedition_media import MAX_BYTES, save

        data = await request.body()
        if len(data) > MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is over 200 MB.")
        name = unquote(request.headers.get("x-filename", "file"))
        try:
            saved = _screen(profile_id, "expeditions", lambda view: save(view, expedition_id, name, data))
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"Added {saved}."}

    @app.get("/api/music/track/{track_id}/audio")
    def web_music_audio(track_id: str, profile_id: str = Depends(require_profile_id)):
        """One song from the library, to play in the browser."""
        from fastapi.responses import FileResponse

        from core.web_more import track_path

        path = _screen(profile_id, "music", lambda view: track_path(view, track_id))
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That song isn't in the library anymore.")
        return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})

    @app.get("/api/files")
    def web_files(path: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_more import files_page

        return _screen(profile_id, "files", lambda view: files_page(view, path))

    @app.get("/api/files/file")
    def web_file(path: str, profile_id: str = Depends(require_profile_id)):
        """One of the person's own files (core/my_files.py: never outside their folder)."""
        from fastapi.responses import FileResponse

        from core.my_files import MyFiles

        try:
            found = _screen(profile_id, "files", lambda view: MyFiles.for_context(view).file(path))
        except ValueError as problem:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(problem)) from None
        return FileResponse(found, filename=found.name, headers={"Cache-Control": "private, no-cache"})

    @app.post("/api/files/upload")
    async def web_file_upload(request: Request, path: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.my_files import MAX_UPLOAD, MyFiles

        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file received.")
        if len(data) > MAX_UPLOAD:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is over 50 MB.")
        name = unquote(request.headers.get("x-filename", "file"))
        try:
            saved = _screen(profile_id, "files", lambda view: MyFiles.for_context(view).save(path, name, data))
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"Saved {saved.rsplit('/', 1)[-1]}.", "path": saved}

    # The Inbox screen (core/web_inbox.py): what's waiting, and each item's files.
    @app.get("/api/inbox")
    def web_inbox(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_inbox import inbox_page

        return _screen(profile_id, "inbox", inbox_page)

    # The inbox's mailbox from the web (core/inbox_mail.py, DEC-0124): set up, unlock, check. Their own endpoints,
    # not actions: a password and passphrase go only into the encrypted vault, never into a proposal or a log.
    def _mail(profile_id: str, do):
        from core.inbox_mail import MailSetupError

        try:
            return _screen(profile_id, "inbox", do)
        except MailSetupError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.post("/api/inbox/email")
    def web_inbox_email_setup(body: MailSetupRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.inbox_mail import configure

        return _mail(profile_id, lambda view: configure(view, body.host, body.address, body.password,
                                                         body.passphrase, body.everyday))

    @app.post("/api/inbox/email/unlock")
    def web_inbox_email_unlock(body: MailUnlockRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.inbox_mail import unlock

        return _mail(profile_id, lambda view: unlock(view, body.passphrase))

    @app.post("/api/inbox/email/check")
    def web_inbox_email_check(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.inbox_mail import check

        return _mail(profile_id, check)

    @app.get("/api/inbox/item/{item_id}/file")
    def web_inbox_file(item_id: str, name: str, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        from core.web_inbox import item_file

        path = _screen(profile_id, "inbox", lambda view: item_file(view, item_id, name))
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That file isn't in the inbox anymore.")
        return FileResponse(path, filename=path.name, headers={"Cache-Control": "private, no-cache"})

    # The game layer (DEC-0028, core/game_layer.py).
    @app.get("/api/shop")
    def web_shop(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.game_layer import shop_page

        return _screen(profile_id, "reward_shop", shop_page)

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

    # The ID wallet (core/id_wallet.py): the person's own cards. Lists mask the number; one card's own view shows it.
    def wallet_of(profile_id: str):
        """The signed-in person's wallet; 404 without one."""
        wallet = getattr(view_for(context, profile_id), "id_wallet", None)
        if wallet is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "The ID wallet isn't on this MIA.")
        return wallet

    @app.get("/api/wallet")
    def wallet_list(profile_id: str = Depends(require_profile_id)) -> dict:
        """The cards, numbers masked, soonest to expire first, with the kinds and the note on what a copy is."""
        from core.id_wallet import KINDS, LEGAL_NOTE

        with app.state.turn_lock:
            return {"cards": wallet_of(profile_id).listing(), "kinds": list(KINDS), "note": LEGAL_NOTE}

    @app.get("/api/wallet/{card_id}")
    def wallet_card(card_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """One card in full, number included, for its Show view (never cached)."""
        from fastapi.responses import JSONResponse

        with app.state.turn_lock:
            card = wallet_of(profile_id).get(card_id)
        if card is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That card isn't in your wallet.")
        return JSONResponse(card, headers={"Cache-Control": "no-store"})

    @app.post("/api/wallet")
    def wallet_add(body: WalletCard, profile_id: str = Depends(require_profile_id)) -> dict:
        """Adds a card."""
        with app.state.turn_lock:
            try:
                card = wallet_of(profile_id).add(**body.model_dump(exclude_none=True))
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"id": card["id"], "message": f"Added {card['name']} to your wallet."}

    @app.put("/api/wallet/{card_id}")
    def wallet_edit(card_id: str, body: WalletCard, profile_id: str = Depends(require_profile_id)) -> dict:
        """Changes a card's details."""
        with app.state.turn_lock:
            try:
                card = wallet_of(profile_id).update(card_id, **body.model_dump(exclude_none=True))
            except (ValueError, KeyError) as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem).strip("'")) from None
        return {"message": f"Saved {card['name']}."}

    @app.get("/api/wallet/{card_id}/photo/{side}")
    def wallet_photo(card_id: str, side: str, profile_id: str = Depends(require_profile_id)):
        """One side's photo (sealed on disk, opened here; never cached)."""
        from fastapi.responses import Response

        with app.state.turn_lock:
            found = wallet_of(profile_id).photo(card_id, side)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo of that side.")
        return Response(found[0], media_type=found[1], headers={"Cache-Control": "no-store"})

    @app.post("/api/wallet/{card_id}/photo/{side}")
    async def wallet_photo_set(card_id: str, side: str, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """Keeps a photo of one side (JPG, PNG or WebP, up to 10 MB), sealed."""
        data = await request.body()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That picture is over 10 MB.")
        name = Path(unquote(request.headers.get("x-filename", "card.jpg"))).name.strip() or "card.jpg"
        with app.state.turn_lock:
            try:
                wallet_of(profile_id).set_photo(card_id, side, data, name)
            except (ValueError, KeyError) as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem).strip("'")) from None
        return {"message": f"Saved the {side}."}

    @app.get("/api/themes")
    def web_themes(profile_id: str = Depends(require_profile_id)) -> dict:
        """The Theme Studio (core/themes.studio, DEC-0136): every theme with its choices, the one in use, the fonts,
        materials and the room's level ranges. Saving and deleting are actions (core/theme_actions.py)."""
        from core.themes import studio

        with app.state.turn_lock:
            return studio(view_for(context, profile_id))

    @app.get("/api/art")
    def web_art(profile_id: str = Depends(require_profile_id)) -> dict:
        """MIA's paintings for this person (core/art_studio.status, DEC-0140): the image engine, their pictures and
        the paintings still going (finished ones are taken in first)."""
        from core.art_studio import status as art_status

        with app.state.turn_lock:
            return art_status(view_for(context, profile_id))

    @app.post("/api/art/paint")
    def web_art_paint(body: ArtRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """Starts a painting on this PC's graphics card (core/art_studio.start); 400 with her sentence when she won't or
        can't (the words, or the engine isn't running)."""
        from core.art_studio import start

        with app.state.turn_lock:
            try:
                return start(view_for(context, profile_id), body.description, body.use, body.apply, area=body.area)
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.get("/api/portals")
    def web_portals(profile_id: str = Depends(require_profile_id)) -> dict:
        """Portal Pictures (core/portal_pictures.screen, DEC-0140): what each area's portal in the Nexus shows, the
        person's paintings to put there, and the portal paintings still going; choosing is portal.picture."""
        from core.portal_pictures import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/art/{art_id}/image")
    def web_art_image(art_id: str, profile_id: str = Depends(require_profile_id)):
        """One of this person's pictures (404 for anyone else's or one that's gone)."""
        from fastapi.responses import FileResponse

        store = getattr(view_for(context, profile_id), "art", None)
        path = store.path(art_id) if store is not None else None
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No picture like that.")
        return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, max-age=604800"})

    @app.post("/api/themes/design")
    def web_theme_design(body: ThemeDesignRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """MIA designs a theme from a description (core/theme_design.design, DEC-0136): its name, base, choices, what
        she understood and what she couldn't use, plus her one-line summary. Nothing is kept; saving is theme.save."""
        from core.theme_design import design, summary

        result = design(body.description)
        return {**result, "summary": summary(result)}

    @app.get("/api/trades")
    def web_trades(item: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """Trade Master (core/web_trades.screen, DEC-0149): the jobs and diagnoses by trade, one opened (`item`, else
        the one being worked), and the walkthrough; every press is a trade.* action."""
        from core.web_trades import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id), item)

    @app.get("/api/sensors")
    def sensors_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        """Sensors (core/sensors.screen): the person's sensors, what each app needs to name a target, and the picks."""
        from core.sensors import screen as sensors_page

        with app.state.turn_lock:
            return sensors_page(view_for(context, profile_id), profile_id)

    @app.post("/api/sensors")
    def sensor_add(body: SensorAdd, profile_id: str = Depends(require_profile_id)) -> dict:
        """Adds a sensor and returns its key, the only time it's shown (never an action: a key is a secret, and actions
        are logged). The person adding it is its say-so for every reading it sends."""
        from core.sensors import SensorError

        store = getattr(context, "sensors", None)
        if store is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Sensors aren't on this MIA.")
        try:
            with app.state.turn_lock:
                sensor, key = store.add(profile_id, body.name, body.app, body.target)
        except SensorError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"sensor": sensor, "key": key, "path": "/api/sensors/reading", "header": "X-Sensor-Key",
                "body": {"value": 6.8}}

    @app.post("/api/sensors/reading")
    def sensor_reading(body: SensorReading, request: Request) -> dict:
        """A sensor's reading (core/sensors.reading), its key in X-Sensor-Key: logged through its app's reading action
        as the person who added it. The key can do nothing else; turned away from outside when phone access is off,
        like every route."""
        from core.sensors import SensorError, reading

        try:
            with app.state.turn_lock:
                done = reading(context, view_for, request.headers.get("x-sensor-key", ""), body.value, body.note)
        except SensorError as problem:
            code = status.HTTP_403_FORBIDDEN if "key" in str(problem) else (
                status.HTTP_429_TOO_MANY_REQUESTS if "Too soon" in str(problem) else status.HTTP_400_BAD_REQUEST)
            raise HTTPException(code, str(problem)) from None
        return {"ok": True, "value": done["value"]}

    @app.get("/api/tracks")
    def web_tracks(profile_id: str = Depends(require_profile_id)) -> dict:
        """Tracks (core/web_tracks.screen, DEC-0099): the person's walks, rides and drives with their numbers and shapes."""
        from core.web_tracks import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/lookup")
    def web_lookup(profile_id: str = Depends(require_profile_id)) -> dict:
        """Look It Up Online before a search (core/web_lookup.screen, DEC-0053): allowed now or why not, the engine,
        the rules."""
        from core.web_lookup import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.post("/api/lookup")
    def web_lookup_search(body: LookupRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """One online search the person asked for (core/web_lookup.look): only the scrubbed words leave the computer,
        through their own SearXNG. The search runs outside the turn lock (it waits on the network)."""
        from core.web_lookup import look

        return look(view_for(context, profile_id), body.words)

    @app.get("/api/connections")
    def web_connections(profile_id: str = Depends(require_profile_id)) -> dict:
        """Connections (core/web_connections.screen, DEC-0146): the ties MIA is holding, the recent ones, and what she's
        been asked never to raise; changes are connection.* actions."""
        from core.web_connections import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/trail-maps")
    def web_trail_maps(profile_id: str = Depends(require_profile_id)) -> dict:
        """Trail Maps (core/web_trails.screen): the park and trail map PDFs on this MIA, by state."""
        from core.web_trails import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.get("/api/trail-maps/{trail_map_id}/file")
    def web_trail_map_file(trail_map_id: str, profile_id: str = Depends(require_profile_id)):
        """One trail map's PDF, to open in the browser's own viewer."""
        from fastapi.responses import FileResponse

        lib = getattr(context, "trail_maps", None)
        path = lib.file_path(trail_map_id) if lib is not None else None
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That trail map's PDF isn't here.")
        return FileResponse(path, media_type="application/pdf")

    @app.post("/api/trail-maps/upload")
    async def web_trail_map_upload(request: Request, park: str = "", state: str = "", notes: str = "",
                                   profile_id: str = Depends(require_profile_id)) -> dict:
        """A trail map PDF sent from the device (raw body), catalogued; refused when it isn't a PDF or is too big."""
        from core.web_trails import add_upload

        data = await request.body()
        with app.state.turn_lock:
            try:
                return add_upload(view_for(context, profile_id), unquote(park), unquote(state), data, unquote(notes))
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.post("/api/trail-maps/fetch")
    def web_trail_map_fetch(body: TrailLinkRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """A trail map PDF downloaded from a direct link the person gave (outside the turn lock: a slow site never
        holds MIA up), then catalogued."""
        from core.web_trails import add_link

        try:
            return add_link(view_for(context, profile_id), body.park, body.state, body.url, body.notes)
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.get("/api/about")
    def web_about(here: str = "pc", profile_id: str = Depends(require_profile_id)) -> dict:
        """About MIA (core/web_about.screen, DEC-0142): what she is, her scale, her focus, her specialties, how her apps
        are doing on the asking device (`here`: pc, phone or glasses; DEC-0057) and what she knows about the person,
        every line from the facts; read only."""
        from core.web_about import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id), here)

    @app.get("/api/worlds")
    def web_worlds(campaign: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """Living Worlds (core/web_worlds.screen, DEC-0134): the person's fictional worlds, campaigns, character and
        quests, one campaign opened; changes are world.* actions."""
        from core.web_worlds import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id), campaign)

    @app.get("/api/answers")
    def web_answers(profile_id: str = Depends(require_profile_id)) -> dict:
        """How MIA Answers (core/answer_compare.screen, DEC-0138): what she's learned about how the person likes to be
        answered; changes are style.* actions."""
        from core.answer_compare import screen

        with app.state.turn_lock:
            return screen(view_for(context, profile_id))

    @app.post("/api/talk/compare")
    def web_talk_compare(body: CompareRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """Now and then after a reply: the same answer a second way, for the person to pick (DEC-0138). {} when no offer
        fits. The model rephrases outside the turn lock; code checks no fact changed before it's shown."""
        from core.answer_compare import keep, plan, restyle

        view = view_for(context, profile_id)
        with app.state.turn_lock:
            private = body.private or _private_conversation(conversation_for(profile_id, view))
            experiment = plan(view, body.reply, private=private)
        if not experiment or context.llm is None or not context.llm.is_available():
            return {}
        other = restyle(lambda prompt: context.llm.generate(prompt, timeout=45), body.reply,
                        experiment["dimension"], experiment["b"])
        if not other:
            return {}
        with app.state.turn_lock:
            return keep(view, experiment, body.reply, other) or {}

    @app.post("/api/themes/mix")
    def web_theme_mix(body: ThemeMixRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """Mix Two (core/themes.combine, DEC-0136): the first theme with chosen parts of the second, and whether it can
        be kept as it is. Nothing is kept here; saving is theme.save."""
        from core.themes import combine

        with app.state.turn_lock:
            try:
                return combine(view_for(context, profile_id), body.first, body.second, body.parts)
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.get("/api/nexus")
    def web_nexus(profile_id: str = Depends(require_profile_id)) -> dict:
        """The Nexus (core/web_nexus.nexus, DEC-0130): portals with what needs you in each, and the HUD."""
        from core.web_nexus import nexus

        with app.state.turn_lock:
            return nexus(view_for(context, profile_id))

    @app.get("/api/health")
    def web_health(profile_id: str = Depends(require_profile_id)) -> dict:
        """The Health page (core/health_actions.health_page, DEC-0129): the person's own, sealed at rest."""
        from core.health_actions import health_page

        with app.state.turn_lock:
            return health_page(view_for(context, profile_id))

    @app.get("/api/communications")
    def web_communications(profile_id: str = Depends(require_profile_id)) -> dict:
        """The Communications screen (core/web_comms.comms_page, DEC-0129)."""
        from core.web_comms import comms_page

        with app.state.turn_lock:
            return comms_page(view_for(context, profile_id))

    @app.get("/api/hub/{area_id}")
    def web_hub(area_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """One area's hub screen (core/web_areas.hub, DEC-0129)."""
        from core.web_areas import hub

        with app.state.turn_lock:
            found = hub(view_for(context, profile_id), area_id)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "There's no area like that.")
        return found

    @app.get("/api/search")
    def web_search(q: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """Search across the person's records, for the frame's Ctrl+K (core/web_search.py)."""
        from core.web_search import search

        view = view_for(context, profile_id)
        with app.state.turn_lock:
            return search(view, q)

    @app.post("/api/missions/idea")
    async def web_mission_idea(profile_id: str = Depends(require_profile_id)) -> dict:
        """Asks the model for a mission idea (core/web_proposals.suggest); it waits for the person's yes or no."""
        from core.web_proposals import suggest

        view = view_for(context, profile_id)

        def run() -> dict:
            """Suggests under the turn lock, off the event loop (the model can take a while)."""
            with app.state.turn_lock:
                return suggest(view)
        return await run_in_threadpool(run)

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
    def change_password(body: PasswordChange, request: Request, profile_id: str = Depends(require_profile_id),
                        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
        """Not an action: a password never sits in a proposal or the undo log. Guarded like sign-in, and every other
        session of this account ends with the old password (OWASP: a stolen session doesn't outlive the change)."""
        from core.first_account import MIN_PASSWORD

        if not _checked(request, profile_id, lambda: context.profiles.verify_password(profile_id, body.current)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password isn't right.")
        if len(body.new or "") < MIN_PASSWORD:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Pick a password of at least {MIN_PASSWORD} characters.")
        from core.security_log import logged_by_caller

        with app.state.turn_lock, logged_by_caller():  # logged below with the device, not again by the listener
            context.profiles.set_password(profile_id, body.new)
        this = credentials.credentials if credentials is not None else ""
        for token in [t for t, pid in list(app.state.sessions.items()) if pid == profile_id and t != this]:
            _end_session(token)
        from core import linked_devices

        linked_devices.unlink_all(context.config, profile_id)  # a linked phone links again with the new password
        log.info("Password changed from the web for profile '%s'; its other sessions ended and its phones unlinked.",
                 profile_id)
        _security("password_changed", profile_id, request)
        from core.security_log import alert

        alert(context, profile_id, "Your MIA password changed",
              f"Your password was changed from {_device(request)}, and every other device was signed out (linked "
              "phones too). If this "
              "wasn't you, use your recovery code to set a new one.")
        return {"changed": True}

    @app.post("/api/account/recovery-code")
    def new_recovery_code(body: PasswordCheck, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """A new recovery code (the old one stops working), shown once; the password check is guarded like sign-in."""
        if not _checked(request, profile_id, lambda: context.profiles.verify_password(profile_id, body.password)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That password isn't right.")
        with app.state.turn_lock:
            code = context.profiles.issue_recovery_code(profile_id)
        _security("recovery_code", profile_id, request)
        return {"recovery_code": code}

    # The Sign-ins page (core/security_log.py, docs/SECURITY.md step 3): this account's security events, how many
    # devices are signed in, and "sign out everywhere".
    # Two-step sign-in (core/two_step.py): start (the password; a new secret, shown once, not on yet), confirm (a code
    # from the app turns it on), off (the password and a current code).
    @app.post("/api/account/two-step/start")
    def two_step_start(body: TwoStepRequest, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        from core import two_step

        if not _checked(request, profile_id, lambda: context.profiles.verify_password(profile_id, body.password)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That password isn't right.")
        secret = two_step.new_secret()
        app.state.two_step_pending[profile_id] = secret
        profile = context.profiles.get_profile(profile_id)
        account = (getattr(profile, "email", "") or getattr(profile, "name", "") or "you") if profile else "you"
        return {"key": two_step.grouped(secret), "link": two_step.otpauth_uri(secret, account)}

    @app.post("/api/account/two-step/confirm")
    def two_step_confirm(body: TwoStepRequest, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.security_log import alert

        secret = app.state.two_step_pending.get(profile_id, "")
        if not secret:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Start setting it up first.")
        if not app.state.steps.accept(profile_id, secret, body.code):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That code isn't right. Check the key in the app, then try the newest code.")
        with app.state.turn_lock:
            context.profiles.set_two_step(profile_id, secret)
        app.state.two_step_pending.pop(profile_id, None)
        _security("two_step_on", profile_id, request)
        alert(context, profile_id, "Two-step sign-in is on",
              "Signing in from another device now asks for the code from your authenticator app. Lost the phone with "
              "the app? Your recovery code still gets you in.")
        return {"on": True}

    @app.post("/api/account/two-step/off")
    def two_step_off(body: TwoStepRequest, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.security_log import alert

        secret = _two_step_secret(profile_id)
        if not secret:
            return {"on": False}
        if not _checked(request, profile_id, lambda: context.profiles.verify_password(profile_id, body.password)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That password isn't right.")
        if not app.state.steps.accept(profile_id, secret, body.code):
            app.state.guard.failed(_guard_keys(request, profile_id))
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That code isn't right. Try the newest one.")
        with app.state.turn_lock:
            context.profiles.set_two_step(profile_id, None)
        _security("two_step_off", profile_id, request)
        alert(context, profile_id, "Two-step sign-in is off",
              f"Two-step sign-in was turned off from {_device(request)}. If this wasn't you, change your password and turn it back on.")
        return {"on": False}

    @app.get("/api/security/log")
    def security_screen(request: Request, profile_id: str = Depends(require_profile_id),
                        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
        book = getattr(context, "security_log", None)
        this = credentials.credentials if credentials is not None else ""
        others = sum(1 for t, pid in app.state.sessions.items() if pid == profile_id and t != this
                     and t in app.state.session_started)
        from core import at_rest

        from core import linked_devices

        sealed = at_rest.status()
        return {"available": book is not None, "events": book.for_person(profile_id) if book is not None else [],
                "other_sessions": others, "two_step": bool(_two_step_secret(profile_id)),
                "linked_devices": linked_devices.listed(context.config, profile_id),
                "at_rest": {"sealing": sealed["sealing"], "protection": sealed["protection"], "why_not": sealed["why_not"],
                            "files": len(sealed["files"])}, "on_this_pc": _on_this_pc(request)}

    def _on_this_pc(request: Request) -> bool:
        """Whether a request was made on this PC itself: from its own address, not forwarded (Tailscale) from another
        device."""
        host = request.client.host if request.client else ""
        return not request.headers.get("x-forwarded-for") and host in ("127.0.0.1", "::1", "localhost")

    @app.post("/api/security/recovery-key")
    def recovery_key(body: TwoStepRequest, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """The recovery key for MIA's sealed files (DEC-0126, core/at_rest.py), to keep in a password manager: asked
        for with the password, only on this PC itself, and written to the security log."""
        from core import at_rest

        if not _on_this_pc(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "The recovery key is only shown on the computer itself.")
        if not _checked(request, profile_id, lambda: context.profiles.verify_password(profile_id, body.password)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That password isn't right.")
        try:
            key = at_rest.recovery_key()
        except ValueError as problem:
            raise HTTPException(status.HTTP_409_CONFLICT, f"There's no recovery key: {problem}.") from None
        _security("data_key_shown", profile_id, request)
        return {"key": key}

    # Your Data (core/your_data.py, docs/SECURITY.md step 8): what MIA keeps about you and what she read to answer you;
    # export and delete (core/account_data.py), each behind the password.
    @app.get("/api/your-data")
    def your_data_screen(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.your_data import page

        with app.state.turn_lock:
            return page(view_for(context, profile_id), profile_id)

    @app.post("/api/account/export")
    def account_export(body: AccountDataRequest, request: Request, profile_id: str = Depends(require_profile_id)):
        """Everything of yours as one .zip (sealed files as their readable content), after the password."""
        import tempfile

        from fastapi.responses import Response

        from core.account_data import export_account

        if not _checked(request, profile_id, lambda: context.profiles.verify_password(profile_id, body.password)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That password isn't right.")
        with tempfile.TemporaryDirectory(prefix="mia_export_") as folder:
            with app.state.turn_lock:
                path = export_account(context, profile_id, Path(folder) / "MIA-data.zip",
                                      include_household=body.include_household)
            data = path.read_bytes()
        _security("data_exported", profile_id, request, "with the household's files" if body.include_household else "")
        return Response(data, media_type="application/zip", headers={
            "Cache-Control": "no-store", "Content-Disposition": 'attachment; filename="MIA-data.zip"'})

    @app.post("/api/account/delete")
    def account_delete(body: AccountDataRequest, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """Deletes the account (archived, or erased for good) after the password; every session of it ends. Refused
        for the device's only account."""
        from core.account_data import delete_account

        if not _checked(request, profile_id, lambda: context.profiles.verify_password(profile_id, body.password)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That password isn't right.")
        if len(context.profiles.list_profiles()) <= 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "This is the only account on this MIA, so it can't be deleted.")
        with app.state.turn_lock:
            done = delete_account(context, profile_id, body.password, erase=body.erase)
        if not done:
            raise HTTPException(status.HTTP_409_CONFLICT, "The account couldn't be deleted.")
        for token in [t for t, pid in list(app.state.sessions.items()) if pid == profile_id]:
            _end_session(token)
        return {"deleted": True, "erased": body.erase}

    @app.post("/api/security/sign-out-everywhere")
    def sign_out_everywhere(request: Request, profile_id: str = Depends(require_profile_id),
                            credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
        """Ends every other session of this account (this one stays) and unlinks every phone linked for it
        (core/linked_devices.py): a lost phone is one press from harmless."""
        from core import linked_devices

        this = credentials.credentials if credentials is not None else ""
        ended = [t for t, pid in list(app.state.sessions.items()) if pid == profile_id and t != this
                 and t in app.state.session_started]
        for token in ended:
            _end_session(token)
        phones = linked_devices.unlink_all(context.config, profile_id)
        _security("signed_out_everywhere", profile_id, request, f"{len(ended)} other session{'s' if len(ended) != 1 else ''}"
                  + (f", {phones} linked phone{'s' if phones != 1 else ''}" if phones else ""))
        return {"ended": len(ended), "unlinked": phones}

    @app.post("/api/security/devices/unlink")
    def unlink_device(body: dict, request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """Unlinks one of this person's linked phones from the computer (the Sign-ins page): its key stops working."""
        from core import linked_devices

        if not linked_devices.unlink(context.config, profile_id, str((body or {}).get("device", ""))):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No linked phone of yours by that id.")
        _security("phone_unlinked", profile_id, request)
        return {"unlinked": True}

    def _models(profile_id: str):
        from core.child_accounts import ASK_A_PARENT, is_child

        models = getattr(context, "local_models", None)
        if models is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "The model test runs in MIA's phone app.")
        if is_child(view_for(context, profile_id)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, ASK_A_PARENT)
        return models

    @app.get("/api/model-test")
    def model_test(profile_id: str = Depends(require_profile_id)) -> dict:
        """The phone's model test (core/local_model.py, docs/PHONE_MODEL_TEST.md)."""
        return _models(profile_id).status()

    @app.post("/api/model-test/{step}")
    def model_test_step(step: str, body: ModelStep, profile_id: str = Depends(require_profile_id)) -> dict:
        models = _models(profile_id)
        steps = {
            "download": lambda: models.download(body.model),
            "delete": lambda: models.delete(body.model),
            "start": lambda: models.start(body.model),
            "stop": models.stop,
            "run": lambda: models.run_test(body.count or 10),
            "cancel": models.cancel_test,
        }
        if step not in steps:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such step.")
        try:
            steps[step]()
        except ValueError as problem:
            raise HTTPException(status.HTTP_409_CONFLICT, str(problem)) from None
        return models.status()

    @app.get("/api/fitness")
    def web_fitness(profile_id: str = Depends(require_profile_id)) -> dict:
        """Today, the weight line, missions and "is it working?" (core/web_fitness.py, DEC-0020)."""
        from core.web_fitness import fitness_page

        with app.state.turn_lock:
            return fitness_page(view_for(context, profile_id))

    @app.get("/api/fitness/week")
    def web_fitness_week(day: Optional[str] = None, profile_id: str = Depends(require_profile_id)) -> dict:
        """The meal-plan week: meals, prep, shopping list, a suggestion."""
        from core.web_fitness import week_page

        try:
            when = date.fromisoformat(day) if day else None
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dates look like 2026-10-12.") from None
        with app.state.turn_lock:
            return week_page(view_for(context, profile_id), when)

    @app.get("/api/character")
    def web_character(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_progress import character_page

        return _screen(profile_id, "character", character_page)

    # ------------------------------------------------------------ Heavy jobs (core/heavy_jobs.py): a linked phone asks
    # This computer's own engines only: a job sent here never goes anywhere else.
    @app.post("/api/heavy/ocr")
    async def heavy_ocr(request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.heavy_jobs import MAX_UPLOAD
        from core.ocr import IMAGE_SUFFIXES, OcrError, ocr_image, ocr_pdf, tesseract_path

        data = await request.body()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is over 60 MB.")
        name = Path(unquote(request.headers.get("x-filename", "page.jpg"))).name or "page.jpg"
        exe = tesseract_path(context.config)
        if exe is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Tesseract isn't installed on the home computer.")
        language = str(context.config.get("ocr.language", "eng") or "eng")

        def read() -> list[str]:
            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / name
                source.write_bytes(data)
                if source.suffix.lower() in IMAGE_SUFFIXES:
                    return [ocr_image(exe, source, language)]
                return ocr_pdf(exe, source, language)

        try:
            return {"pages": await run_in_threadpool(read)}
        except OcrError as problem:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(problem)) from None

    @app.post("/api/heavy/transcribe")
    async def heavy_transcribe(request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        audio = await request.body()
        if len(audio) > MAX_VOICE_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Recording too long.")
        voice = context.voice
        if voice is None or not voice.is_stt_available():
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Speech-to-text isn't set up on the home computer.")

        def hear() -> Optional[str]:
            with tempfile.TemporaryDirectory() as tmp:
                wav_path = Path(tmp) / "utterance.wav"
                wav_path.write_bytes(audio)
                return voice.transcribe(wav_path)

        return {"text": (await run_in_threadpool(hear)) or ""}

    @app.post("/api/heavy/speak")
    def heavy_speak(body: VoiceTextRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        voice = context.voice
        if voice is None or not voice.is_tts_available() or not body.text.strip():
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "There's no voice on the home computer.")
        with tempfile.TemporaryDirectory() as tmp:
            made = voice.synthesize(body.text.strip()[:2000], Path(tmp) / "say.wav")
            if made is None:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The voice couldn't say that.")
            return {"audio_wav_base64": base64.b64encode(Path(made).read_bytes()).decode("ascii")}

    # ------------------------------------------------------------ Sync (core/sync.py): the PC answers, the phone asks
    def _sync_person(profile_id: str) -> str:
        from core.child_accounts import is_child

        if is_child(view_for(context, profile_id)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sync is for grown-ups' devices for now.")
        return profile_id

    @app.get("/api/sync/manifest")
    def sync_manifest(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.sync import manifest

        with app.state.turn_lock:
            return manifest(context, _sync_person(profile_id))

    @app.get("/api/sync/file")
    def sync_file(scope: str, name: str, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import Response

        from core.sync import path_for

        try:
            path = path_for(context, _sync_person(profile_id), scope, name)
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That file isn't here.")
        from core.at_rest import open_bytes

        with app.state.turn_lock:
            data = open_bytes(path)  # a sealed file goes as its content (DEC-0126); the phone seals its own copy
        return Response(data, media_type="application/octet-stream", headers={"Cache-Control": "no-store"})

    @app.post("/api/sync/file")
    def sync_put(body: SyncFileRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """Take a file from the phone, only if it's still the version the phone saw."""
        import base64
        import binascii

        from core.at_rest import open_bytes
        from core.sync import digest, path_for, write_file

        try:
            path = path_for(context, _sync_person(profile_id), body.scope, body.name)
            data = base64.b64decode(body.data.encode("ascii"), validate=True)
            data.decode("utf-8")
        except (ValueError, binascii.Error, UnicodeDecodeError) as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem) or "That file can't be read.") from None
        with app.state.turn_lock:
            current = open_bytes(path) if path.is_file() else None
            if digest(current) != body.expect:
                raise HTTPException(status.HTTP_409_CONFLICT, "It changed here since; sync again.")
            write_file(context, path, data)
        return {"ok": True}

    def _sync_blob_path(profile_id: str, scope: str, path: str) -> Path:
        from core.sync import file_path_for

        try:
            return file_path_for(context, _sync_person(profile_id), scope, path)
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.get("/api/sync/blob")
    def sync_blob(scope: str, path: str, profile_id: str = Depends(require_profile_id)):
        """A photo or file, streamed (core/sync.py: FILE_FOLDERS)."""
        from fastapi.responses import FileResponse

        here = _sync_blob_path(profile_id, scope, path)
        if not here.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That file isn't here.")
        return FileResponse(here, media_type="application/octet-stream", headers={"Cache-Control": "no-store"})

    @app.put("/api/sync/blob")
    async def sync_blob_put(request: Request, scope: str, path: str, sha: str, expect: str = "",
                            profile_id: str = Depends(require_profile_id)) -> dict:
        """Take a photo or file from the phone: streamed to the side, its
        fingerprint checked, then put in place only if what's here is still
        the version the phone saw."""
        import hashlib
        import os

        from core import live
        from core.sync import FINGERPRINTS, MAX_FILE_BYTES

        here = _sync_blob_path(profile_id, scope, path)
        here.parent.mkdir(parents=True, exist_ok=True)
        tmp = here.with_name(f".{here.name}.{secrets.token_hex(4)}.part")
        h, size = hashlib.sha256(), 0
        try:
            with open(tmp, "wb") as out:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_FILE_BYTES:
                        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is too big to sync.")
                    h.update(chunk)
                    out.write(chunk)
            if h.hexdigest() != sha:
                raise HTTPException(422, "The file arrived damaged; send it again.")
            with app.state.turn_lock:
                current = FINGERPRINTS.of(here) if here.is_file() else ""
                if current != expect:
                    raise HTTPException(status.HTTP_409_CONFLICT, "It changed here since; sync again.")
                os.replace(tmp, here)
        finally:
            if tmp.exists():
                tmp.unlink()
        live.bump()
        return {"ok": True}

    @app.delete("/api/sync/blob")
    def sync_blob_delete(scope: str, path: str, expect: str, profile_id: str = Depends(require_profile_id)) -> dict:
        from core import live
        from core.sync import FINGERPRINTS

        here = _sync_blob_path(profile_id, scope, path)
        with app.state.turn_lock:
            if here.is_file():
                if FINGERPRINTS.of(here) != expect:
                    raise HTTPException(status.HTTP_409_CONFLICT, "It changed here since; sync again.")
                here.unlink()
        live.bump()
        return {"ok": True}

    # ------------------------------------------------------------ Passwords (core/password_vault.py, DEC-0035)
    # Never through the action contract: a password must never sit in an action's record.
    # Every answer is no-store, and only reveal() ever sends a password, one at a time.
    def _vault(profile_id: str):
        vault = _screen(profile_id, "passwords", lambda v: v.passwords)
        if vault is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Passwords aren't set up on this MIA.")
        return vault

    def _vault_answer(body: dict):
        from fastapi.responses import JSONResponse

        return JSONResponse(body, headers={"Cache-Control": "no-store"})

    def _vault_call(profile_id: str, work):
        from core.password_vault import VaultError, VaultLocked

        vault = _vault(profile_id)
        try:
            with app.state.turn_lock:
                return _vault_answer(work(vault) or {})
        except VaultLocked as problem:
            raise HTTPException(423, str(problem)) from None
        except VaultError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.get("/api/passwords")
    def passwords_page(profile_id: str = Depends(require_profile_id)):
        from core.password_vault import vault_page

        return _vault_answer(_screen(profile_id, "passwords", vault_page))

    @app.post("/api/passwords/setup")
    def passwords_setup(body: PasswordVaultRequest, profile_id: str = Depends(require_profile_id)):
        return _vault_call(profile_id, lambda v: {
            "recovery_code": v.setup(body.master),
            "message": "Your vault is made and open. Write the recovery code down now: it's shown once."})

    @app.post("/api/passwords/unlock")
    def passwords_unlock(body: PasswordVaultRequest, profile_id: str = Depends(require_profile_id)):
        def work(v):
            v.unlock(master=body.master, recovery=body.recovery)
            if body.recovery and body.new:
                v.reset_master(body.new)
                return {"message": "Unlocked, with your new master password."}
            return {"message": "Unlocked."}
        return _vault_call(profile_id, work)

    @app.post("/api/passwords/lock")
    def passwords_lock(profile_id: str = Depends(require_profile_id)):
        return _vault_call(profile_id, lambda v: (v.lock(), {"message": "Locked."})[1])

    @app.post("/api/passwords/change")
    def passwords_change(body: PasswordVaultRequest, profile_id: str = Depends(require_profile_id)):
        return _vault_call(profile_id, lambda v: (v.change_master(body.master, body.new),
                                                  {"message": "Your master password is changed."})[1])

    @app.post("/api/passwords/login")
    def passwords_save(body: VaultLoginRequest, profile_id: str = Depends(require_profile_id)):
        def work(v):
            login = v.save(body.title, body.username, body.password, body.url, body.note, body.folder,
                           entry_id=body.entry_id, keep_password=body.keep_password)
            return {"message": f"Saved {login.title}.", "entry_id": login.entry_id}
        return _vault_call(profile_id, work)

    @app.delete("/api/passwords/login/{entry_id}")
    def passwords_delete(entry_id: str, profile_id: str = Depends(require_profile_id)):
        return _vault_call(profile_id, lambda v: (v.delete(entry_id), {"message": "Deleted."})[1])

    @app.get("/api/passwords/autofill")
    def passwords_autofill(domain: str = "", package: str = "", profile_id: str = Depends(require_profile_id)):
        """The logins that fit the boxes the phone's autofill found (core/password_autofill.matches): titles and
        usernames only; 423 while the vault is locked. The password is read only when the person picks one (reveal)."""
        from core.password_autofill import matches

        return _vault_call(profile_id, lambda v: {"matches": matches(v, domain[:200], package[:200])})

    @app.post("/api/passwords/login/{entry_id}/reveal")
    def passwords_reveal(entry_id: str, profile_id: str = Depends(require_profile_id)):
        return _vault_call(profile_id, lambda v: {"password": v.get(entry_id).password})

    @app.post("/api/passwords/import")
    def passwords_import(body: CsvRequest, profile_id: str = Depends(require_profile_id)):
        if len(body.text) > 5_000_000:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is too big.")
        return _vault_call(profile_id, lambda v: {"message": f"Brought in {v.import_csv(body.text)} logins. "
                                                             "Now delete the export file: it isn't encrypted."})

    # ------------------------------------------------------------ Compliance (core/web_compliance.py, DEC-0040)
    @app.get("/api/compliance")
    def web_compliance(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_compliance import compliance_page

        return _screen(profile_id, "compliance", compliance_page)

    # ------------------------------------------------------------ Freedom (core/freedom.py, DEC-0038)
    @app.get("/api/freedom")
    def web_freedom(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.freedom import freedom_page

        return _screen(profile_id, "freedom", freedom_page)

    # ------------------------------------------------------------ The Fix-It Log (core/failure_log.py, DEC-0049)
    @app.get("/api/dev")
    def web_dev(q: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        """The development dashboard (DEC-0068/0070): the device's owner only."""
        from core.work_dashboard import for_person

        found = for_person(view_for(context, profile_id), profile_id, q[:200])
        if found is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only this MIA's owner sees the development work.")
        return found

    # ------------------------------------------------------------ What MIA makes (ACAF, DEC-0088 to DEC-0091)
    @app.get("/api/made")
    def web_made_list(profile_id: str = Depends(require_profile_id)) -> dict:
        """The person's creations: drafts and published, never anyone else's."""
        store = getattr(view_for(context, profile_id), "creations", None)
        items = list(store.items) if store is not None else []
        counts = {}
        for owner in ("household", "personal"):
            sets = getattr(view_for(context, profile_id), "record_sets" if owner == "household" else "my_record_sets", None)
            for rs in (sets.sets if sets is not None else []):
                counts[rs["id"]] = len(rs["records"])
        return {"evaluation": store.evaluation(counts) if store is not None else [], "creations": [{"id": c["id"], "title": c["title"], "status": c["status"], "version": c["version"],
                               "versions": len(c["versions"]), "owner": c["owner"],
                               "icon": c["versions"][-1]["spec"].get("icon", "apps"), "created": c["created"]}
                              for c in items]}

    @app.get("/api/made/{creation_id}")
    def web_made(creation_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """One creation drawn from its spec (core/creation_spec.assemble): the published version,
        or for a draft its latest version, read-only."""
        from core.creation_actions import sets_for
        from core.creation_spec import assemble
        from core.creations import CreationError
        from core.record_sets import RecordError

        view = view_for(context, profile_id)
        store = getattr(view, "creations", None)
        if store is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No creations here.")
        try:
            found = store.get(creation_id)
        except CreationError as problem:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(problem)) from None
        latest, shown = found["versions"][-1], store.shown(creation_id)
        spec = latest["spec"] if found["status"] == "draft" else shown["spec"]
        if found["status"] == "published":
            from datetime import date as _date

            store.opened(creation_id, _date.today().isoformat())
        if spec.get("kind") == "workflow":  # said in plain sentences (core/workflows.py)
            from core.workflows import describe, may

            return {"id": found["id"], "kind": "workflow", "status": found["status"], "version": found["version"],
                    "latest": latest["version"], "pending": latest["version"] != found["version"], "owner": found["owner"],
                    "why": latest["why"], "made_by": latest["made_by"], "blueprint": "a workflow",
                    "rollback": len(found["published_versions"]) > 1, "title": spec["title"], "steps": describe(spec),
                    "may": may(spec), "runs": (found.get("runs") or [])[-10:][::-1]}
        record_set = None
        if spec.get("source"):  # read from her history (core/creation_sources.py), drafts too: it's already theirs
            from core.creation_sources import records, source_of

            record_set = {"records": records(view, source_of(spec).id)}
        elif found["set_id"]:
            try:
                record_set = sets_for(view, found["owner"]).get(found["set_id"])
            except (RecordError, Exception):
                record_set = None
        return {"id": found["id"], "status": found["status"], "version": found["version"],
                "latest": latest["version"], "pending": latest["version"] != found["version"],
                "owner": found["owner"], "why": latest["why"], "made_by": latest["made_by"],
                "blueprint": latest["blueprint"] or "her own layout", "rollback": len(found["published_versions"]) > 1,
                "source": spec.get("source", ""), "screen": assemble(spec, record_set)}

    @app.post("/api/made/{creation_id}/dry")
    def web_made_dry(creation_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """What a workflow would do now, doing none of it."""
        from core.workflows import run

        try:
            return {"lines": run(view_for(context, profile_id), creation_id, dry=True)["lines"]}
        except (ValueError, KeyError) as problem:
            raise HTTPException(status.HTTP_409_CONFLICT, str(problem)) from None

    @app.post("/api/made/import")
    def web_made_import(body: dict, profile_id: str = Depends(require_profile_id)) -> dict:
        """A file (CSV) nobody planned for becomes a draft screen with its rows kept beside it
        (core/record_import.py). Changes no data until it's published."""
        from core.child_accounts import is_child
        from core.record_import import ImportError_, draft

        view = view_for(context, profile_id)
        if is_child(view, profile_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Ask a grown-up to bring in a file.")
        text = str(body.get("csv", ""))
        if len(text) > 2_000_000:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is too big (2 MB at most).")
        try:
            made = draft(view, str(body.get("name", ""))[:60], text)
        except ImportError_ as problem:
            raise HTTPException(status.HTTP_409_CONFLICT, str(problem)) from None
        return {"id": made["id"], "title": made["title"], "status": made["status"]}

    @app.post("/api/made")
    def web_make(body: dict, profile_id: str = Depends(require_profile_id)) -> dict:
        """MIA makes a draft from a need in plain words (core/creation_maker.py). Changes no data:
        the draft is private until the person publishes it."""
        from core.child_accounts import is_child
        from core.creation_maker import MakerError, make

        view = view_for(context, profile_id)
        if is_child(view, profile_id):  # Made by MIA isn't one of the children's apps
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Ask a grown-up to make a new screen.")
        from core.creation_maker import RECURRING, make_workflow

        need = str(body.get("need", ""))[:600]
        try:  # something again and again is a workflow (DEC-0092); anything else, a screen
            made = make_workflow(view, need) if body.get("kind") == "workflow" or (
                body.get("kind") != "screen" and RECURRING.search(need)) else make(view, need)
        except MakerError as problem:
            raise HTTPException(status.HTTP_409_CONFLICT, str(problem)) from None
        return {"id": made["id"], "title": made["title"], "status": made["status"]}

    @app.get("/api/failures")
    def web_failures(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.failure_actions import failures_page

        return _screen(profile_id, "issues", failures_page)

    @app.post("/api/failures/page")
    def web_page_error(body: PageErrorRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """A page that broke reports itself (web/shell.js); never more than a line."""
        from core.failure_actions import page_error

        with app.state.turn_lock:
            page_error(view_for(context, profile_id), body.page, body.message)
        return {"logged": True}

    @app.post("/api/usage/page")
    def web_page_opened(body: PageOpenedRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """A web screen opened (web/shell.js): a count for the page-usage audit, nothing more."""
        tracker = getattr(context, "usage_tracker", None)
        if tracker is not None:
            tracker.record_page(body.page)
        return {"counted": tracker is not None}

    # ------------------------------------------------------------ The Sunday check-in (core/weekly_checkin.py, DEC-0047)
    @app.get("/api/checkin")
    def web_checkin(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.weekly_checkin import checkin

        return _screen(profile_id, "missions", checkin)

    # ------------------------------------------------------------ The Dungeon (core/web_dungeon.py, DEC-0046)
    @app.get("/api/dungeon")
    def web_dungeon(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_dungeon import dungeon_page

        return _screen(profile_id, "dungeon", dungeon_page)

    # ------------------------------------------------------------ Chickens (core/web_flock.py, DEC-0037)
    @app.get("/api/flock")
    def web_flock(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.web_flock import flock_page

        return _screen(profile_id, "flock", flock_page)

    # ------------------------------------------------------------ Insurance check-up (core/insurance.py, DEC-0034)
    @app.get("/api/insurance")
    def web_insurance(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.insurance import insurance_page

        return _screen(profile_id, "insurance", insurance_page)

    @app.post("/api/insurance/read")
    async def insurance_read(request: Request, profile_id: str = Depends(require_profile_id)) -> dict:
        """A policy's PDF or a photo of its declarations page: what it says, for
        the Add form (the person checks it; nothing is saved here)."""
        from core.document_text import extract
        from core.insurance import read_policy

        _screen(profile_id, "insurance", lambda v: None)
        data = await request.body()
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file received.")
        if len(data) > MAX_DOCUMENT_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That file is over 25 MB.")
        name = Path(unquote(request.headers.get("x-filename", "policy.pdf"))).name.strip() or "policy.pdf"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_bytes(data)
            doc = await run_in_threadpool(extract, path)
            text = doc.text if doc.readable else ""
            if not text and doc.needs_ocr:
                text = await run_in_threadpool(_ocr_text, path)
        if not text.strip():
            raise HTTPException(422, "MIA couldn't read any text in that. Type the policy in instead.")
        found = read_policy(text)
        return {"values": found, "message": f"Read {len(found)} things from {name}. Check them before you save."
                if found else "MIA read it but found no policy details. Type them in instead."}

    def _ocr_text(path: Path) -> str:
        """A photo or scan: Tesseract here, else the home computer (core/heavy_jobs.py)."""
        from core.ocr import OcrError, ocr_image, ocr_pdf, tesseract_path

        exe = tesseract_path(context.config)
        try:
            if exe:
                if path.suffix.lower() == ".pdf":
                    return "\n".join(ocr_pdf(exe, path))
                return ocr_image(exe, path)
            from core.heavy_jobs import can_use_home, read_document

            return "\n".join(read_document(context, path)) if can_use_home(context) else ""
        except (OcrError, OSError, ValueError, ImportError):  # ImportError: no PDF renderer on the phone
            return ""

    # ------------------------------------------------------------ Memory vault (core/memory_vault.py)
    # The phone's own screen:
    @app.get("/api/vault")
    def web_vault(month: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.memory_vault import vault_page

        return _screen(profile_id, "vault", lambda view: vault_page(view, month))

    @app.get("/api/vault/photo/{sha}")
    def vault_photo(sha: str, full: int = 0, profile_id: str = Depends(require_profile_id)):
        """A photo from the vault, small (full=0) or as it is: from this phone
        when it's still here, else from the home computer."""
        from fastapi.responses import FileResponse, Response

        from core.home_link import HomeLinkError, home_call
        from core.memory_vault import _clean_sha, thumbnail

        view = view_for(context, profile_id)
        vault = _screen(profile_id, "vault", lambda v: v.memory_vault)
        try:
            sha = _clean_sha(sha)
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        item = vault.items.get(sha) if vault is not None else None
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That photo isn't in your vault.")
        here = vault.file_of(sha)
        if here is not None:
            if full or item.get("kind") != "photo":
                return FileResponse(here, headers={"Cache-Control": "no-store"})
            data, kind = thumbnail(here)
            return Response(data, media_type=kind, headers={"Cache-Control": "no-store"})
        try:
            data = home_call(view, f"/api/vault/blob/{sha}?thumb={0 if full else 1}", timeout=60, raw=True)
        except HomeLinkError as problem:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"It's on the home computer: {problem}") from None
        return Response(data, media_type="image/jpeg" if not full else "application/octet-stream",
                        headers={"Cache-Control": "no-store"})

    @app.post("/api/vault/free/plan")
    def vault_free_plan(body: VaultFreeRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """Exactly what Android will be asked to move to its Trash, after the
        home computer has read each of those files again, now."""
        from core.home_link import HomeLinkError
        from core.memory_vault import free_plan

        view = view_for(context, profile_id)
        vault = _screen(profile_id, "vault", lambda v: v.memory_vault)
        try:
            return free_plan(view, vault, body.what)
        except (HomeLinkError, ValueError) as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.post("/api/vault/free/done")
    def vault_free_done(body: VaultFreeRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.memory_vault import _size, note_freed

        view = view_for(context, profile_id)
        vault = _screen(profile_id, "vault", lambda v: v.memory_vault)
        done = note_freed(view, vault, body.paths, lock=app.state.turn_lock)
        where = "One copy of each stays on the phone." if body.what == "copies" else "They're safe on the home computer."
        return {**done, "message": f"Freed {_size(done['bytes'])} on this phone. {where}" if done["count"]
                else "Nothing was removed."}

    @app.post("/api/vault/now")
    def vault_now(profile_id: str = Depends(require_profile_id)) -> dict:
        _screen(profile_id, "vault", lambda v: None)
        loop = getattr(app.state, "vault_loop", None)
        if loop is not None:
            loop.poke()
        return {"message": "Looking for new photos and copying them now."}

    # The home computer's side (the phone asks with its link key):
    def _shelf(profile_id: str):
        from core.memory_vault import shelf_for

        return shelf_for(context, _sync_person(profile_id))

    @app.post("/api/vault/have")
    def vault_have(body: VaultShasRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        try:
            return {"have": _shelf(profile_id).have(body.shas)}
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.put("/api/vault/blob/{sha}")
    async def vault_blob_put(sha: str, request: Request, offset: int = 0, size: int = 0, name: str = "",
                             taken_at: str = "", kind: str = "", profile_id: str = Depends(require_profile_id)) -> dict:
        from core.memory_vault import CHUNK_BYTES

        data = await request.body()
        if len(data) > CHUNK_BYTES * 2:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Send it in smaller pieces.")
        try:
            return _shelf(profile_id).receive(sha, offset, data, size, name, taken_at, kind)
        except ValueError as problem:
            raise HTTPException(422, str(problem)) from None

    @app.get("/api/vault/blob/{sha}")
    def vault_blob(sha: str, thumb: int = 0, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse, Response

        from core.memory_vault import _clean_sha, thumbnail

        try:
            path = _shelf(profile_id).path_of(_clean_sha(sha))
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That photo isn't on this computer.")
        if thumb:
            data, kind = thumbnail(path)
            return Response(data, media_type=kind, headers={"Cache-Control": "no-store"})
        return FileResponse(path, headers={"Cache-Control": "no-store"})

    @app.post("/api/vault/verify")
    def vault_verify(body: VaultShasRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        try:
            return {"ok": _shelf(profile_id).verify(body.shas)}
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.post("/api/vault/scores")
    def vault_scores(body: VaultShasRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        try:
            return {"scores": _shelf(profile_id).scores(body.shas)}
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.post("/api/vault/hashes")
    def vault_hashes(body: VaultShasRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        try:  # how each photo looks, so near-duplicates are offered like bursts (core/memory_vault.py)
            return {"hashes": _shelf(profile_id).hashes(body.shas)}
        except ValueError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.post("/api/sync/game")
    def sync_game(values: dict, profile_id: str = Depends(require_profile_id)) -> dict:
        from core.sync import set_game_numbers

        with app.state.turn_lock:
            set_game_numbers(context, _sync_person(profile_id), values)
        return {"ok": True}

    @app.get("/api/sync/status")
    def sync_status(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.sync import status as sync_state

        return sync_state(context)

    @app.post("/api/sync/now")
    def sync_now_endpoint(profile_id: str = Depends(require_profile_id)) -> dict:
        """The phone: sync with the linked home computer right now."""
        from core.home_link import HomeLinkError
        from core.sync import state_for, sync_now

        _sync_person(profile_id)
        try:
            done = sync_now(context, lock=app.state.turn_lock)
        except (HomeLinkError, ValueError, OSError) as problem:
            state_for(context).set_status(problem=str(problem))
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(problem)) from None
        changed = done["pushed"] + done["pulled"] + done["merged"]
        said = ("Up to date with the home computer." if not changed else
                f"Synced: {done['pulled']} from the computer, {done['pushed']} to it, {done['merged']} merged.")
        return {"message": f"{said} {done['note']}".strip(), **done}

    # ------------------------------------------------------------ Security (DEC-0033, core/security_cams.py)
    @app.get("/api/security")
    def web_security(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.security_cams import security_page

        return _screen(profile_id, "security", security_page)

    def _security_book(profile_id: str):
        from core.child_accounts import ASK_A_PARENT, app_allowed

        view = view_for(context, profile_id)
        if not app_allowed(view, "security"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, ASK_A_PARENT)
        book = getattr(view, "security", None)
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Security isn't set up on this MIA.")
        return book

    @app.post("/api/security/camera")
    def web_security_camera(body: CameraRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """Add or change a camera with its login (the password never goes
        through an action's record, and never comes back to a screen)."""
        from core.security_cams import CameraError

        book = _security_book(profile_id)
        if body.on_pc or (body.camera_id or "").startswith("pc-"):  # the camera lives on the home computer
            from core.home_link import HomeLinkError, home_call

            payload = body.model_dump(exclude={"on_pc"})
            payload["camera_id"] = (body.camera_id or "").removeprefix("pc-") or None
            try:
                return home_call(view_for(context, profile_id), "/api/security/camera", payload, timeout=15)
            except HomeLinkError as problem:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(problem)) from None
        try:
            with app.state.turn_lock:
                cam = book.save_camera(body.camera_id, body.name, body.location, body.brand, body.host, body.path,
                                       body.user, body.password)
        except CameraError as problem:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None
        return {"message": f"{cam.name} is saved.", "camera_id": cam.camera_id}

    @app.delete("/api/security/camera/{camera_id}")
    def web_security_camera_remove(camera_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """Remove a camera here (a linked phone asking this computer)."""
        book = _security_book(profile_id)
        cam = book.get(camera_id)
        if cam is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That camera isn't set up anymore.")
        with app.state.turn_lock:
            book.remove(camera_id)
        return {"message": f"Removed {cam.name}."}

    @app.get("/api/security/cameras/{camera_id}/frame")
    def web_security_frame(camera_id: str, profile_id: str = Depends(require_profile_id)):
        """The camera's picture now (outside the turn lock: a slow camera never holds MIA up)."""
        from fastapi.responses import Response

        from core.security_cams import CameraError

        book = _security_book(profile_id)
        try:
            data = book.frame(camera_id)
        except CameraError as problem:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(problem)) from None
        return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/security/pictures/{name}")
    def web_security_picture(name: str, profile_id: str = Depends(require_profile_id)):
        from fastapi.responses import FileResponse

        from core.security_cams import CameraError

        book = _security_book(profile_id)
        try:
            path = book.picture_path(name)
        except CameraError as problem:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(problem)) from None
        return FileResponse(path, filename=path.name, headers={"Cache-Control": "private, max-age=86400"})

    @app.get("/api/places")
    def web_places(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.places import places_page

        return _screen(profile_id, "expeditions", places_page)

    @app.get("/api/party")
    def web_party(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.party import party_page

        return _screen(profile_id, "missions", party_page)

    @app.get("/api/worldmap")
    def web_worldmap(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.world_map import world_page

        return _screen(profile_id, "expeditions", world_page)

    @app.get("/api/chronicle")
    def web_chronicle(profile_id: str = Depends(require_profile_id)) -> dict:
        from core.chronicle import chronicle_page

        return _screen(profile_id, "character", chronicle_page)

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
        app.state.fresh_talk.add(profile_id)
        return {"reset": True}

    @app.get("/api/talk/conversations")
    def talk_conversations(profile_id: str = Depends(require_profile_id)) -> dict:
        """The person's past conversations with MIA, newest first (core/web_conversations.history), and which one Talk
        is in now."""
        from core.web_conversations import history

        with app.state.turn_lock:
            view = view_for(context, profile_id)
            current = app.state.voice_conversations.get(profile_id)
            return history(view, current.conversation_id if current is not None else "")

    @app.get("/api/talk/conversations/{conversation_id}")
    def talk_conversation(conversation_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """One past conversation to read (only what was kept: never private or off-the-record messages)."""
        from core.web_conversations import one

        with app.state.turn_lock:
            found = one(view_for(context, profile_id), conversation_id)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That conversation isn't here.")
        return found

    def talk_conversation_named(view, profile_id: str, conversation_id: str) -> Conversation:
        """The conversation an id names in the person's own store (`current`: the one Talk is in); 404 when it
        isn't there. Call it holding the turn lock."""
        if conversation_id == "current":
            return app.state.voice_conversations.get(profile_id) or conversation_for(profile_id, view)
        manager = getattr(view, "conversations", None)
        found = manager.get_conversation(conversation_id) if manager is not None else None
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That conversation isn't here.")
        return found

    @app.get("/api/talk/conversations/{conversation_id}/export")
    def talk_export(conversation_id: str, form: str = "markdown", profile_id: str = Depends(require_profile_id)) -> dict:
        """One conversation as text, Markdown or JSON, for the chat page's Copy (saving it to Files is the action
        `conversation.export`). Only what was kept. A phone linked to the home computer reads the computer's
        current conversation: that's where its words went."""
        from core.conversation_export import export_of
        from core.home_link import HomeLinkError, home_call, linked

        if conversation_id == "current" and linked(context):
            try:
                return home_call(context, f"/api/talk/conversations/current/export?form={quote(form)}", method="GET")
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        with app.state.turn_lock:
            found = talk_conversation_named(view_for(context, profile_id), profile_id, conversation_id)
            try:
                return export_of(found, form)
            except ValueError as problem:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(problem)) from None

    @app.post("/api/talk/conversations/{conversation_id}/summary")
    def talk_summary(conversation_id: str, profile_id: str = Depends(require_profile_id)) -> dict:
        """A summary of one whole conversation (core/conversation_export.summary_of): what was talked about,
        decided, left open and to do. The conversation is found under the turn lock; the model reads it outside
        the lock, so Talk isn't held up while it writes."""
        from core.conversation_export import summary_of
        from core.home_link import HomeLinkError, home_call, linked

        if conversation_id == "current" and linked(context):
            try:
                return home_call(context, "/api/talk/conversations/current/summary", payload={}, timeout=240.0,
                                 method="POST")
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        with app.state.turn_lock:
            view = view_for(context, profile_id)
            found = talk_conversation_named(view, profile_id, conversation_id)
        return summary_of(view, found)

    @app.post("/api/talk/continue")
    def talk_continue(body: ContinueRequest, profile_id: str = Depends(require_profile_id)) -> dict:
        """Talk picks a past conversation back up: the next turn, here or on the phone, continues it."""
        from core.web_conversations import pick_up

        with app.state.turn_lock:
            view = view_for(context, profile_id)
            try:
                picked = pick_up(view, body.conversation_id)
            except ValueError as problem:
                raise HTTPException(status.HTTP_404_NOT_FOUND, str(problem)) from None
            manager = getattr(view, "conversations", None)
            if manager is not None and manager is getattr(context, "conversations", None):
                manager.set_active_conversation_id(picked.conversation_id)  # the desk's own active one, too
            app.state.fresh_talk.discard(profile_id)
            app.state.voice_conversations[profile_id] = picked
        return {"conversation_id": picked.conversation_id, "title": picked.title}

    @app.get("/api/talk/thread")
    def talk_thread(limit: int = 20, earlier: bool = False, profile_id: str = Depends(require_profile_id)) -> dict:
        """The conversation Talk continues (DEC-0029): its recent messages,
        so the phone, the web and the glasses show the same thread. Off-
        the-record messages are never kept, so never shown. `earlier` is the
        glasses' log, which goes back through past conversations too, since
        a new one starts after hours of quiet. A phone linked to the home computer reads the
        computer's: that's where its words went."""
        from core.home_link import HomeLinkError, home_call, linked

        limit = max(1, min(limit, 200))
        if linked(context):
            try:
                return home_call(context, f"/api/talk/thread?limit={limit}&earlier={int(earlier)}", method="GET")
            except HomeLinkError:
                pass  # the computer's out of reach: this phone answers
        with app.state.turn_lock:
            view = view_for(context, profile_id)
            conversation = conversation_for(profile_id, view)
            manager = getattr(view, "conversations", None)
            past = [c for c in (manager.all_conversations() if earlier and manager is not None else [])
                    if c.conversation_id != conversation.conversation_id]
            past.sort(key=lambda c: c.messages[-1].timestamp if c.messages else "")
            shown = [m for c in past + [conversation] for m in c.messages if not getattr(m, "privacy", "")]
            messages = [{"role": m.role, "content": m.content} for m in shown][-limit:]
            return {"conversation_id": conversation.conversation_id, "title": conversation.title, "messages": messages}

    # The web front end (web/, DEC-0012) and the schemas it's built on.
    # Mounted before "/" so the phone app keeps the root.
    if _WEB_DIR.is_dir():
        app.mount("/web", _Fresh(directory=_WEB_DIR, html=True), name="web")
    if _SCHEMA_DIR.is_dir():  # the preview's examples; MIA on a phone ships without them (DEC-0019)
        app.mount("/schema", StaticFiles(directory=_SCHEMA_DIR), name="schema")
    app.mount("/", _Fresh(directory=_STATIC_DIR, html=True), name="static")
    return app
