"""Markdown out of what MIA says (core/plain_words.py)."""

from core.plain_words import for_speech, strip_markdown
from core.voice_manager import prepare_text_for_speech


def test_the_screen_loses_the_markers_not_the_words():
    said = "### **Making Products to Order**\n**Pros:**\n- **Lower costs:** no stock\n* Less waste\n\n---\nUse `Garage Rewire`."
    assert strip_markdown(said) == "Making Products to Order\nPros:\n- Lower costs: no stock\n- Less waste\n\nUse Garage Rewire."
    assert strip_markdown("2 * 3 = 6, and 4*5") == "2 * 3 = 6, and 4*5"  # arithmetic isn't italics


def test_the_voice_hears_sentences():
    assert for_speech("**Pros:**\n- Lower costs\n- Less waste") == "Pros: Lower costs. Less waste."
    assert prepare_text_for_speech("**MIA** says hi") == "Mia says hi"
