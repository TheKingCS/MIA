"""
tests.test_storm_thread
=========================

The preparedness conversation check's fixes (2026-11-26): "how prepared am I for a winter storm?" is the checklist
from his records, "what am I missing?" after it his kit's gaps (it had listed MIA's own software), and her setup's
"what am I missing" only when it says her setup.
"""

from types import SimpleNamespace

from core import assistant_turn, her_asks, service_map, storm_ready


def test_ready_and_missing(monkeypatch):
    monkeypatch.setattr(storm_ready, "checklist", lambda c, f=None: ["Drinking water: about 5 days.",
                                                                     "Charge phones and power banks."])
    said = storm_ready.ready_for(SimpleNamespace(), "winter storm")
    assert said.startswith("For a winter storm, from your records: Drinking water")
    monkeypatch.setattr(storm_ready, "ready_for", lambda c, k="storm": f"ready[{k}]")
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "how prepared am I for a winter storm?") == \
        "ready[winter storm]"
    from core import ready_kit

    monkeypatch.setattr(ready_kit, "say", lambda c, p=None: "kit")
    assert her_asks.reply(SimpleNamespace(), said, "what am I missing?") == "kit"
    assert not service_map._DOWN.search("what am i missing?")
    assert service_map._DOWN.search("what are you missing?")
    assert service_map._DOWN.search("what am i missing in your setup?")
