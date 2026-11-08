"""Every knowledge entry in work/knowledge/ has its own id: two sessions working at once can each write the next
number, and a merge then brings both in (found 2026-11-07: seven pairs). Renumber the newer one when this fails."""

from collections import Counter
from pathlib import Path

KNOWLEDGE = Path(__file__).resolve().parent.parent / "work" / "knowledge"


def test_no_two_knowledge_entries_share_an_id():
    ids = Counter(p.name[:6] for p in KNOWLEDGE.glob("K-*.md"))
    assert not [k for k, n in ids.items() if n > 1], "duplicate knowledge ids"
