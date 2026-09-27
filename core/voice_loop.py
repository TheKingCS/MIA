"""
core.voice_loop
=================

The headless Core runtime's actual voice loop: push-to-talk -> transcribe
-> Assistant -> speak — docs/VISION.md's 2026-07-15 "Core drops its GUI
entirely" sharpening, the piece it explicitly flagged as "not built yet,
and genuinely substantial when it is."

Runs as one blocking, single-threaded loop, not a QThread/Qt-signal
pipeline like `modules/assistant/module.py`'s GUI equivalent — there's
no GUI responsiveness to protect here (see `core/core_runtime.py`'s
docstring on why this whole runtime stays Qt-free), and a personal
voice companion is inherently one-turn-at-a-time anyway. Mirrors that
GUI version's real, already-tested pipeline stage for stage
(`context.voice.start_recording()` -> `.stop_recording()` ->
`.transcribe()` -> `core.assistant_chat.build_chat_request()` ->
`context.llm.chat_with_tools()` -> `split_safe_tool_calls()` ->
`context.assistant_actions.execute()` -> `context.voice.synthesize()` +
`.play()`), reusing every one of those exact functions rather than
reimplementing the decision logic. The turn itself (2026-09-27) lives in
`core/assistant_turn.py`, shared with the phone voice endpoint.

Conversation history is in-memory only, for the life of one process —
deliberately not `core/conversation_manager.py`'s disk-persisted,
titled, browsable conversation list, since that's a "chat log UI"
concept with no screen to browse it on here. Still real multi-turn
context within a boot session (`build_chat_request()` takes the same
`Conversation`/`ConversationMessage` dataclasses either way), just
reset on restart rather than saved. Auto-titling
(`build_title_generation_prompt()`) is skipped for the same
no-conversation-list-UI reason; memory extraction
(`build_memory_extraction_prompt()`) is kept, since personalization is
useful whether or not there's a screen.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.assistant_turn import run_assistant_turn, run_followup
from core.conversation_manager import Conversation
from core.logger import get_logger
from core.push_to_talk_source import PushToTalkSource
from core.receiver_indicators import ReceiverIndicators

log = get_logger(__name__)

_MIC_UNAVAILABLE = "Voice input isn't available right now."
_STT_UNAVAILABLE = "I couldn't understand that — speech-to-text isn't available right now."
_LLM_UNAVAILABLE = "The Assistant's language model isn't available right now."


class VoiceLoopController:
    """Drives one push-to-talk turn at a time until `stop()` is called."""

    def __init__(
        self,
        context: AppContext,
        push_to_talk: PushToTalkSource,
        indicators: ReceiverIndicators,
    ) -> None:
        self.context = context
        self._push_to_talk = push_to_talk
        self._indicators = indicators
        self._conversation = Conversation(conversation_id="core-session")
        self._running = False

    def stop(self) -> None:
        self._running = False

    def run_forever(self) -> None:
        """Blocks, running turns until `stop()` is called (e.g. from a signal handler)."""
        self._running = True
        while self._running:
            self.run_one_turn()

    def run_one_turn(self) -> None:
        """Runs exactly one press -> speak cycle. Public so tests/verification scripts can drive it directly."""
        self._indicators.on_idle()
        self._push_to_talk.wait_for_press()

        if self.context.voice is None or not self.context.voice.start_recording():
            log.warning(_MIC_UNAVAILABLE)
            return
        self._indicators.on_listening()
        self._push_to_talk.wait_for_release()

        wav_path = self.context.voice.stop_recording()
        if wav_path is None:
            log.warning(_MIC_UNAVAILABLE)
            return

        transcript = self.context.voice.transcribe(wav_path)
        if not transcript:
            log.warning(_STT_UNAVAILABLE)
            return

        log.info("Heard: %s", transcript)
        self._indicators.on_thinking()
        self._handle_turn(transcript)

    def _handle_turn(self, prompt: str) -> None:
        turn = run_assistant_turn(self.context, self._conversation, prompt)
        for text in turn.replies:
            self._speak(text)
        if not turn.llm_available:
            log.warning(_LLM_UNAVAILABLE)
            return
        run_followup(self.context, self._conversation, turn.followup)

    def _speak(self, text: str) -> None:
        self._indicators.on_speaking()
        log.info("Saying: %s", text)
        if self.context.voice is None:
            return
        import tempfile
        from pathlib import Path

        output_path = Path(tempfile.gettempdir()) / "mia_core_reply.wav"
        synthesized = self.context.voice.synthesize(text, output_path)
        if synthesized is not None:
            self.context.voice.play(synthesized)
