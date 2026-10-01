"""
core.assistant_email_actions
===============================

The Assistant writes emails (2026-10-01, accounts stage 3,
core/email_drafts.py). `draft_email` only ever makes a draft: the person
sends it by pressing Send (desktop or phone), copies it, or opens it in
their mail app. There is deliberately no tool that sends.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.email_drafts import addresses_in
from core.main_thread import publish
from core.person_settings import person_id


def _action_draft_email(context, arguments: dict) -> str:
    drafts = getattr(context, "email_drafts", None)
    if drafts is None:
        return "I can't keep drafts until someone is signed in."
    body = str(arguments.get("body") or "").strip()
    if not body:
        return "What should the email say?"
    to = addresses_in(str(arguments.get("to") or ""))
    subject = str(arguments.get("subject") or "").strip()
    draft = drafts.create(to, subject, body)
    # A phone turn runs on the person's own view (it has a profile_id); its
    # draft shows on the phone, not as a window at the desk.
    on_phone = bool(getattr(context, "profile_id", None))
    publish(context, "email.draft_ready", draft_id=draft.draft_id, profile_id=person_id(context), on_phone=on_phone)
    who = f" to {', '.join(to)}" if to else ""
    missing = "" if to else " Add who it goes to (their email address)."
    return (f"I wrote a draft{who}: \"{subject or 'no subject'}\". Have a look: you can Send it, Copy it, or open it "
            f"in your mail app. I won't send anything unless you press Send.{missing}")


def register_email_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="draft_email", domain="email",
        description=(
            "Write an email for the user as a draft they review. Write the whole email yourself: a clear subject and "
            "a friendly, complete body in the user's voice, signed with their name. Never claims it was sent: the "
            "user sends it by pressing Send, copies it, or opens it in their mail app."
        ),
        parameters={"type": "object", "properties": {
            "to": {"type": "string", "description": "Recipient email address(es), if the user gave them."},
            "subject": {"type": "string", "description": "The subject line."},
            "body": {"type": "string", "description": "The full email text."},
        }, "required": ["subject", "body"]},
        handler=_action_draft_email,
        trigger_phrases=("an email", "email to", "email my", "email the", "email him", "email her", "email them",
                         "e-mail", "write to", "draft a", "draft an", "write a letter", "reply to", "an e-mail"),
    ))
