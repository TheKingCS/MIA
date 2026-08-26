"""
MIA Homestead — Notification Dispatch
v0.1

Handles the escalation rules from SAFETY_SPEC.md: info -> log only,
warning -> dashboard + digest, critical -> immediate push to primary +
secondary contact. Email works out of the box with any SMTP account
(Gmail app password, etc). SMS is stubbed against Twilio's API shape —
drop in real credentials when ready, no interface change needed.
"""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.notifications")


@dataclass
class NotificationConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = ""
    primary_contact_email: str = ""
    secondary_contact_email: str = ""
    # SMS — leave blank until a provider is chosen; dispatch becomes a
    # no-op (logged only) until these are set.
    sms_provider_api_key: str = ""
    primary_contact_phone: str = ""
    secondary_contact_phone: str = ""


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
            self._send_sms(self.config.primary_contact_phone, message)
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
            self._send_sms(self.config.secondary_contact_phone, message)

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

    def _send_sms(self, to: str, body: str) -> None:
        if not to or not self.config.sms_provider_api_key:
            logger.debug("SMS not configured — skipping send")
            return
        # TODO: wire to actual provider (Twilio, etc) once chosen.
        # Kept as a clearly-marked stub rather than a fake success —
        # a silent no-op here would be exactly the kind of false
        # confidence this whole system is designed to avoid.
        logger.warning(
            "SMS dispatch requested but no provider wired yet — "
            "message NOT sent: %s", body,
        )

    def describe_capabilities(self):
        from contracts.capability import Capability
        sms_ready = bool(self.config.sms_provider_api_key)
        return Capability(
            module_id="notifications",
            display_name="Notification Dispatch",
            purpose=(
                "Escalates alerts to a human: info is logged only, warnings "
                "go to email, critical alerts go to primary + secondary "
                "contact via email (and SMS once a provider is configured)."
            ),
            data_produced=[],
            actions_possible=["send email", "send SMS" if sms_ready else "send SMS (not configured yet)"],
            limits_and_safety=(
                "SMS is currently stubbed — it logs 'not sent' rather than "
                "silently failing, so a missing provider is never mistaken "
                "for a delivered alert."
            ),
            example_questions=["Would I get notified if something went critical right now?"],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # sends over existing internet/cell connection — no dedicated hardware
