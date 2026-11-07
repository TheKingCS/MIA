"""
core.guitar_ear
=================

How MIA hears a guitar (DEC-0111): a recording, worked out in code, so a skill
check can be passed by playing it, not only by saying so. The same rule she
keeps for herself: a skill counts when it's shown.

- `read_wav()`: a WAV recording (16-bit PCM, mono or stereo) as samples and a
  rate. The web and phone record WAV for this.
- `pitch()`: the note a single string is playing, by autocorrelation over a
  guitar's range (about 70 to 1,000 Hz), as a frequency. `note_of()` names it
  (A2, E4) with how many cents sharp or flat: the tuner.
- `chroma()`: how much of each of the twelve pitch classes a recording holds,
  from its spectrum (each partial folded onto its note). `hear_chord()` says
  which of a chord's notes rang, which didn't, and which other notes were
  loud (a buzz, a wrong string).

What it can't do, said plainly: it hears notes, not technique. A chord can
ring with every note and still be played with the wrong fingers; a muted
string that should be muted is silent either way. It's a check that the
right sounds came out, and a person (or the next check) covers the rest.
Thresholds are deliberately forgiving, so a real guitar on a phone's
microphone passes when it should; a check heard this way says "heard".
"""

from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Iterable, Optional

NOTES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
A4 = 440.0
LOW_HZ, HIGH_HZ = 70.0, 1000.0
CHORD_TONE = 0.25  # a chord tone rang when its pitch class has at least this share of the loudest one
STRAY = 0.35  # a note outside the chord this loud (against the loudest) is a wrong note or a buzz
# Set on synthesized strings (2026-11-07): clean open chords' overtones reach 0.21 outside the chord, a wrong
# string 0.43 or more, and the quietest chord tone 0.33. Real recordings may move them; adjust from those.
STANDARD_TUNING = (("E", 2), ("A", 2), ("D", 3), ("G", 3), ("B", 3), ("E", 4))


class EarError(ValueError):
    """A recording that can't be heard (not a WAV MIA reads, silent, too short)."""


def read_wav(source) -> tuple[list[float], int]:
    """A WAV file (a path or a file object) as mono samples between -1 and 1, and its sample rate; EarError for a
    format it doesn't read (only 16-bit PCM)."""
    try:
        with wave.open(str(source) if isinstance(source, (str, Path)) else source, "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(frames)
    except (wave.Error, EOFError, OSError) as problem:
        raise EarError(f"That recording couldn't be read ({problem}).") from None
    if width != 2:
        raise EarError("Record it as 16-bit WAV.")
    import numpy as np

    data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data.tolist(), rate


def _array(samples):
    """The samples as a numpy array, with the quiet start and end trimmed off; EarError when there's nothing loud
    enough to hear, or under a tenth of a second."""
    import numpy as np

    x = np.asarray(samples, dtype=np.float64)
    if x.size == 0 or float(np.max(np.abs(x))) < 0.01:
        raise EarError("I couldn't hear anything in that recording.")
    loud = np.nonzero(np.abs(x) > 0.05 * float(np.max(np.abs(x))))[0]
    return x[loud[0]:loud[-1] + 1]


def pitch(samples: Iterable[float], rate: int) -> float:
    """The frequency of the note a single string plays, by autocorrelation over a guitar's range, refined between
    samples; EarError when no steady note is there."""
    import numpy as np

    x = _array(samples)
    x = x[: int(rate * 0.5)] if x.size > rate * 0.5 else x  # half a second is plenty for one note
    if x.size < rate * 0.05:
        raise EarError("That's too short to hear a note.")
    x = x - x.mean()
    spectrum = np.fft.rfft(x, n=2 * x.size)
    corr = np.fft.irfft(spectrum * np.conj(spectrum))[: x.size]
    lo, hi = int(rate / HIGH_HZ), min(int(rate / LOW_HZ), x.size - 2)
    if hi <= lo or corr[0] <= 0:
        raise EarError("I couldn't find a steady note.")
    window = corr[lo:hi]
    best = int(np.argmax(window)) + lo
    if corr[best] < 0.3 * corr[0]:
        raise EarError("I couldn't find a steady note.")
    # An octave error guard: a strong peak at half the lag is the real note.
    half = best // 2
    if half >= lo and corr[half] > 0.85 * corr[best]:
        best = half
    a, b, c = corr[best - 1], corr[best], corr[best + 1]
    shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    return rate / (best + shift)


def note_of(freq: float) -> tuple[str, int, float]:
    """Pure logic. A frequency as (note, octave, cents off): 110 Hz is ("A", 2, 0.0); positive cents are sharp."""
    if freq <= 0:
        raise EarError("That isn't a note.")
    semis = 12 * math.log2(freq / A4) + 57  # semitones from C0
    nearest = round(semis)
    return NOTES[nearest % 12], nearest // 12, round(100 * (semis - nearest), 1)


def freq_of(note: str, octave: int) -> float:
    """Pure logic. A note's frequency in equal temperament (A4 = 440 Hz)."""
    return A4 * 2 ** ((NOTES.index(note) + 12 * octave - 57) / 12)


def tuning(freq: float, string: int) -> dict:
    """Pure logic. How a string (6 is the low E, 1 the high E) is tuned against standard tuning: its target, the
    note heard, and cents sharp (positive) or flat; within 10 cents is in tune."""
    target_note, target_octave = STANDARD_TUNING[6 - string]
    target = freq_of(target_note, target_octave)
    cents = round(1200 * math.log2(freq / target), 1)
    heard = note_of(freq)
    return {"string": string, "target": f"{target_note}{target_octave}", "heard": f"{heard[0]}{heard[1]}",
            "cents": cents, "in_tune": abs(cents) <= 10}


def chroma(samples: Iterable[float], rate: int) -> list[float]:
    """How much of each pitch class (C to B) a recording holds, from its spectrum between 70 Hz and 2 kHz, each
    peak's strength folded onto its note (by magnitude, not energy,
    so one string isn't drowned by three); scaled so the loudest is 1."""
    import numpy as np

    x = _array(samples)
    x = x[: int(rate * 2)] if x.size > rate * 2 else x
    x = (x - x.mean()) * np.hanning(x.size)
    mags = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(x.size, 1 / rate)
    keep = (freqs >= LOW_HZ) & (freqs <= 2000)
    out = np.zeros(12)
    floor = 0.05 * float(mags[keep].max()) if keep.any() else 0.0
    for f, m in zip(freqs[keep], mags[keep]):
        if m > floor:
            out[int(round(12 * math.log2(f / A4) + 57)) % 12] += m
    top = float(out.max())
    return [round(float(v / top), 3) for v in out] if top > 0 else [0.0] * 12


def hear_chord(levels: list[float], notes: Iterable[str]) -> dict:
    """Pure logic. Against a chord's notes: which rang (at least CHORD_TONE of the loudest), which were missing,
    which notes outside the chord were loud (over STRAY), and whether it passes: every chord tone rang and
    nothing stray was loud."""
    wanted = [n for n in notes]
    rang = [n for n in wanted if levels[NOTES.index(n)] >= CHORD_TONE]
    missing = [n for n in wanted if n not in rang]
    stray = [NOTES[i] for i, v in enumerate(levels) if NOTES[i] not in wanted and v >= STRAY]
    return {"rang": rang, "missing": missing, "stray": stray, "passed": not missing and not stray}


def describe_chord(name: str, heard: dict) -> str:
    """Pure logic. What MIA heard of a chord, said plainly."""
    if heard["passed"]:
        return f"That's a clean {name}: every note rang ({', '.join(heard['rang'])})."
    bits = []
    if heard["missing"]:
        bits.append(f"I didn't hear {', '.join(heard['missing'])}: a string may be muted by a finger or not pressed "
                    "hard enough")
    if heard["stray"]:
        bits.append(f"I heard {', '.join(heard['stray'])}, which isn't in {name}: a wrong fret, an open string that "
                    "should be muted, or a buzz")
    return f"Not quite a clean {name} yet. " + "; ".join(bits) + "."


def synth(freqs: Iterable[float], rate: int = 22050, seconds: float = 1.0, harmonics: int = 5) -> list[float]:
    """Pure logic. A plucked-string-like sound of the given notes (each with decaying harmonics), for tests and for
    hearing what a chord should sound like."""
    import numpy as np

    t = np.arange(int(rate * seconds)) / rate
    out = np.zeros_like(t)
    for f in freqs:
        for h in range(1, harmonics + 1):
            out += (0.6 ** (h - 1)) * np.sin(2 * math.pi * f * h * t) * np.exp(-2.0 * t)
    peak = float(np.max(np.abs(out))) or 1.0
    return (0.8 * out / peak).tolist()


def heard_note(samples, rate: int) -> Optional[tuple[str, int, float]]:
    """The note a recording holds, named, or None when no steady note is there."""
    try:
        return note_of(pitch(samples, rate))
    except EarError:
        return None
