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


def known_addresses(context) -> list[tuple[str, str]]:
    """(name, email) MIA can address by name: People & Pets, and the other
    people in this household (their sign-in email)."""
    known = []
    relationships = getattr(context, "relationships", None)
    for person in (relationships.all_people() if relationships is not None else []):
        if getattr(person, "email", ""):
            known.append((person.name, person.email))
    households = getattr(context, "households", None)
    me = person_id(context)
    if households is not None and me:
        known += [(p.name, p.email) for p in households.shares_with(me) if p.email]
    return known


def resolve_recipients(context, to: str) -> tuple[list[str], list[str]]:
    """Pure-ish. (addresses, names said but without a known address).
    Written addresses win; otherwise names are looked up, whole words only."""
    written = addresses_in(to)
    if written:
        return written, []
    text = f" {(to or '').lower()} "
    found, by_first = [], {}
    for name, email in known_addresses(context):
        by_first.setdefault(name.lower().split()[0], []).append(email)
        if f" {name.lower()} " in text:
            found.append(email)
    for first, emails in by_first.items():
        if not found and f" {first} " in text and len(emails) == 1:
            found.append(emails[0])
    if found:
        return list(dict.fromkeys(found)), []
    words = [w.strip(".,") for w in (to or "").split() if w[:1].isupper()]
    return [], words


def _action_draft_email(context, arguments: dict) -> str:
    drafts = getattr(context, "email_drafts", None)
    if drafts is None:
        return "I can't keep drafts until someone is signed in."
    body = str(arguments.get("body") or "").strip()
    if not body:
        return "What should the email say?"
    to, unknown = resolve_recipients(context, str(arguments.get("to") or ""))
    subject = str(arguments.get("subject") or "").strip()
    draft = drafts.create(to, subject, body)
    # A phone turn runs on the person's own view (it has a profile_id); its
    # draft shows on the phone, not as a window at the desk.
    on_phone = bool(getattr(context, "profile_id", None))
    publish(context, "email.draft_ready", draft_id=draft.draft_id, profile_id=person_id(context), on_phone=on_phone)
    who = f" to {', '.join(to)}" if to else ""
    if to:
        missing = ""
    elif unknown:
        missing = (f" I don't have an email address for {' '.join(unknown)}: add it in the draft, or tell me "
                   f"(\"{unknown[0]}'s email is ...\") and I'll remember it.")
    else:
        missing = " Add who it goes to (their email address)."
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
            "to": {"type": "string", "description": "Who it's to: an email address, or the person's name."},
            "subject": {"type": "string", "description": "The subject line."},
            "body": {"type": "string", "description": "The full email text."},
        }, "required": ["subject", "body"]},
        handler=_action_draft_email,
        trigger_phrases=("an email", "email to", "email my", "email the", "email him", "email her", "email them",
                         "e-mail", "write to", "draft a", "draft an", "write a letter", "reply to", "an e-mail"),
    ))
