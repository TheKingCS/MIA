"""
core.model_forge
==================

MIA's model forge (DEC-0106, stage 1): where she trains small models of her
own, measures them honestly, and keeps a card saying what each one is.

Zac, 2026-11-07: "I want her capable of building a custom AI ... based on her
own infrastructure and research ... custom building similar or different AI
models." Training a large model from scratch takes a data center; small
specialist models, trained on her own records, run on any of her devices.
This file is where that starts.

**The first model: a tool router.** Given what someone said, which of her
tools fit? Today the keyword router (core/assistant_actions.py) decides by
trigger phrases and domain words, tuned by hand. This model learns the same
job from the tools' **own words only**: each tool's name, description,
trigger phrases and subjects (`examples_from_actions()`). It's then tested
on requests it never saw (the routing corpus, real things people said),
so its score is honest.

- **The model** (`Router`): softmax regression over word stems and word
  pairs, trained by full-batch gradient descent with numpy (no other
  library, no randomness, so the same data always makes the same model).
  Small enough to run on the phone.
- **The measure** (`evaluate()`): top-1 and top-k on the held-out
  requests, and which ones it missed. Requests answered from the help docs
  (no tool) are left out: the router only picks tools. The held-out
  requests are split in two (`split()`): a few training settings are tried
  and the best on one half is kept, and the score on the card comes from
  the other half, which chose nothing. (Picking settings by the same
  requests that give the score would flatter it: a lesson from building
  this, K-0045.)
- **The card** (`card.json` beside the weights in `data/models/<name>/`):
  what it is, what it was trained on, what it was tested on, its scores,
  the keyword router's on the same requests, and when. A model with no
  card isn't kept.

**Nothing uses it yet.** It isn't wired into her answers: the keyword
router was tuned on these same requests, so beating it here proves
nothing. The next stage runs it in the shadow on new requests (the Fix-It
Log's misses first), and it goes in only when it wins there and Zac
approves.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from core.atomic_write import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "data" / "models"
_WORD = re.compile(r"[a-z0-9']+")
_STOP = {"a", "an", "the", "to", "of", "and", "or", "is", "are", "my", "me", "i", "it", "for", "in", "on", "do",
         "does", "what", "how", "can", "you", "your", "this", "that", "with", "be", "s"}
_SUFFIXES = ("ings", "ing", "ies", "ed", "es", "s")


def _stem(word: str) -> str:
    """Pure logic. A crude stem, so "logged" and "logs" meet "log"."""
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def features(text: str) -> list[str]:
    """Pure logic. What the model sees of a text: its word stems (common little words left out) and each pair of
    neighbouring words, so "pay off" isn't just "pay"."""
    words = [w.replace("'", "") for w in _WORD.findall((text or "").lower().replace("_", " "))]
    stems = [_stem(w) for w in words if w and w not in _STOP]
    pairs = [f"{a}_{b}" for a, b in zip(stems, stems[1:])]
    return stems + pairs


@dataclass
class Example:
    """One thing to learn from or be tested on: some words, and the tool they mean."""
    text: str
    label: str


def examples_from_actions(actions: Iterable) -> list[Example]:
    """The training set from the tools themselves: each tool's name (as words), description, trigger phrases and
    subjects, each an example of that tool. Nothing a person said is in it."""
    out = []
    for a in actions:
        texts = [a.name.replace("_", " "), a.description, *getattr(a, "trigger_phrases", ()),
                 *getattr(a, "subjects", ())]
        out.extend(Example(t, a.name) for t in texts if t and t.strip())
    return out


class Router:
    """A small tool router: softmax regression from a text's features to a tool, learned with numpy."""

    def __init__(self) -> None:
        """Untrained: no words, no tools, no weights."""
        self.vocab: dict[str, int] = {}
        self.labels: list[str] = []
        self.weights = None  # numpy array, features x tools
        self.bias = None

    def _vector(self, text: str):
        """A text as a unit-length row of which known features it has (unknown words are ignored)."""
        import numpy as np

        row = np.zeros(len(self.vocab), dtype=np.float32)
        for f in features(text):
            i = self.vocab.get(f)
            if i is not None:
                row[i] = 1.0
        norm = float(np.linalg.norm(row))
        return row / norm if norm else row

    def train(self, examples: list[Example], epochs: int = 400, rate: float = 4.0, l2: float = 1e-4) -> "Router":
        """Learns from examples by full-batch gradient descent on the cross-entropy, with a little L2 so rare words
        don't take over; the same examples always give the same model. ValueError with nothing to learn."""
        import numpy as np

        if not examples:
            raise ValueError("Nothing to learn from.")
        self.labels = sorted({e.label for e in examples})
        self.vocab = {f: i for i, f in enumerate(sorted({f for e in examples for f in features(e.text)}))}
        x = np.stack([self._vector(e.text) for e in examples])
        index = {label: i for i, label in enumerate(self.labels)}
        y = np.zeros((len(examples), len(self.labels)), dtype=np.float32)
        y[np.arange(len(examples)), [index[e.label] for e in examples]] = 1.0
        w = np.zeros((x.shape[1], y.shape[1]), dtype=np.float32)
        b = np.zeros(y.shape[1], dtype=np.float32)
        n = float(len(examples))
        for _ in range(epochs):
            logits = x @ w + b
            logits -= logits.max(axis=1, keepdims=True)
            p = np.exp(logits)
            p /= p.sum(axis=1, keepdims=True)
            grad = p - y
            w -= rate * ((x.T @ grad) / n + l2 * w)
            b -= rate * grad.mean(axis=0)
        self.weights, self.bias = w, b
        return self

    def scores(self, text: str, top: int = 5) -> list[tuple[str, float]]:
        """The `top` tools for a text with the model's probability for each, best first."""
        import numpy as np

        if self.weights is None:
            return []
        logits = self._vector(text) @ self.weights + self.bias
        p = np.exp(logits - logits.max())
        p /= p.sum()
        order = np.argsort(-p)[:top]
        return [(self.labels[i], round(float(p[i]), 4)) for i in order]

    def save(self, folder: Path) -> None:
        """Writes the weights (weights.npz) and the words and tools it knows (vocab.json) into a folder."""
        import numpy as np

        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / ".weights.tmp.npz"
        np.savez_compressed(tmp, weights=self.weights, bias=self.bias)
        tmp.replace(folder / "weights.npz")
        atomic_write_text(folder / "vocab.json", json.dumps({"vocab": self.vocab, "labels": self.labels}))

    @classmethod
    def load(cls, folder: Path) -> "Router":
        """A saved router (OSError or ValueError when it isn't there or won't read)."""
        import numpy as np

        folder = Path(folder)
        model = cls()
        meta = json.loads((folder / "vocab.json").read_text(encoding="utf-8"))
        model.vocab, model.labels = dict(meta["vocab"]), list(meta["labels"])
        with np.load(folder / "weights.npz") as data:
            model.weights, model.bias = data["weights"], data["bias"]
        return model


def evaluate(model: Router, held_out: list[Example], top: int = 5) -> dict:
    """How the model does on examples it never saw: the share whose tool is its first pick and the share in its top
    `top`, over the examples whose tool it knows; the ones about tools it never learned, and its misses."""
    known = [e for e in held_out if e.label in set(model.labels)]
    first = in_top = 0
    misses = []
    for e in known:
        picks = [label for label, _p in model.scores(e.text, top)]
        first += bool(picks and picks[0] == e.label)
        in_top += e.label in picks
        if e.label not in picks:
            misses.append({"said": e.text, "wanted": e.label, "picked": picks[:3]})
    n = len(known)
    return {"tested": n, "unknown_tools": len(held_out) - n, "top1": round(first / n, 3) if n else None,
            f"top{top}": round(in_top / n, 3) if n else None, "misses": misses}


# Training settings to choose from (epochs, rate, l2), cheapest first: a tie goes to the cheaper one.
SETTINGS = ((400, 4.0, 1e-4), (800, 8.0, 1e-4), (1500, 8.0, 0.0))


def split(held_out: list[Example]) -> tuple[list[Example], list[Example]]:
    """Pure logic. The held-out requests in two halves, alternating: one to choose the training settings on, one to
    report the score on. Choosing on the same requests the score comes from would flatter the model."""
    return held_out[0::2], held_out[1::2]


def forge_router(actions: Iterable, held_out: list[Example], name: str = "router", folder: Path = MODELS,
                 baseline: Optional[float] = None, top: int = 5, settings=SETTINGS) -> dict:
    """Trains a router from the tools' own words, keeps it with its card in folder/name, and returns the card. Each
    of the settings is tried; the one that does best on half the held-out requests is kept, and its score is
    reported on the other half, which chose nothing. `baseline` is the keyword router's share on the same
    requests, for the card."""
    actions = list(actions)
    training = examples_from_actions(actions)
    choose_on, report_on = split(held_out)
    best = None
    for epochs, rate, l2 in settings:
        candidate = Router().train(training, epochs, rate, l2)
        tried = evaluate(candidate, choose_on, top)
        mark = (tried["top1"] or 0, tried[f"top{top}"] or 0)
        if best is None or mark > best[0]:
            best = (mark, candidate, (epochs, rate, l2))
    _mark, model, chosen = best
    scored = evaluate(model, report_on, top)
    card = {
        "name": name, "kind": "tool router (softmax regression over word stems and pairs, numpy)",
        "made": datetime.now().isoformat(timespec="seconds"), "decision": "DEC-0106",
        "trained_on": {"examples": len(training), "tools": len(model.labels), "features": len(model.vocab),
                       "source": "each tool's own name, description, trigger phrases and subjects; nothing a person said"},
        "settings": {"epochs": chosen[0], "rate": chosen[1], "l2": chosen[2], "chosen_on": len(choose_on),
                     "chosen_on_scores": {"top1": _mark[0], f"top{top}": _mark[1]}},
        "tested_on": {"examples": scored["tested"], "left_out_unknown_tools": scored["unknown_tools"],
                      "source": "half the routing corpus: real requests, never trained on and not used to choose"},
        "scores": {"top1": scored["top1"], f"top{top}": scored[f"top{top}"]},
        "keyword_router": {"offers_the_tool": baseline,
                           "note": "tuned by hand on these same requests, so it isn't a fair comparison"},
        "misses": scored["misses"][:40],
        "in_use": False,
    }
    target = Path(folder) / name
    model.save(target)
    atomic_write_text(target / "card.json", json.dumps(card, indent=1, ensure_ascii=False))
    return card


def cards(folder: Path = MODELS) -> list[dict]:
    """Every model she has made, by its card (a folder without a readable card is left out)."""
    out = []
    for path in sorted(Path(folder).glob("*/card.json")) if Path(folder).exists() else []:
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out
