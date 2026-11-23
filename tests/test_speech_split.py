"""
tests.test_speech_split
=========================

Her first words sooner (core/speech_split.py, brainstorm 1.1(c)): the first sentence voiced first, the rest a part at a
time while it plays, never cut mid-sentence; only for a page that asks (the phone app keeps the whole audio).
"""

from pathlib import Path

from core import speech_split as ss

ROOT = Path(__file__).resolve().parent.parent
LONG = ("Your tomatoes are in the ground and tonight drops to 31°F. Cover them before dark with sheets or buckets, "
        "and water the soil this afternoon so it holds its warmth. Take the covers off once the sun is up. The peppers "
        "can wait inside one more week; 2.5 inches of mulch helps too.")


def test_a_short_answer_is_said_in_one_go():
    assert ss.first_part("Done. I added it.") == ("Done. I added it.", "")
    assert ss.first_part("x" * 300) == ("x" * 300, "")  # one long sentence: nothing to split


def test_a_long_answer_splits_after_its_first_sentence():
    first, rest = ss.first_part(LONG)
    assert first == "Your tomatoes are in the ground and tonight drops to 31°F."
    assert rest.startswith("Cover them before dark") and rest.endswith("mulch helps too.")
    assert f"{first} {rest}" == " ".join(LONG.split())


def test_a_very_short_opening_takes_the_next_sentence_with_it():
    first, _rest = ss.first_part("Yes. " + LONG)
    assert first.startswith("Yes. Your tomatoes")


def test_decimals_and_abbreviations_are_never_a_sentence_end():
    assert ss.sentences("Use 2.5 inches, e.g. straw. Then water.") == ["Use 2.5 inches, e.g. straw.", "Then water."]


def test_only_a_page_that_asks_gets_the_split():
    app = (ROOT / "server" / "app.py").read_text(encoding="utf-8")
    assert "split: bool = False" in app and '"audio_rest_text": rest' in app
    mia = (ROOT / "web" / "mia.js").read_text(encoding="utf-8")
    assert '"/api/voice/turn" + (opts && opts.split ? "?split=1" : "")' in mia
    shell = (ROOT / "web" / "shell.js").read_text(encoding="utf-8")
    assert "MIA.voice(audio, { split: true })" in shell and "turn.audio_rest_text" in shell
