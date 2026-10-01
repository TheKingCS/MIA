"""
Quick capture (core/quick_capture.py, gui/quick_capture_dialog.py),
2026-10-01: type anything, MIA files it; nothing is ever lost.
"""

from types import SimpleNamespace

import pytest

from core.assistant_turn import AssistantTurn
from core.conversation_manager import ConversationManager
from core.event_bus import EventBus
from core.journal_manager import JournalManager
from core.quick_capture import NOTE_TAG, TITLE, capture
from core.undo_log import UndoLog, recording


@pytest.fixture
def ctx(tmp_path):
    context = SimpleNamespace(events=EventBus(), llm=object(), undo=UndoLog(), profile_id="p1",
                              config=SimpleNamespace(get=lambda k, d=None: d))
    context.conversations = ConversationManager(context, data_dir=tmp_path)
    context.journal = JournalManager(context, data_dir=tmp_path)
    return context


def _files_it(tmp_path):
    def run(context, conversation, text):
        with recording("add_grocery_item", "p1") as change:
            (tmp_path / "grocery.json").write_text(text)  # a store writing (simulated)
            change.files[tmp_path / "grocery.json"] = None
        context.undo.add(change)
        return AssistantTurn(replies=["Added milk and eggs to the grocery list."])
    return run


def test_filed_by_a_tool(ctx, tmp_path):
    result = capture(ctx, "milk and eggs", turn_runner=_files_it(tmp_path))
    assert result.filed and result.reply == "Added milk and eggs to the grocery list."
    assert ctx.journal.all_entries() == []
    [conversation] = ctx.conversations.all_conversations()
    assert conversation.title == TITLE


def test_unfiled_becomes_a_note(ctx):
    asked = lambda context, conversation, text: AssistantTurn(replies=["Which list?"])  # noqa: E731
    result = capture(ctx, "idea: a rain barrel by the shed", turn_runner=asked)
    assert not result.filed and "Saved as a note" in result.reply
    [note] = ctx.journal.all_entries()
    assert note.title == "idea: a rain barrel by the shed" and NOTE_TAG in note.tags


def test_without_the_model_or_when_it_fails(ctx):
    ctx.llm = None
    assert "Saved as a note" in capture(ctx, "call the vet").reply

    def broken(context, conversation, text):
        raise RuntimeError("boom")

    ctx.llm = object()
    assert not capture(ctx, "x" * 80, turn_runner=broken).filed
    assert any(e.title.endswith("…") for e in ctx.journal.all_entries())
    assert capture(ctx, "   ").reply == "Nothing to capture."


def test_the_box(ctx, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    import gui.quick_capture_dialog as dialog_module

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(dialog_module, "capture", lambda c, t: capture(c, t, turn_runner=_files_it(tmp_path)))

    class Now:  # run the worker inline so the test sees the result
        def __init__(self, target, daemon, name):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(dialog_module.threading, "Thread", Now)
    box = dialog_module.QuickCaptureDialog(ctx)
    box.edit.setText("milk and eggs")
    box._on_submit()
    assert "grocery list" in box.result_label.text() and box.undo_button.isEnabled() and box.edit.text() == ""
    box._on_undo()
    assert box.result_label.text() == "Undone." and not (tmp_path / "grocery.json").exists()
