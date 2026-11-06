"""Sight (build plan step 15, core/sight.py): a photo and a question, answered on the PC: reading tries Tesseract
first (its words are exactly what's printed), the vision model's judgment is said as one, a person is never
identified, and only the kind and timing of each look are kept."""

from types import SimpleNamespace

import pytest

from core import loops, sight

BY_ID = {l.id: l for l in loops.LOOPS}
PHOTO = b"\xff\xd8\xff\xe0fake-jpeg"


def test_what_kind_of_looking():
    assert sight.kind_of("what is this?") == sight.WHAT
    assert sight.kind_of("read this label") == sight.READ and sight.kind_of("what does it say") == sight.READ
    assert sight.kind_of("inspect this part") == sight.INSPECT and sight.kind_of("is this belt worn?") == sight.INSPECT
    assert sight.refuses("who is this?") and sight.refuses("recognize this person") and not sight.refuses("what is this")


@pytest.fixture
def person(tmp_path):
    return SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path), config=None)


def test_reading_tries_tesseract_first(person):
    asked = []
    said = sight.look(person, PHOTO, "read this label", ask=lambda *a: asked.append(a) or "x",
                      read_text=lambda img: "CAUTION\nHot surface")
    assert said["said"] == "It says:\nCAUTION\nHot surface" and said["how"] == "read" and asked == []
    model = sight.look(person, PHOTO, "read this", ask=lambda m, p, i: "Hot surface", read_text=lambda img: "")
    assert model["how"] == "vision model" and model["said"] == "Hot surface"


def test_a_judgment_is_said_as_one_and_people_are_never_identified(person):
    seen = {}

    def ask(model, prompt, image):
        seen.update(model=model, prompt=prompt, image=image)
        return "A serpentine belt with cracks across several ribs."
    out = sight.look(person, PHOTO, "inspect this part", ask=ask)
    assert out["said"].startswith("From the photo: ") and seen["image"] == PHOTO and seen["model"] == sight.MODEL
    assert "Never identify a person" in seen["prompt"] and "inspect this part" in seen["prompt"]
    refused = sight.look(person, PHOTO, "who is this?", ask=lambda *a: pytest.fail("never asked"))
    assert refused["said"] == sight.NO_FACES


def test_what_it_wont_or_cant_do(person):
    with pytest.raises(sight.SightError, match="No photo"):
        sight.look(person, b"")
    with pytest.raises(sight.SightError, match="aren't answering"):
        sight.look(person, PHOTO, "what is this", ask=lambda *a: (_ for _ in ()).throw(OSError("connection refused")))


def test_only_the_kind_and_timing_are_kept_and_the_loop_reads_them(person, tmp_path):
    for _ in range(4):
        sight.look(person, PHOTO, "what is this", ask=lambda *a: "A garden trowel.")
    with pytest.raises(sight.SightError):
        sight.look(person, PHOTO, "what is this", ask=lambda *a: "")
    kept = (tmp_path / "sight_log.jsonl").read_text(encoding="utf-8")
    assert "trowel" not in kept and "fake-jpeg" not in kept
    reading = BY_ID["sight.failed"].measure(person)
    assert (reading.value, reading.n) == (0.2, 5)
