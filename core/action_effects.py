"""
core.action_effects
=====================

What each kind of action reaches, and whether it can be undone (REQ-AUT-006, REQ-AUT-007; DEC-0181; prompt 23's
review, UI-3). Every action kind is one of four reaches and three reversibilities:

**Reach**
- `records`: only the person's records in MIA's stores;
- `device`: something on the machine outside the stores (his files, a camera, a sensor, an offline map);
- `system`: the machine or MIA herself (her code, the operating system);
- `outside`: another person, a shop or a site.

**Reversibility**
- `undoable`: "undo" puts it back exactly (its writes go through the stores, which the undo log and the lasting
  history keep);
- `compensable`: another action reverses it (a renamed file renamed back, a removed camera added again);
- `irreversible`: nothing puts it back (a file deleted, a message sent, a commit pressed on a site).

Most of MIA's 468 kinds only change records and are undoable, so that is the default. `EFFECTS` names every kind
that differs, each checked by reading its code (Opus, 2026-11-16). Two rules use it:
- an irreversible kind says so in its approval sentence (`ActionCenter.propose` adds "This can't be undone." when
  the sentence doesn't already say it);
- a kind that reaches the system or outside is tiered `act_with_approval` or `never` in its app's manifest
  (REQ-AUT-007; tests/test_action_effects.py holds it).

A sweep test reads every kind's code for the marks of reaching beyond the stores (deleting or moving files, the
network, a device link, a subprocess, the lab) and fails on one that isn't declared here, so a new outward action
can't slip in as "records".
"""

from __future__ import annotations

REACHES = ("records", "device", "system", "outside")
REVERSIBILITY = ("undoable", "compensable", "irreversible")
DEFAULT = ("records", "undoable")

# kind -> (reach, reversibility, why)
EFFECTS: dict[str, tuple[str, str, str]] = {
    # outside
    "browser.commit": ("outside", "irreversible", "presses a commit on a site: an order placed, a form sent"),
    "map.tak_share": ("outside", "irreversible", "sends his places to TAK apps on the network, where they stay"),
    # system
    "lab.approve": ("system", "compensable", "merges a change into MIA's own code; a later change can revert it"),
    "lab.revert": ("system", "compensable", "takes one of her changes back out of her code; it can be retried"),
    # FW-06: through the system helper, his password asked again in the operating system's dialog
    "system.restart_service": ("system", "compensable", "restarts one of her system services; it comes back up"),
    "system.power": ("system", "irreversible", "powers off or restarts the computer: whatever was open closes"),
    "system.apply_update": ("system", "compensable", "restarts into the staged update; the previous one stays bootable"),
    # REQ-HW-014: her models in the model server's store, never his records
    "model.remove": ("device", "compensable", "removes one of her models from the model server; it can be fetched again"),
    "model.fetch": ("device", "compensable", "downloads one of her models again into the model server; it can be removed"),
    "library.fetch": ("device", "compensable", "downloads reference packs into her offline library; each can be deleted"),
    # device: can't be put back
    "myfile.delete": ("device", "irreversible", "deletes one of his files or folders for good"),
    "track.delete": ("device", "irreversible", "deletes a music file from the disk"),
    "security.picture_delete": ("device", "irreversible", "deletes a camera picture file"),
    "craft.photo_delete": ("device", "irreversible", "deletes a build photo file"),
    "expedition.media_delete": ("device", "irreversible", "deletes an expedition's photo or video file"),
    # device: another action reverses it
    "myfile.rename": ("device", "compensable", "renames one of his files; renaming it back reverses it"),
    "myfile.folder": ("device", "compensable", "makes a folder in his files; deleting it reverses it"),
    "conversation.export": ("device", "compensable", "writes a copy of a conversation into his files"),
    "map.area_keep": ("device", "compensable", "downloads an offline map area; taking it off reverses it"),
    "map.area_remove": ("device", "compensable", "deletes a downloaded map area; it can be downloaded again"),
    "security.save_picture": ("device", "compensable", "takes and keeps a camera picture; deleting it reverses it"),
    "camera.remove": ("device", "compensable", "takes a camera off; adding it again reverses it"),
    "sensor.remove": ("device", "compensable", "revokes a sensor's key; the sensor must be added again"),
    # records, but not through the undo log alone
    "inbox.file": ("records", "compensable", "moves a document into place; unfiling it reverses it"),
    "inbox.unfile": ("records", "compensable", "moves a document back to the inbox; filing it reverses it"),
    "activity.erase": ("records", "irreversible", "erases what she noted about his apps, with no copy kept"),
    "undo.last": ("records", "irreversible", "an undo isn't itself undone"),
    "history.undo": ("records", "irreversible", "an undo isn't itself undone"),
}


def effect_of(kind: str) -> tuple[str, str]:
    """Pure logic. (reach, reversibility) for an action kind; records and undoable unless declared."""
    found = EFFECTS.get(kind)
    return (found[0], found[1]) if found else DEFAULT


def says_irreversible(summary: str) -> str:
    """Pure logic. An approval sentence that says it can't be undone, if it doesn't already."""
    low = (summary or "").lower()
    if any(w in low for w in ("can't be undone", "cannot be undone", "for good", "permanently", "can't be taken back")):
        return summary
    return (summary or "").rstrip(" .") + ". This can't be undone."
