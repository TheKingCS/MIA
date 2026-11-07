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

**Assigning a model to an issue or project** (`PLAYBOOK`, `opportunities()`): an issue is one of her improvement
loops (core/loops.py) below its floor or sliding. The playbook says which kinds of small model could move which
loops (a router for requests reaching the wrong tool, a classifier for messages that aren't welcome, an
extractor for documents read wrong, a forecaster for numbers she guesses, a scorer for answers that land badly),
and each model's card names what it `serves`. So a model is judged by the issue it was made for: its loop has to
get better, not only its test score.

**In the shadow, never in charge** (`shadow_picks()`, `shadow_record()`):
each traced turn notes the router's top five beside what the keyword
router offered and the tool she called (core/turn_trace.py), tool names
only. The keyword router was tuned on the corpus, so the corpus can't
show which is better; new requests can. The `models.router_shadow` loop
watches how often the tool she called is in the router's top five. It
goes into use only when it wins there and Zac approves.
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
    """One thing to learn from or be tested on: some words, the tool they mean, and the domains whose records the
    words name (the person's own things: "the peppers" names a Maintenance record)."""
    text: str
    label: str
    named: tuple = ()


def examples_from_actions(actions: Iterable, named: bool = True) -> list[Example]:
    """The training set from the tools themselves: each tool's name (as words), description, trigger phrases and
    subjects, each an example of that tool; and, with `named`, each of those again as though it named one of the
    person's records in the tool's domain, so a request naming "the peppers" leans toward that domain's tools
    (chosen on the half of the corpus that chooses: 86% to 87% first pick, 97% to 99% in the top five).
    Nothing a person said is in it."""
    out = []
    for a in actions:
        texts = [a.name.replace("_", " "), a.description, *getattr(a, "trigger_phrases", ()),
                 *getattr(a, "subjects", ())]
        texts = [t for t in texts if t and t.strip()]
        out.extend(Example(t, a.name) for t in texts)
        if named and getattr(a, "domain", None):
            out.extend(Example(t, a.name, (a.domain,)) for t in texts)
    return out


class Router:
    """A small tool router: softmax regression from a text's features to a tool, learned with numpy."""

    def __init__(self) -> None:
        """Untrained: no words, no tools, no weights."""
        self.vocab: dict[str, int] = {}
        self.labels: list[str] = []
        self.weights = None  # numpy array, features x tools
        self.bias = None

    def _vector(self, text: str, named: Iterable[str] = ()):
        """A text as a unit-length row of which known features it has (unknown words are ignored), with one
        feature for each domain whose records it names."""
        import numpy as np

        row = np.zeros(len(self.vocab), dtype=np.float32)
        for f in features(text) + [f"@{d}" for d in named]:
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
        self.vocab = {f: i for i, f in enumerate(sorted({f for e in examples
                                                          for f in features(e.text) + [f"@{d}" for d in e.named]}))}
        x = np.stack([self._vector(e.text, e.named) for e in examples])
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

    def scores(self, text: str, top: int = 5, named: Iterable[str] = ()) -> list[tuple[str, float]]:
        """The `top` tools for a text (and the domains whose records it names) with the model's probability for
        each, best first."""
        import numpy as np

        if self.weights is None:
            return []
        logits = self._vector(text, named) @ self.weights + self.bias
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
        picks = [label for label, _p in model.scores(e.text, top, e.named)]
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
                 baseline: Optional[float] = None, top: int = 5, settings=SETTINGS,
                 serves: tuple[str, ...] = ("loop:answers.no_tool", "loop:answers.rephrased",
                                            "loop:answers.talked_instead", "loop:answers.routing")) -> dict:
    """Trains a router from the tools' own words, keeps it with its card in folder/name, and returns the card. Each
    of the settings is tried; the one that does best on half the held-out requests is kept, and its score is
    reported on the other half, which chose nothing. `baseline` is the keyword router's share on the same
    requests, for the card. `serves` names the issues or projects it's assigned to (loop:..., project:...,
    mission:..., gap:...): whether it helps is read from those."""
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
        "serves": list(serves),  # the issues (loops) or projects it's assigned to, and judged by
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


def assigned_to(ref: str, folder: Path = MODELS) -> list[dict]:
    """The models assigned to an issue or project (a ref like loop:answers.routing or project:...), by their cards."""
    return [c for c in cards(folder) if ref in (c.get("serves") or [])]


# ------------------------------------------------------------------ choosing a specialist for an issue

@dataclass(frozen=True)
class Specialist:
    """One kind of small model she can make for an issue: what it does, what it learns from, the loops whose issues
    it could move, and whether the forge can make it yet."""
    kind: str
    does: str
    learns_from: str
    serves: tuple[str, ...]
    built: bool = False


# Her playbook (Zac, 2026-11-07: "how she can best use this new feature to better herself by assigning or building
# specialized models to an issue or project"). An issue is a loop that slipped; each kind of model here is a way to
# move one. A project gets a model by naming it in the model's `serves`.
PLAYBOOK: tuple[Specialist, ...] = (
    Specialist("router", "picks which of her tools fit what was said",
               "her tools' own words, then the requests that reached the wrong tool",
               ("answers.no_tool", "answers.rephrased", "answers.talked_instead", "answers.routing", "gaps.repeated"),
               built=True),
    Specialist("classifier", "sorts a thing into a kind (a document's type, whether a message is welcome now)",
               "past things and the kind each turned out to be (filed documents, dismissed or kept messages)",
               ("inbox.reading", "gate.dismissed", "gate.unwelcome", "checks.dismissed", "actions.declined",
                "notes.offers")),
    Specialist("extractor", "reads fields out of text (a receipt's total, a due date, a part number)",
               "documents and the fields a person corrected when filing them",
               ("inbox.reading", "memory.quality", "corrections.all")),
    Specialist("forecaster", "predicts a number or a date from a history (a bill, a lay rate, a work day)",
               "the records' own history, checked against what then happened",
               ("answers.projections", "loop.prediction", "answers.numbers", "missions.recurring")),
    Specialist("scorer", "judges an answer or a candidate: how likely it lands well, or is right",
               "answers rated, flagged or corrected, and how they were rated",
               ("answers.corpus", "answers.calibration", "answers.thumbs", "answers.failures", "news.misleading")),
)


def specialists_for(loop_id: str) -> list[Specialist]:
    """Pure logic. The kinds of model that could move a loop, the ones the forge can make today first."""
    return sorted((s for s in PLAYBOOK if loop_id in s.serves), key=lambda s: not s.built)


def opportunities(rows: list[dict], folder: Path = MODELS) -> list[dict]:
    """Where a model of her own could help now: each loop below its floor or sliding (rows from loops.summary()),
    with the kinds of model that could move it and the models already assigned to it; below the floor first."""
    out = []
    for row in rows:
        if row.get("state") not in ("below", "slid"):
            continue
        kinds = specialists_for(row["id"])
        if not kinds:
            continue
        out.append({"loop": row["id"], "what": row.get("what", ""), "state": row["state"], "why": row.get("why", ""),
                    "kinds": [{"kind": s.kind, "does": s.does, "learns_from": s.learns_from, "built": s.built}
                              for s in kinds],
                    "assigned": [c["name"] for c in assigned_to(f"loop:{row['id']}", folder)]})
    return sorted(out, key=lambda o: o["state"] != "below")


# ------------------------------------------------------------------ the shadow

_LOADED: dict = {}  # folder -> (the weights file's time, the router)


def shadow_router(folder: Path = MODELS / "router") -> Optional[Router]:
    """The saved router, loaded once and again only when it's retrained; None when there isn't one (or it won't
    read)."""
    try:
        stamp = (Path(folder) / "weights.npz").stat().st_mtime
    except OSError:
        return None
    cached = _LOADED.get(str(folder))
    if cached and cached[0] == stamp:
        return cached[1]
    try:
        model = Router.load(folder)
    except (OSError, ValueError, KeyError):
        return None
    _LOADED[str(folder)] = (stamp, model)
    return model


def shadow_picks(context, prompt: str, top: int = 5, folder: Path = MODELS / "router") -> list[str]:
    """What the router would offer for a request, best first, for the trace: tool names only, and [] when there's
    no router or anything goes wrong (the shadow never gets in the way of an answer)."""
    try:
        model = shadow_router(folder)
        if model is None or not (prompt or "").strip():
            return []
        registry = getattr(context, "assistant_actions", None)
        named = registry.named_domains(prompt, context) if registry is not None else set()
        return [label for label, _p in model.scores(prompt, top, sorted(named))]
    except Exception:
        return []


def shadow_record(traces: list[dict]) -> dict:
    """Pure logic. How the router did in the shadow on turns where she called a tool: how often that tool was its
    first pick, how often in its top five, and how often the keyword router had offered it."""
    judged = [t for t in traces if t.get("shadow") and t.get("tools_called")]
    first = sum(1 for t in judged if t["shadow"][0] in t["tools_called"])
    in_top = sum(1 for t in judged if set(t["shadow"]) & set(t["tools_called"]))
    n = len(judged)
    return {"turns": n, "top1": round(first / n, 3) if n else None, "top5": round(in_top / n, 3) if n else None}
