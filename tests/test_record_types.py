"""Tests for the record-type registry (LS-05, core/record_types.py): one table links and the history share, and a
kind the history names is either readable or listed with why it isn't."""
import re
from pathlib import Path
from types import SimpleNamespace

from core import links, record_types

ROOT = Path(__file__).resolve().parent.parent


def _history_kinds() -> dict:
    """Every kind a life-event ref names in core/ and modules/: the f-string refs inside life_events.record(...) and
    on_change(...) calls, and on_change's own ref."""
    found: dict = {}
    for path in list((ROOT / "core").rglob("*.py")) + list((ROOT / "modules").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"life_events\.(?:record|on_change)\(", text):
            i, depth = match.end(), 1
            while depth and i < len(text):
                depth += {"(": 1, ")": -1}.get(text[i], 0)
                i += 1
            call = text[match.end():i]
            for kind in re.findall(r"[\"']([a-z_]+):(?:\{|[\"'])", call):
                found.setdefault(kind, path.name)
            if "on_change" in match.group(0):
                parts = re.findall(r"[\"']([^\"']*)[\"']", call)
                if len(parts) >= 3 and parts[2]:
                    found.setdefault(parts[2].split(":")[0], path.name)
    return found


def test_every_kind_the_history_names_is_in_the_registry():
    """A new `kind:` in a life event's refs needs a place: readable in TYPES, or in HISTORY_ONLY with why."""
    unknown = {kind: where for kind, where in _history_kinds().items() if not record_types.known(kind)}
    assert unknown == {}


def test_links_read_the_same_table():
    """Links' kinds are the registry's, not a copy."""
    assert links.KINDS is record_types.TYPES and links.Kind is record_types.RecordType


def test_no_kind_is_both_readable_and_history_only():
    """A kind is either read back or skipped with a reason, never both; every reason is said."""
    assert not set(record_types.TYPES) & set(record_types.HISTORY_ONLY)
    assert all(why.strip() for why in record_types.HISTORY_ONLY.values())


def test_a_ref_reads_its_record_from_its_store():
    """read() finds the record by id through the store's lister, whether it keeps objects or dicts."""
    store = SimpleNamespace(all_projects=lambda: [SimpleNamespace(project_id="p1", name="Barn")],
                            notes=[{"id": "n1", "what": "call"}])
    context = SimpleNamespace(projects=store, life_notes=store)
    assert record_types.read(context, "project:p1").name == "Barn"
    assert record_types.read(context, "note:n1") == {"id": "n1", "what": "call"}
    assert record_types.read(context, "project:gone") is None and record_types.read(context, "alarm:a1") is None
    assert record_types.readable(context, "project") and not record_types.readable(context, "asset")


def test_a_persons_own_record_set_reads_back_under_the_households_kind():
    """A person's own record sets record `record_set:` refs, so read() looks in their store too."""
    context = SimpleNamespace(record_sets=SimpleNamespace(sets=[]), my_record_sets=SimpleNamespace(sets=[{"id": "r1"}]))
    assert record_types.read(context, "record_set:r1") == {"id": "r1"}
