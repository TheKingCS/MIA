"""What I Used (DEC-0029, ALICE pick 1): a turn gets the memories that
match what was asked, returns them with the reply, and each can be fixed
or forgotten (and the forgetting undone)."""

from core.assistant_chat import turn_memories
from core.assistant_turn import run_assistant_turn
from core.conversation_manager import Conversation
from core.llm_manager import ChatReply
from core.user_memory_manager import UserMemory, memory_relevance, relevant_memories
from core.user_memory_manager import UserMemoryManager
from tests.engine_world import build_world


def mem(i, text, when="2026-10-01"):
    return UserMemory(memory_id=str(i), text=text, created_at=when)


def test_relevance():
    jordan = mem(1, "The user's sister Jordan loves climbing.")
    mower = mem(2, "The user's mower blade was dull last spring.", "2026-10-05")
    coffee = mem(3, "The user drinks iced coffee.", "2026-10-09")
    assert memory_relevance("what should I get jordan for her birthday", jordan) == 2  # a name counts double
    assert memory_relevance("hi mia how are you", jordan) == 0  # question words never match
    assert [m.memory_id for m in relevant_memories("is my mower due for blades?", [jordan, mower, coffee])] == ["2"]
    assert relevant_memories("hello there", [jordan, mower, coffee]) == []


class _Model:
    def __init__(self):
        self.seen = None

    def chat_with_tools(self, messages, tools):
        self.seen = messages
        return ChatReply(content="Maybe a new chalk bag.", tool_calls=[])

    def generate(self, prompt):
        return "NONE"


def test_a_turn_says_what_it_used_and_memories_can_be_fixed_or_forgotten(tmp_path, monkeypatch):
    from core.actions import ActionCenter

    world = build_world(tmp_path, monkeypatch)
    world.user_memories = UserMemoryManager(world, data_dir=tmp_path / "mem")
    jordan = world.user_memories.add_memory("The user's sister Jordan loves climbing.", "Relationships")
    world.user_memories.add_memory("The user drinks iced coffee.", "Preferences")
    world.llm = _Model()
    world.assistant_actions = world.device_help = None
    turn = run_assistant_turn(world, Conversation(conversation_id="c1", title="New Conversation"),
                              "What should I get Jordan for her birthday?")
    assert [u["text"] for u in turn.used] == ["The user's sister Jordan loves climbing."]
    system = world.llm.seen[0]["content"]
    assert "Jordan loves climbing" in system and "iced coffee" not in system  # only what matters
    # Nothing matches: a few recent memories, still shown honestly.
    assert {m.text for m in turn_memories(world, "hello")} == {m.text for m in world.user_memories.all_memories()}

    world.actions = ActionCenter()
    p = world.actions.propose(world, "memory.fix", {"memory_id": jordan.memory_id, "text": "The user's sister Jordan loves bouldering."})
    assert p.summary == "Change what MIA remembers to: The user's sister Jordan loves bouldering."
    world.actions.approve(world, p.proposal_id)
    assert world.user_memories.get_memory(jordan.memory_id).text.endswith("bouldering.")
    p = world.actions.propose(world, "memory.forget", {"memory_id": jordan.memory_id})
    assert p.summary.startswith("Forget: The user's sister Jordan")
    world.actions.approve(world, p.proposal_id)
    assert world.user_memories.get_memory(jordan.memory_id) is None
    world.actions.undo(world, p.proposal_id)
    assert world.user_memories.get_memory(jordan.memory_id) is not None  # forgetting can be undone
