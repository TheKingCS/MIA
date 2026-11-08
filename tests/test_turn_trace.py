"""Turn traces (DEC-0067, core/turn_trace.py): one line per turn, how it was
answered and how long it took; never a private turn, never a password."""

from tests.engine_world import build_world


def _world(tmp_path, monkeypatch):
    """The test household with no model and turn traces in a temporary folder."""
    from core.turn_trace import TurnTraces

    w = build_world(tmp_path, monkeypatch)
    w.llm = None
    w.traces = TurnTraces(w, data_dir=tmp_path / "traces")
    return w


def test_a_turn_leaves_one_trace_with_its_route(tmp_path, monkeypatch):
    from core.assistant_turn import run_assistant_turn
    from core.conversation_manager import Conversation

    w = _world(tmp_path, monkeypatch)
    run_assistant_turn(w, Conversation(conversation_id="c", title="t"), "MIA, show off for my friends")
    t = w.traces.recent()[-1]
    assert t["route"] == "show off" and t["conversation"] == "c" and t["seconds"] >= 0
    assert t["asked"] == "MIA, show off for my friends" and t["words"] > 0


def test_a_turn_with_no_model_says_so(tmp_path, monkeypatch):
    from core.assistant_turn import run_assistant_turn
    from core.conversation_manager import Conversation

    w = _world(tmp_path, monkeypatch)
    run_assistant_turn(w, Conversation(conversation_id="c", title="t"), "what do you think about sailing?")
    t = w.traces.recent()[-1]
    assert t["route"] == "no model" and t["model_answered"] is False


def test_a_password_never_reaches_a_trace(tmp_path, monkeypatch):
    from core.assistant_turn import run_assistant_turn
    from core.conversation_manager import Conversation

    w = _world(tmp_path, monkeypatch)
    run_assistant_turn(w, Conversation(conversation_id="c", title="t"), "my password is hunter2, what do you think?")
    assert "hunter2" not in w.traces.recent()[-1]["asked"]


def test_a_private_turn_is_never_traced(tmp_path, monkeypatch):
    from core.turn_trace import record

    w = _world(tmp_path, monkeypatch)

    class Private:
        conversation_id, mode = "p", "listen"

        def current_privacy(self):
            return "off_record"

    record(w, Private(), "something private", type("T", (), {"replies": ["ok"]})(), 0.1)
    assert w.traces.recent() == []


def test_traces_are_kept_on_disk_and_bounded(tmp_path):
    import core.turn_trace as tt

    traces = tt.TurnTraces(data_dir=tmp_path)
    for i in range(tt.MAX_KEPT + 5):
        traces.traces.append({"i": i})
    traces.add({"i": "last"})
    again = tt.TurnTraces(data_dir=tmp_path)
    assert len(again.traces) == tt.MAX_KEPT and again.traces[-1] == {"i": "last"}
