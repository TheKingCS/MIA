"""
core.web_push
===============

Sends Web Push messages via pywebpush (VAPID-signed, per the standard
Web Push protocol) and owns this device's VAPID keypair — generated
once on first use and persisted to data/vapid_keys.json, never
regenerated after that (regenerating it would silently invalidate every
subscription a browser has already registered against the old key).

data/vapid_keys.json holds a real secret (the VAPID private key), same
"runtime state, not committed" treatment as every other file under
data/ — but note what this secret's blast radius actually is: it can
only ever be used to send push messages to this app's own subscribers
(server/app.py's /api/push/* routes), never to read any of the user's
data, so it doesn't need cryptography_manager.py-grade handling.

Delivery failure is expected, routine behavior (a phone that's been
off for weeks, a subscription the browser silently dropped) — not
something to raise on. send_web_push() returns False and logs, mirroring
core/llm_manager.py's own stance on an unreachable external service. A
permanently dead subscription (the push service's 404/410 "gone"
response) is removed via PushSubscriptionManager so it doesn't keep
being retried forever.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02, b64urlencode
from pywebpush import WebPushException, webpush

from core.logger import get_logger
from core.push_subscription_manager import PushSubscription, PushSubscriptionManager

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_VAPID_KEYS_FILE = _DATA_DIR / "vapid_keys.json"

# Contact info the push services (Google/Mozilla/Apple) require in the
# VAPID "sub" claim — a mailto: or https: URL they can reach if this
# app's traffic ever needs investigating. No real inbox is needed for a
# personal single-user deployment; this is the protocol's own required
# field, not a real support channel.
_VAPID_CLAIM_SUB = "mailto:mia-webpush@localhost"

_DEAD_SUBSCRIPTION_STATUS_CODES = (404, 410)


def get_or_create_vapid_keys() -> tuple[str, str]:
    """Returns (private_key_der_b64, public_key_b64) for this device,
    generating and persisting a new keypair on first call.

    The private key is stored/returned as base64url-encoded DER
    (PKCS8), not PEM — confirmed directly against py_vapid's own
    Vapid.from_string() (what pywebpush.webpush() calls internally on
    a str vapid_private_key): it b64url-decodes the whole string and
    feeds it straight to load_der_private_key(), so a PEM string (with
    "-----BEGIN..." header lines) fails to parse. This bit me once
    already in this feature's own manual end-to-end verification —
    not a hypothetical concern."""
    if _VAPID_KEYS_FILE.exists():
        try:
            raw = json.loads(_VAPID_KEYS_FILE.read_text(encoding="utf-8"))
            return raw["private_key_der_b64"], raw["public_key_b64"]
        except (json.JSONDecodeError, OSError, KeyError):
            log.exception("Failed to load vapid_keys.json — regenerating (existing push subscriptions will need to re-subscribe).")

    vapid = Vapid02()
    vapid.generate_keys()
    private_key_der = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_key_der_b64 = b64urlencode(private_key_der)
    # The uncompressed EC point (0x04 || X || Y), base64url-encoded with
    # no padding — the exact shape browsers' PushManager.subscribe()
    # expects for `applicationServerKey`. py_vapid has no built-in
    # accessor for this encoding (confirmed via its own source — public_key
    # is a raw cryptography EC key object), so it's derived directly here.
    public_key_raw = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_key_b64 = b64urlencode(public_key_raw)

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _VAPID_KEYS_FILE.write_text(
        json.dumps({"private_key_der_b64": private_key_der_b64, "public_key_b64": public_key_b64}, indent=2),
        encoding="utf-8",
    )
    log.info("Generated a new VAPID keypair for Web Push.")
    return private_key_der_b64, public_key_b64


def send_web_push(
    subscription: PushSubscription,
    title: str,
    message: str,
    subscriptions: PushSubscriptionManager,
) -> bool:
    """Sends one push message to `subscription`. Returns True on success,
    False on any failure (network error, or the push service reporting
    it undeliverable) — never raises. `subscriptions` is used to drop a
    subscription the push service reports as permanently gone."""
    private_key_der_b64, _ = get_or_create_vapid_keys()
    payload = json.dumps({"title": title, "message": message})

    try:
        webpush(
            subscription_info=subscription.as_webpush_subscription_info(),
            data=payload,
            vapid_private_key=private_key_der_b64,
            vapid_claims={"sub": _VAPID_CLAIM_SUB},
        )
        return True
    except WebPushException as exc:
        if exc.status_code in _DEAD_SUBSCRIPTION_STATUS_CODES:
            log.info("Push subscription for profile '%s' is gone (status %s) — removing it.", subscription.profile_id, exc.status_code)
            subscriptions.remove_subscription(subscription.endpoint)
        else:
            log.warning("Web Push send failed for profile '%s': %s", subscription.profile_id, exc)
        return False
    except requests.exceptions.RequestException:
        # The push service itself was unreachable (network down, DNS
        # failure, timeout) — webpush() only wraps a *reached* service's
        # non-success response in WebPushException, so this is a
        # separate, equally routine failure case to degrade gracefully on.
        log.warning("Push service unreachable while sending to profile '%s'.", subscription.profile_id, exc_info=True)
        return False
    except ValueError:
        # A malformed p256dh/auth key (bad base64) raises here before
        # webpush() ever reaches the network — caught during this
        # feature's own manual verification. Not a "confirmed gone"
        # signal from the push service itself, so the subscription is
        # logged but not removed (unlike the 404/410 case above).
        log.warning("Malformed push subscription for profile '%s' — cannot send.", subscription.profile_id, exc_info=True)
        return False
