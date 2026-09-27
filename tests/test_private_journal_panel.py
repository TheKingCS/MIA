"""The Private Journal tab (gui/private_journal_panel.py) and the desktop
chat surfaces' safety-floor path, offscreen."""

import pytest
from PySide6.QtWidgets import QApplication

import core.config_manager as config_module
import core.conversation_manager as conversation_module
import core.private_journal as pj
import core.user_memory_manager as memory_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.event_bus import EventBus
from core.private_journal import JournalExchange, PrivateJournalEntry, PrivateJournalManager
from core.user_memory_manager import UserMemoryManager
from gui.private_journal_panel import PrivateJournalPanel, format_private_entry_row, render_private_entry_html

PASS = "correct horse battery"


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(tmp_path, monkeypatch, qapp):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(conversation_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(conversation_module, "_CONVERSATIONS_FILE", tmp_path / "conversations.json")
    monkeypatch.setattr(memory_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(memory_module, "_USER_MEMORIES_FILE", tmp_path / "user_memories.json")
    monkeypatch.setattr(pj, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(pj, "_KEYS_FILE", tmp_path / "private_journal_keys.json")
    monkeypatch.setattr(pj, "_ENTRIES_FILE", tmp_path / "private_journal.json")
    monkeypatch.setattr(pj, "_RSA_KEY_SIZE", 2048)
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.conversations = ConversationManager(context)
    context.user_memories = UserMemoryManager(context)
    context.private_journal = PrivateJournalManager(context)
    return context


def _entry():
    return PrivateJournalEntry(
        entry_id="e1", title="Long shift <3", mood="drained", themes=["work"], summary="You talked about work.",
        exchanges=[JournalExchange("user", "It dragged."), JournalExchange("assistant", "That sounds long.")],
        created_at="2026-09-27T17:05:00",
    )


def test_formatting_escapes_and_labels():
    entry = _entry()
    assert format_private_entry_row(entry) == "2026-09-27  Long shift <3  · drained"
    rendered = render_private_entry_html(entry)
    assert "Long shift &lt;3" in rendered and "<b>You:</b> It dragged." in rendered and "<b>MIA:</b>" in rendered


def test_panel_states(ctx):
    panel = PrivateJournalPanel(ctx)
    assert panel._setup_button.isVisibleTo(panel) and not panel._unlock_button.isVisibleTo(panel)

    ctx.private_journal.setup(PASS)
    ctx.private_journal.save_entry(_entry())
    ctx.private_journal.lock()
    panel.refresh()
    assert panel._unlock_button.isVisibleTo(panel) and panel._list.count() == 0
    assert "1 entry saved" in panel._status_label.text()

    ctx.private_journal.unlock(PASS)
    panel.refresh()
    assert panel._lock_button.isVisibleTo(panel) and panel._list.count() == 1
    panel._list.setCurrentRow(0)
    assert "It dragged." in panel._reader.toPlainText()


def test_assistant_module_safety_reply_without_the_model(ctx, monkeypatch):
    from modules.assistant.module import AssistantModule

    ctx.llm = None  # the model is down; the floor must still answer
    module = AssistantModule(ctx)
    widget = module.get_widget()  # keep a reference so Qt does not delete it
    monkeypatch.setattr(module, "_speak", lambda text: None)
    module._input.setText("I want to end my life")
    module._on_send()
    conversation = ctx.conversations.get_or_create_active_conversation()
    assert "988" in conversation.messages[-1].content
    assert module._worker is None
    del widget
