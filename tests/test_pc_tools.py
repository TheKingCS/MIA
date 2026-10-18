"""
The home-PC kit (DEC-0022): the readiness check says what's missing,
and the model comparison recommends the most accurate model, the faster
of two that are about as accurate.
"""

from tools.pc_model_check import recommend


def test_recommend_most_accurate_then_faster():
    rows = [{"model": "14b", "done": 213, "percent": 93.0, "median_seconds": 1.2},
            {"model": "32b", "done": 213, "percent": 95.0, "median_seconds": 2.9}]
    assert recommend(rows)["model"] == "14b"  # within 3 points: the faster
    rows[1]["percent"] = 98.0
    assert recommend(rows)["model"] == "32b"
    assert recommend([]) is None


def test_readiness_lists_what_the_phone_needs(monkeypatch):
    import tools.pc_check as pc

    class Config:
        values = {"llm.base_url": "http://127.0.0.1:9", "llm.model": "qwen2.5:14b", "server.enabled": False}

        def get(self, key, default=None):
            return self.values.get(key, default)

    monkeypatch.setattr(pc, "_tailscale", lambda: None)
    got = {name: status for name, status, _d, _f in pc.checks(Config())}
    assert got["The brain (Ollama)"] == pc.MISSING
    assert got["Phone Access"] == pc.MISSING and got["Tailscale"] == pc.MISSING
