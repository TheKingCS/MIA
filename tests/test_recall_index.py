"""Recall by meaning: refs and vectors only, every hit re-read from its store (core/recall_index.py, DEC-0210)."""

from types import SimpleNamespace

from core import recall_index as ri


class _Memories:
    """A stand-in memory store."""

    def __init__(self, items):
        """{id: text}."""
        self.items = dict(items)

    def all_memories(self):
        """Every memory."""
        return [SimpleNamespace(memory_id=k, text=v) for k, v in self.items.items()]

    def get_memory(self, mid):
        """One memory, or None."""
        return SimpleNamespace(memory_id=mid, text=self.items[mid]) if mid in self.items else None


class _Projects:
    """A stand-in project store."""

    def __init__(self, items):
        """{id: (name, description)}."""
        self.items = dict(items)

    def all_projects(self):
        """Every project."""
        return [SimpleNamespace(project_id=k, name=n, description=d) for k, (n, d) in self.items.items()]

    def get_project(self, pid):
        """One project, or None."""
        if pid not in self.items:
            return None
        n, d = self.items[pid]
        return SimpleNamespace(project_id=pid, name=n, description=d)


def _embed(texts, kind):
    """A stand-in embedding: a vector of which topic words a text has (coop, money, garden)."""
    topics = (("coop", "chicken", "hens"), ("money", "budget", "savings"), ("garden", "tomato", "seed"))
    return [[1.0 if any(w in t.lower() for w in ws) else 0.0 for ws in topics] + [0.01] for t in texts]


_embed.model = "test-embed"


def _context(tmp_path, memories=None, projects=None):
    """A context with these stores and an empty index."""
    return SimpleNamespace(user_memories=_Memories(memories or {}), projects=_Projects(projects or {}),
                           recall=ri.RecallIndex(None, tmp_path))


def test_the_index_holds_refs_hashes_and_vectors_never_the_text(tmp_path):
    ctx = _context(tmp_path, {"m1": "Zac wants to build a chicken coop this spring"})
    ctx.recall.refresh(ctx, embed=_embed)
    from core.at_rest import open_text

    assert (tmp_path / "recall_index.json").read_text(encoding="utf-8").startswith("MIA-SEALED")  # sealed on disk
    saved = open_text(tmp_path / "recall_index.json")
    assert "memory:m1" in saved and "chicken" not in saved and "spring" not in saved


def test_a_search_finds_by_meaning_and_rereads_the_record(tmp_path):
    ctx = _context(tmp_path, {"m1": "He wants hens by April", "m2": "Savings goal is set"},
                   {"p1": ("Coop build", "framing and roof")})
    ctx.recall.refresh(ctx, embed=_embed)
    found = ri.search(ctx, "what about the chicken house?", embed=_embed)
    assert found["how"] == "meaning" and {h["ref"] for h in found["hits"]} == {"memory:m1", "project:p1"}
    assert all(h["how"] == "related" for h in found["hits"])


def test_a_deleted_record_never_comes_back_from_a_stale_vector(tmp_path):
    ctx = _context(tmp_path, {"m1": "He wants hens by April"})
    ctx.recall.refresh(ctx, embed=_embed)
    del ctx.user_memories.items["m1"]
    assert ri.search(ctx, "chicken", embed=_embed)["hits"] == [] and "memory:m1" not in ctx.recall.items


def test_a_refresh_drops_what_is_gone_and_reembeds_what_changed(tmp_path):
    ctx = _context(tmp_path, {"m1": "hens", "m2": "budget"})
    ctx.recall.refresh(ctx, embed=_embed)
    before = ctx.recall.items["memory:m1"]["h"]
    ctx.user_memories.items["m1"] = "tomato seedlings"
    del ctx.user_memories.items["m2"]
    done = ctx.recall.refresh(ctx, embed=_embed)
    assert done["dropped"] == 1 and done["added"] == 1 and ctx.recall.items["memory:m1"]["h"] != before


def test_refreshing_embeds_at_most_a_batch_at_a_time(tmp_path, monkeypatch):
    monkeypatch.setattr(ri, "BATCH", 2)
    ctx = _context(tmp_path, {f"m{i}": f"note {i}" for i in range(5)})
    assert ctx.recall.refresh(ctx, embed=_embed) == {"added": 2, "dropped": 0, "waiting": 3}


def test_another_embedding_model_starts_the_index_over(tmp_path):
    ctx = _context(tmp_path, {"m1": "hens"})
    ctx.recall.refresh(ctx, embed=_embed)

    def other(texts, kind):
        """Another model."""
        return _embed(texts, kind)

    other.model = "other-embed"
    ctx.recall.refresh(ctx, embed=other)
    assert ctx.recall.model == "other-embed" and list(ctx.recall.items) == ["memory:m1"]


def test_without_an_embedding_model_it_matches_words_and_says_so(tmp_path, monkeypatch):
    ctx = _context(tmp_path, {"m1": "the chicken coop needs a roof", "m2": "budget for March"})
    monkeypatch.setattr(ri, "embedder", lambda context: None)  # no model, whatever this machine has running
    found = ri.search(ctx, "coop roof", embed=None)
    assert found["how"] == "words" and [h["ref"] for h in found["hits"]] == ["memory:m1"]


def test_the_private_journal_is_never_a_source():
    assert all(attr != "private_journal" for attr, *_rest in ri.SOURCES.values())


def test_she_says_what_she_found_and_how(tmp_path, monkeypatch):
    ctx = _context(tmp_path, {"m1": "He wants hens by April"})
    ctx.recall.refresh(ctx, embed=_embed)
    monkeypatch.setattr(ri, "embedder", lambda c: _embed)
    said = ri.said(ctx, "chickens")
    assert "related by meaning" in said and "He wants hens by April" in said
    assert "didn't find" in ri.said(ctx, "taxes")


def test_the_index_is_a_personal_store_rebuilt_by_a_job_held_by_stop():
    from core.background_jobs import JOBS
    from core.personal_data import PERSONAL_ATTRIBUTES
    from core.stop import JOBS_THAT_WAIT

    assert "recall" in PERSONAL_ATTRIBUTES and "recall_index" in JOBS_THAT_WAIT
    assert ("recall_index", 600, "_check_recall_index") in JOBS


def test_the_background_refresh_embeds_on_its_own_thread_once_at_a_time(tmp_path):
    import time

    ctx = _context(tmp_path, {"m1": "hens"})
    assert ctx.recall.refresh_later(ctx, embed=_embed)
    for _ in range(100):
        if not ctx.recall._refreshing.is_set():
            break
        time.sleep(0.02)
    assert "memory:m1" in ctx.recall.items


def test_a_second_background_refresh_waits_for_the_first():
    import tempfile

    index = ri.RecallIndex(None, tempfile.mkdtemp())
    index._refreshing.set()
    assert index.refresh_later(SimpleNamespace()) is False
