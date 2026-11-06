"""The council's answers (T-0045, from Zac's first real turns): the question before the brief, so the CLI members
answer it instead of acknowledging their instructions; the local members given the code a question is about, and
told they see only that; @mia answering from her documents only when they match well."""

from types import SimpleNamespace

from core import council


def test_the_question_comes_first():
    prompt = council.ASK_PROMPT.format(name="Codex", about="review", words=150, roster="claude", context="(nothing)",
                                       who="zac", text="Why does the page scroll?", reach=council.REACH_CLI, code="")
    assert prompt.startswith("zac asks you:\nWhy does the page scroll?")
    assert "never reply to these instructions" in prompt and prompt.rstrip().endswith("Why does the page scroll?")


def test_code_for_a_question(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "core").mkdir()
    (tmp_path / "web" / "dev.js").write_text("\n".join(
        ["function render() {"] + ["  callback();"] * 40 + ["  const pageY = window.scrollY;", "  window.scrollTo(0, pageY);",
                                                            "}"]), encoding="utf-8")
    (tmp_path / "core" / "device_framework.py").write_text("# devices scroll back\n" * 5, encoding="utf-8")
    code = council.code_for("Why is the MIA Dev page scrolling back to the top?", tmp_path)
    assert "--- web/dev.js" in code and "window.scrollTo(0, pageY)" in code
    assert "device_framework" not in code  # "dev" is a whole path part, never part of "device"
    named = council.code_for("look at core/device_framework.py please", tmp_path)
    assert named.startswith("--- core/device_framework.py")
    assert council.keywords("Can you check why the @mia page keeps scrolling?") == ["scrolling"]


def test_mia_says_so_when_her_sources_dont_cover_it(monkeypatch):
    from core import self_docs

    weak = SimpleNamespace(search=lambda q, n: [(2.0, None)])
    monkeypatch.setattr(self_docs, "index", lambda: weak)
    monkeypatch.setattr(council, "index", lambda repo=None, store=None: SimpleNamespace(search=lambda *a, **k: [],
                                                                                           close=lambda: None))
    said = council.mia_answers("@mia any useEffect hooks resetting the scroll?")
    assert said.startswith("Nothing in my documents or the development history covers that well")
    strong = SimpleNamespace(search=lambda q, n: [(9.0, None)])
    monkeypatch.setattr(self_docs, "index", lambda: strong)
    monkeypatch.setattr(self_docs, "answer", lambda q: "From my own documents: Night School.")
    assert council.mia_answers("what is night school").startswith("From my own documents: Night School.")
