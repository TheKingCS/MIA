"""
MIA Homestead — Notification Dispatch
v0.1

Handles the escalation rules from SAFETY_SPEC.md: info -> log only,
warning -> dashboard + digest, critical -> immediate push to primary +
secondary contact. Email works out of the box with any SMTP account
(Gmail app password, etc).

SMS ships via a carrier email-to-SMS gateway (corrected 2026-08-30 —
originally stubbed against Twilio's API shape, which this project's own
no-outside-vendor-dependency stance argues against for something this
project can already do for free). A carrier's gateway is just an email
address — `<10-digit-number>@<gateway-domain>` — so this reuses
_send_email() unchanged; there's no separate delivery mechanism to
build or maintain, and no new account/API key/recurring cost beyond
the SMTP account email already needs. The trade-off, stated plainly:
delivery depends on the carrier keeping their gateway domain running
(most major US carriers have for years, but it's not contractually
guaranteed the way a paid API is) and the message length carriers
silently truncate/split varies by carrier — genuinely lower assurance
than Twilio for a genuinely large reduction in cost and dependency
surface. Right trade-off for this project's stated values; would be
the wrong one for something safety-certified.
"""

import logging
import smtplib
from dataclasses import dataclass, fields
from email.message import EmailMessage
from pathlib import Path

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.notifications")

# Free carrier email-to-SMS gateways — not exhaustive (an MVNO usually
# rides its parent network's gateway; add more here as needed, this is
# a lookup table, not an external dependency). SMS length is limited
# and carrier-truncated unpredictably beyond it — kept conservative.
CARRIER_SMS_GATEWAYS = {
    "verizon": "vtext.com",
    "att": "txt.att.net",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",  # legacy network, mostly merged into T-Mobile now
    "uscellular": "email.uscc.net",
    "boost": "sms.myboostmobile.com",
    "cricket": "sms.cricketwireless.net",
    "metropcs": "mymetropcs.com",
    "googlefi": "msg.fi.google.com",
    "visible": "vtext.com",   # rides Verizon's network
    "mint": "tmomail.net",    # rides T-Mobile's network
}
SMS_MAX_LENGTH = 300  # conservative — most carrier gateways truncate/split well before this


@dataclass
class NotificationConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = ""
    primary_contact_email: str = ""
    secondary_contact_email: str = ""
    # SMS via carrier email gateway — both phone AND carrier are
    # required (the gateway domain is carrier-specific); dispatch
    # no-ops (logged, not silently dropped) if either is missing or
    # the carrier isn't in CARRIER_SMS_GATEWAYS.
    primary_contact_phone: str = ""
    primary_contact_carrier: str = ""    # a key in CARRIER_SMS_GATEWAYS, e.g. "verizon"
    secondary_contact_phone: str = ""
    secondary_contact_carrier: str = ""

    @classmethod
    def from_config(cls, path: str = "config/notifications.yaml") -> "NotificationConfig":
        """Real gap found live 2026-09-02 (docs/DAY_ONE_READINESS.md):
        main.py used to construct NotificationConfig() with zero
        arguments, every run, with no way to set real values short of
        hand-editing main.py's source — the one configurable subsystem
        in this project that didn't follow its own "config IS the
        source of truth" convention (config/location.yaml,
        config/irrigation_schedules.yaml, config/mia_home_sync.yaml all
        do). A missing file or empty values behaves EXACTLY like the
        old NotificationConfig() default — inert, never guessed at,
        same precedent as location.yaml's weather-check gate — so this
        is purely additive: nothing that worked before changes."""
        import yaml
        p = Path(path)
        if not p.exists():
            logger.info("No notification config at %s — notifications stay inert", path)
            return cls()
        raw = yaml.safe_load(p.read_text()) or {}
        known_fields = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known_fields and v is not None})


class NotificationDispatcher(Describable):
    def __init__(self, config: NotificationConfig):
        self.config = config

    def dispatch(self, severity: str, message: str, source: str = "") -> None:
        if severity == "info":
            logger.info("[INFO] %s: %s", source, message)
            return

        if severity == "warning":
            logger.warning("[WARNING] %s: %s", source, message)
            self._send_email(
                to=self.config.primary_contact_email,
                subject=f"MIA Homestead — Warning: {source}",
                body=message,
            )
            return

        if severity == "critical":
            logger.error("[CRITICAL] %s: %s", source, message)
            self._send_email(
                to=self.config.primary_contact_email,
                subject=f"MIA Homestead — CRITICAL: {source}",
                body=message,
            )
            if self.config.secondary_contact_email:
                self._send_email(
                    to=self.config.secondary_contact_email,
                    subject=f"MIA Homestead — CRITICAL (escalated): {source}",
                    body=message,
                )
            self._send_sms(self.config.primary_contact_phone, self.config.primary_contact_carrier, message)
            return

    def dispatch_dead_mans_switch(self, hours_since_checkin: float) -> None:
        """Called when no human has acknowledged anything within the
        configured window (default 72h per SAFETY_SPEC.md) — escalates
        to secondary contact even with no active fault, since the whole
        point is catching 'something's wrong and no one's watching.'"""
        message = (
            f"No check-in on the MIA Homestead dashboard or alerts in "
            f"{hours_since_checkin:.0f} hours. This doesn't necessarily "
            f"mean anything's wrong with the system, but no one has "
            f"confirmed that recently."
        )
        if self.config.secondary_contact_email:
            self._send_email(
                to=self.config.secondary_contact_email,
                subject="MIA Homestead — No recent check-in",
                body=message,
            )
        if self.config.secondary_contact_phone:
            self._send_sms(self.config.secondary_contact_phone, self.config.secondary_contact_carrier, message)

    # ---------- Delivery mechanics ----------

    def _send_email(self, to: str, subject: str, body: str) -> None:
        if not to or not self.config.smtp_host:
            logger.debug("Email not configured — skipping send (%s)", subject)
            return
        msg = EmailMessage()
        msg["From"] = self.config.from_address
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
            logger.info("Email sent to %s: %s", to, subject)
        except Exception:
            logger.exception("Failed to send email to %s", to)

    def _sms_gateway_address(self, phone: str, carrier: str) -> str | None:
        """Pure — computes the carrier email-gateway address for an
        SMS, or None if phone/carrier is missing or unrecognized. Split
        out from _send_sms() so the address-construction logic is
        directly testable without touching smtplib."""
        if not phone or not carrier:
            return None
        gateway = CARRIER_SMS_GATEWAYS.get(carrier.lower().strip())
        if gateway is None:
            return None
        digits = "".join(c for c in phone if c.isdigit())
        if not digits:
            return None
        return f"{digits}@{gateway}"

    def _send_sms(self, phone: str, carrier: str, body: str) -> None:
        address = self._sms_gateway_address(phone, carrier)
        if address is None:
            if phone and carrier and carrier.lower().strip() not in CARRIER_SMS_GATEWAYS:
                # Missing/unset is the common "not configured yet" case (debug-level,
                # matches _send_email's own quiet skip); an actually-unrecognized
                # carrier name is more likely a typo worth a human noticing.
                logger.warning(
                    "SMS requested but carrier '%s' isn't a known gateway — message "
                    "NOT sent. Known carriers: %s", carrier, ", ".join(sorted(CARRIER_SMS_GATEWAYS)),
                )
            else:
                logger.debug("SMS not configured (missing phone or carrier) — skipping send")
            return
        # Carrier gateways silently truncate/split long messages
        # unpredictably — truncate client-side instead, so what's sent
        # is at least a controlled, complete-sentence-ish cut rather
        # than whatever a specific carrier happens to do.
        truncated = body if len(body) <= SMS_MAX_LENGTH else body[:SMS_MAX_LENGTH - 3] + "..."
        self._send_email(to=address, subject="", body=truncated)

    def describe_capabilities(self):
        from contracts.capability import Capability
        sms_ready = bool(self.config.primary_contact_phone and self.config.primary_contact_carrier)
        return Capability(
            module_id="notifications",
            display_name="Notification Dispatch",
            purpose=(
                "Escalates alerts to a human: info is logged only, warnings "
                "go to email, critical alerts go to primary + secondary "
                "contact via email and SMS (once a phone+carrier are configured)."
            ),
            data_produced=[],
            actions_possible=["send email", "send SMS" if sms_ready else "send SMS (not configured yet)"],
            limits_and_safety=(
                "SMS goes via a free carrier email-to-SMS gateway (CARRIER_SMS_GATEWAYS — "
                "corrected 2026-08-30 from an original Twilio-shaped stub, per this project's "
                "own no-outside-vendor-dependency stance), not a paid API — lower delivery "
                "assurance than a dedicated SMS provider (depends on the carrier's gateway "
                "staying up, no delivery receipts), traded for zero new account/cost beyond "
                "the SMTP email already configured. An unconfigured or unrecognized carrier "
                "logs 'not sent' rather than silently failing, same honesty stance as before."
            ),
            example_questions=["Would I get notified if something went critical right now?"],
            verification_evidence=[
                "Live manual test 2026-08-26: email dispatch path exercised throughout session "
                "logs (no real SMTP credentials configured, so delivery itself unverified — "
                "the code path and severity routing are).",
                "Live manual test 2026-08-31 (SMS gateway): confirmed _sms_gateway_address() "
                "correctly builds e.g. '5551234567@vtext.com' for a real phone+carrier pair, "
                "strips non-digit formatting from the phone number, returns None for a missing "
                "phone/carrier and for an unrecognized carrier name (with the unrecognized case "
                "logging a distinct warning naming the known carriers, not a silent skip), and "
                "correctly truncates a body over SMS_MAX_LENGTH. Real SMTP delivery itself is "
                "unverified here for the same reason email's is — no real account configured in "
                "this dev sandbox — but the address-construction and routing logic, the part "
                "unique to this change, is verified directly.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # sends over existing internet/cell connection — no dedicated hardware
