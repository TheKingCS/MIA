"""
core.specialist_models
========================

Which local model does each specialist's thinking (T1's second part; the local specialists plan, S3; DEC-0197:
"the model per specialist is chosen from this table, not from a guide"). The table is the engineering bench's
results on this PC (`work/eng_bench/<model>.json`, written by `python -m tools.eng_bench`).

**How a model is chosen** (`choose`): a specialist works through the worksheet, so only the bench's "tools" mode
counts (the model choosing calculators, code computing). For each benched model, its results on the disciplines
the specialist's worksheet uses (`core.specialist_work.DISCIPLINES`) are added up: the share it got good (right,
or asked for what was missing) and how often it **guessed** an input it wasn't given, the dangerous failure. The
best is the one benched on the most of those disciplines, then the fewest guesses (a guessed input can't be seen in
the answer, where a wrong pick of calculator can), then the highest share, then the fastest. It **passes** at `PASS` with no guess and every discipline benched; one
below is still the best this PC has, and the worksheet says so on its answer rather than pretend otherwise. A
specialist whose disciplines no model has been benched on, or a PC with no results at all, uses MIA's everyday
model, and says that too.

**Asking the chosen model** (`asker`): only where MIA's model is this machine's own Ollama (the PC; not the phone
or a linked home computer, whose models are their own), a backend for the chosen model, at temperature 0, with a
thinking model's thinking off and its reply capped. Elsewhere, MIA's everyday model.

Pure logic over the results, plus one read of the folder.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.data_root import WORK_DIR
from core.logger import get_logger

log = get_logger(__name__)

RESULTS = WORK_DIR / "eng_bench"
PASS = 0.8
MODE = "tools"  # how a specialist really works: the model picks calculators, code computes
MAX_TOKENS = 3072
TIMEOUT = 300.0


@dataclass(frozen=True)
class Choice:
    """The model for a specialist and why: `model` is None when MIA's everyday model is used; `passed` whether the
    chosen model reached PASS with no guess; the totals it was judged on; and `why`, in words for the person."""
    model: Optional[str]
    passed: bool
    good: float = 0.0
    tasks: int = 0
    guessed: int = 0
    seconds: float = 0.0
    why: str = ""


def load(folder: Path = RESULTS) -> dict[str, dict]:
    """Each benched model's summary ({model: {mode: {discipline: counts}}}); an unreadable file is left out."""
    out = {}
    for path in sorted(Path(folder).glob("*.json")) if Path(folder).is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            out[str(data["model"])] = data["summary"]
        except (OSError, ValueError, KeyError, TypeError):
            log.warning("Bench results %s couldn't be read", path.name)
    return out


def _totals(summary: dict, disciplines: tuple) -> Optional[tuple[int, int, int, float, int]]:
    """Pure logic. (tasks, good, guessed, mean seconds, how many of the disciplines it was benched on) over the
    disciplines in a model's tools-mode summary, or None when it wasn't benched on any of them."""
    cells = [summary.get(MODE, {}).get(d) for d in disciplines]
    cells = [c for c in cells if c]
    if not cells:
        return None
    tasks = sum(c["tasks"] for c in cells)
    good = sum(c.get("right", 0) + c.get("asked", 0) for c in cells)
    seconds = sum(c.get("seconds", 0.0) * c["tasks"] for c in cells) / tasks
    return tasks, good, sum(c.get("guessed", 0) for c in cells), round(seconds, 2), len(cells)


def choose(specialist_id: str, results: Optional[dict] = None) -> Choice:
    """Pure logic over the results (this PC's, unless given). The model for a specialist (see the module's
    opening)."""
    from core.specialist_work import DISCIPLINES

    disciplines = DISCIPLINES.get(specialist_id, ())
    results = load() if results is None else results
    scored = []
    for model, summary in results.items():
        found = _totals(summary, disciplines)
        if found:
            tasks, good, guessed, seconds, covered = found
            scored.append((covered, -guessed, good / tasks, -seconds, model, found))
    if not scored:
        why = ("no model on this PC has been benched on this work yet, so it uses my everyday model"
               if results else "this PC has no bench results yet, so it uses my everyday model")
        return Choice(None, False, why=why)
    covered, _g, share, _s, model, (tasks, good, guessed, seconds, _c) = max(scored)
    passed = share >= PASS and guessed == 0 and covered == len(disciplines)
    said = f"{model} got {good} of {tasks} of the bench's problems for this work right"
    said += f" and guessed {guessed} time{'s' if guessed != 1 else ''} when something was missing" if guessed else ""
    if covered < len(disciplines):
        said += "; it hasn't been benched on all of this work yet"
    elif not passed:
        said += f"; it's the best on this PC, but below the {PASS:.0%} with no guessing a specialist should reach"
    return Choice(model, passed, round(share, 3), tasks, guessed, seconds, said)


def table(results: Optional[dict] = None) -> list[dict]:
    """Every specialist with a worksheet and the model it gets: {"specialist", "name", "model", "passed", "why"}."""
    from core.specialist_work import DISCIPLINES
    from core.specialists import BY_ID

    results = load() if results is None else results
    rows = []
    for sid in DISCIPLINES:
        pick = choose(sid, results)
        rows.append({"specialist": sid, "name": BY_ID[sid].name if sid in BY_ID else sid, "model": pick.model,
                     "passed": pick.passed, "why": pick.why})
    return rows


def asker(context, choice: Choice) -> Optional[Callable[[str], str]]:
    """`ask(prompt) -> text` on the chosen model, where MIA's model is this machine's own Ollama; None otherwise
    (then the everyday model answers)."""
    if choice.model is None:
        return None
    from core.llm_manager import OllamaBackend

    llm = getattr(context, "llm", None)
    backend = getattr(llm, "_backend", None)
    if not isinstance(backend, OllamaBackend) or getattr(llm, "home", None) is not None:
        return None
    chosen = OllamaBackend(backend._base_url, choice.model, "10m", 0.0, think=False, num_predict=MAX_TOKENS)

    def ask(prompt: str) -> str:
        """One question to the specialist's own model."""
        return chosen.generate(prompt, TIMEOUT)
    return ask
