"""
core.response_style
======================

Learning how the person likes MIA to answer (DEC-0138): now and then she offers the *same* answer two ways — "do you
prefer this response, or this one?" — differing on one dimension of style (how long, how it's laid out, its tone,
whether it leads with the answer). The person picks; MIA records it and adjusts, so over time she settles into the way
they like to be talked to. The facts never change — only the phrasing and layout (CLAUDE.md: "the model phrases").

This module is the learning core: the per-person store of picks, the current preferred style it derives, how sure it
is on each dimension, which dimension to experiment on next, and a plain-words style instruction for the phrasing
layer to follow. Generating the two variants (the model rendering the same facts two ways) and showing the A/B choice
are the surface's job; this decides *what* to compare and *what was learned*.

A personal store (`response_styles.json`), sealed at rest (DEC-0126). Nothing here is fiction, so events are real.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import life_events
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "response_styles.json"
_KEEP = 500  # the most recent picks kept per person

# Each dimension of how MIA answers, with its options (the first is the neutral default).
DIMENSIONS: dict[str, tuple[str, ...]] = {
    "length": ("standard", "brief", "detailed"),
    "format": ("mixed", "prose", "bulleted"),
    "tone": ("warm", "neutral", "direct"),
    "lead": ("answer_first", "context_first"),
}
DEFAULTS = {dim: options[0] for dim, options in DIMENSIONS.items()}

# How each value reads in a style instruction to the phrasing layer.
DESCRIPTIONS = {
    ("length", "brief"): "keep it short — a sentence or two",
    ("length", "standard"): "a normal, complete length",
    ("length", "detailed"): "thorough, with the detail",
    ("format", "prose"): "in flowing prose",
    ("format", "bulleted"): "laid out as bullet points",
    ("format", "mixed"): "a line of prose then bullets where they help",
    ("tone", "warm"): "a warm, friendly tone",
    ("tone", "neutral"): "a plain, neutral tone",
    ("tone", "direct"): "a direct, no-preamble tone",
    ("lead", "answer_first"): "lead with the answer, then the why",
    ("lead", "context_first"): "give the context first, then the answer",
}


@dataclass
class Pick:
    """One A/B choice: which dimension was tested, the value chosen over the one rejected, and when."""

    dimension: str
    chosen: str
    rejected: str
    at: str

    def to_dict(self) -> dict:
        """As a plain dict for JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Pick":
        """From a stored dict, tolerant of missing keys."""
        return Pick(dimension=d.get("dimension", ""), chosen=d.get("chosen", ""),
                    rejected=d.get("rejected", ""), at=d.get("at", ""))


class StyleBook:
    """A person's answer-style preferences (response_styles.json): the picks they've made and the style MIA derives."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Points at the person's response_styles.json (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE if data_dir is not None else _DATA_DIR / _FILE
        self.picks: list[Pick] = []
        self._load()

    def _load(self) -> None:
        """Reads the picks; a missing file starts empty, a sealed one that won't open is set aside (DEC-0126)."""
        try:
            raw = json.loads(open_text(self._file))
        except FileNotFoundError:
            return
        except (ValueError, OSError):
            log.exception("Couldn't read response_styles.json — starting empty.")
            return
        self.picks = [Pick.from_dict(d) for d in raw.get("picks", [])]

    def _save(self) -> None:
        """Writes the picks atomically (undoable), newest-trimmed, sealed at rest."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"picks": [p.to_dict() for p in self.picks[-_KEEP:]]},
                                                 indent=1, ensure_ascii=False))

    # ------------------------------------------------------------------ record

    def record_pick(self, dimension: str, chosen: str, rejected: str = "") -> Pick:
        """Record that the person preferred `chosen` over `rejected` on `dimension` (ValueError for an unknown
        dimension or value)."""
        if dimension not in DIMENSIONS:
            raise ValueError(f"Dimension is one of {tuple(DIMENSIONS)}.")
        if chosen not in DIMENSIONS[dimension] or (rejected and rejected not in DIMENSIONS[dimension]):
            raise ValueError(f"Values for {dimension} are {DIMENSIONS[dimension]}.")
        pick = Pick(dimension=dimension, chosen=chosen, rejected=rejected,
                    at=datetime.now().isoformat(timespec="seconds"))
        self.picks.append(pick)
        self._save()
        life_events.record(self, "style_pick", f"Prefers {chosen} over {rejected or 'the other'} ({dimension})",
                           [f"style:{dimension}"])
        return pick

    # ------------------------------------------------------------------ what she learned

    def tally(self, dimension: str) -> Counter:
        """How often each value of a dimension was chosen (recent picks only)."""
        return Counter(p.chosen for p in self.picks if p.dimension == dimension)

    def preferred(self, dimension: str) -> str:
        """The person's current preferred value for a dimension — the most-chosen, or the default with no picks yet."""
        counts = self.tally(dimension)
        return counts.most_common(1)[0][0] if counts else DEFAULTS[dimension]

    def confidence(self, dimension: str) -> float:
        """How settled a dimension is, 0–1: the lead of the top value over the rest, by share of its picks (0 with no
        picks)."""
        counts = self.tally(dimension)
        total = sum(counts.values())
        if not total:
            return 0.0
        top = counts.most_common(1)[0][1]
        return (2 * top - total) / total  # 1.0 when all picks agree, 0 when evenly split

    def profile(self) -> dict:
        """The current preferred value on every dimension."""
        return {dim: self.preferred(dim) for dim in DIMENSIONS}

    def next_experiment(self) -> dict:
        """What to A/B next: the least-settled dimension, the preferred value vs. the least-tried challenger, so she
        keeps learning where she's unsure."""
        dim = min(DIMENSIONS, key=lambda d: (len([p for p in self.picks if p.dimension == d]), self.confidence(d)))
        counts = self.tally(dim)
        keep = self.preferred(dim)
        challenger = min((v for v in DIMENSIONS[dim] if v != keep), key=lambda v: counts.get(v, 0))
        return {"dimension": dim, "a": keep, "b": challenger}

    def style_instruction(self) -> str:
        """A plain-words instruction for the phrasing layer to answer the way the person likes, e.g. 'Answer: keep it
        short…; lead with the answer…'. Only names a dimension once there's a pick for it, so it never over-claims."""
        parts = [DESCRIPTIONS[(dim, self.preferred(dim))] for dim in DIMENSIONS if self.tally(dim)]
        return "Answer: " + "; ".join(parts) + "." if parts else "Answer in your normal style."
