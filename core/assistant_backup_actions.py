"""
core.assistant_backup_actions
===============================

Backups by voice (DEC-0125), read only: "when did I last back up?" says how
long since the last backup in the backups folder and where they go
(core/web_backups.py). Making one is on Settings (a passphrase is typed, never
said aloud); restoring is on the PC.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _status(context, arguments: dict) -> str:
    """Tool get_backup_status: the last backup's age, how many there are, and where; for the PC's owner."""
    from core.person_settings import _is_first_account, person_id
    from core.web_backups import status

    if not _is_first_account(context, person_id(context) or ""):
        return "Backups are the PC owner's."
    info = status(context)
    if not info["count"]:
        return f"There are no backups in {info['folder']} yet. Settings has Back Up Now."
    last = info["backups"][0]
    return (f"Your last backup was {info['last']} ({last['size']}{', with a passphrase' if last['locked'] else ''}); "
            f"{info['count']} in {info['folder']}.")


def register_backup_actions(registry) -> None:
    """Registers get_backup_status."""
    registry.register(AssistantAction(
        name="get_backup_status", domain="backup",
        description="When MIA was last backed up, and where the backups are.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_status,
        trigger_phrases=("last backup", "backed up", "my backups", "backup status"),
    ))
    registry.register_domain_keywords("backup", ("backup", "backups", "backed up"))
