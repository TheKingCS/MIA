"""Sight (build plan step 15, core/sight.py): a photo and a question, answered on the PC: reading tries Tesseract
first (its words are exactly what's printed), the vision model's judgment is said as one, a person is never
identified, and only the kind and timing of each look are kept.
And a part in a photo tied to its spec."""

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
    """A stand-in person with a failure log folder and no config."""
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


def test_a_part_in_a_photo_is_tied_to_its_spec_or_how_to_get_one():
    """The answer names an HC-SR04: its spec follows, said as "if it's"; an unknown board asked about as a part: how to
    have its specs looked up; a mug: nothing added."""
    from types import SimpleNamespace

    from core import sight

    context = SimpleNamespace(config=None)
    known = sight.look(context, b"x", "what part is this?", ask=lambda m, p, i: "A module marked HC-SR04.")["said"]
    assert "If it's the HC-SR04 ultrasonic sensor, I know its spec" in known and "4.5 to 5.5 V" in known
    unknown = sight.look(context, b"x", "what part is this?", ask=lambda m, p, i: "A board marked ZX-1234.")["said"]
    assert "look up the specs for" in unknown
    assert sight.look(context, b"x", "what is this?", ask=lambda m, p, i: "A coffee mug.")["said"] == \
        "From the photo: A coffee mug."
