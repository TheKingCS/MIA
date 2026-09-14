"""
core.push_subscription_manager
=================================

Persists the Web Push subscriptions a profile's browser/PWA has
registered — the endpoint URL + keys `PushManager.subscribe()` returns,
per the standard Web Push API. One profile can have more than one
subscription (a phone and a laptop, say), so this is a list keyed by
profile_id, not a single field on Profile.

Same dataclass + manager + JSON-file shape as every other manager in
this codebase (see core/notification_manager.py). Persisted to
data/push_subscriptions.json — deliberately its own file rather than a
new Profile field, since a subscription is a browser/device credential,
not a fact about the person.

Actually sending a push through a stored subscription is
core/web_push.py's job, not this one — this manager only owns the
CRUD/persistence, matching the existing "manager owns storage,
behavior lives beside it" split (e.g. core/mission_manager.py vs.
core/mission_rewards.py-style helpers elsewhere in this codebase).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SUBSCRIPTIONS_FILE = _DATA_DIR / "push_subscriptions.json"


@dataclass
class PushSubscription:
    profile_id: str
    endpoint: str
    p256dh_key: str
    auth_key: str
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "endpoint": self.endpoint,
            "p256dh_key": self.p256dh_key,
            "auth_key": self.auth_key,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PushSubscription":
        return PushSubscription(
            profile_id=data.get("profile_id", ""),
            endpoint=data.get("endpoint", ""),
            p256dh_key=data.get("p256dh_key", ""),
            auth_key=data.get("auth_key", ""),
            created_at=data.get("created_at", ""),
        )

    def as_webpush_subscription_info(self) -> dict:
        """The shape pywebpush.webpush()'s `subscription_info` argument expects."""
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh_key, "auth": self.auth_key},
        }


class PushSubscriptionManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._subscriptions: list[PushSubscription] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _SUBSCRIPTIONS_FILE.exists():
            self._subscriptions = []
            return
        try:
            raw = json.loads(_SUBSCRIPTIONS_FILE.read_text(encoding="utf-8"))
            self._subscriptions = [PushSubscription.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load push_subscriptions.json — starting with an empty list.")
            self._subscriptions = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_SUBSCRIPTIONS_FILE,
            json.dumps([s.to_dict() for s in self._subscriptions], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_subscription(self, profile_id: str, endpoint: str, p256dh_key: str, auth_key: str) -> PushSubscription:
        """Registers a new subscription, or replaces an existing one for
        the same endpoint (a browser re-subscribing after key rotation
        reuses the same endpoint in practice, but this stays correct
        either way)."""
        self._subscriptions = [s for s in self._subscriptions if s.endpoint != endpoint]
        subscription = PushSubscription(
            profile_id=profile_id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._subscriptions.append(subscription)
        self._save()
        log.info("Push subscription registered for profile '%s'.", profile_id)
        return subscription

    def remove_subscription(self, endpoint: str) -> None:
        self._subscriptions = [s for s in self._subscriptions if s.endpoint != endpoint]
        self._save()

    def subscriptions_for_profile(self, profile_id: str) -> list[PushSubscription]:
        return [s for s in self._subscriptions if s.profile_id == profile_id]

    def all_subscriptions(self) -> list[PushSubscription]:
        return list(self._subscriptions)
