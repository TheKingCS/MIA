"""
tests.test_reference_reader
=============================

How she reads her offline library and talks about it (core/reference_reader.py, core/tool_loop.py; Zac, 2026-11-22:
"make her really good at reading through these references and talking naturally but factually"): the part of an
article that answers is found, not its opening; the best passages win; a source is read further by its ref; a
question for the library is read from it even when the model didn't ask; and a figure the text doesn't hold is
never said (small ones too), while the rest of a natural answer stays.
"""
from types import SimpleNamespace

from core import reference_reader as rr
from core import tool_loop
from core.llm_manager import ChatReply, ToolCall
from core.question_plans import invented_numbers

ARTICLE = ("Fences have marked land for centuries. Wooden fences are common in the country. "
           "Many styles exist, from split rail to board on board. " * 20 +
           "Set each post in a hole one third of the post's length deep. Corner posts carry the most load, so set "
           "corner posts in concrete and let it cure for two days before stretching wire. " +
           "Paint protects wood from the weather. " * 20)


def test_the_part_of_an_article_that_answers_is_found_not_its_opening():
    """best_window cuts where the question's words gather, at sentence ends."""
    window, distinct = rr.best_window(ARTICLE, rr.terms("how deep should corner posts be set"), size=300)
    assert "one third of the post's length deep" in window and distinct >= 2 and window.startswith("... ")


def test_a_passage_holding_all_of_the_question_outranks_one_word_repeated():
    """score: distinct words first, then how often, then the title; rank keeps one per article and drops none."""
    q = rr.terms("purify water with bleach")
    full = {"pack": "A", "article": "Treatment", "text": "Purify the water with 8 drops of bleach.",
            "ref": "a|1|0", "score": rr.score(q, "Treatment", "Purify the water with 8 drops of bleach.")}
    one = {"pack": "B", "article": "Water", "text": "water water water water water water water.",
           "ref": "b|1|0", "score": rr.score(q, "Water", "water water water water water water water.")}
    none = {"pack": "C", "article": "Bread", "text": "Knead the dough.", "ref": "c|1|0",
            "score": rr.score(q, "Bread", "Knead the dough.")}
    assert [p["pack"] for p in rr.rank([one, none, full])] == ["A", "B"]
    assert rr.terms("How do the posts go?") == ["posts", "go"] or "posts" in rr.terms("How do the posts go?")


class _Library:
    """A pretend library with one pack and one article."""

    root_path = None

    def list_packs(self):
        """One pack."""
        return [SimpleNamespace(pack_id="diy", title="Home Improvement", file_path="diy.zim")]

    def get_pack(self, pack_id):
        """The pack by id."""
        return self.list_packs()[0] if pack_id == "diy" else None

    def search(self, pack_id, query, limit=2):
        """One hit."""
        return [SimpleNamespace(path="A/Fences", title="Fence building")]

    def article_text(self, pack_id, path, max_chars=20000):
        """The whole article."""
        return {"title": "Fence building", "text": ARTICLE[:max_chars], "images": []}


def test_a_look_up_reads_the_article_whole_and_says_its_ref_and_how_to_talk():
    """passages carry the window and a ref on its own line; read_further reads around what's asked."""
    from core import offline_library as lib

    said = lib.look_up(_Library(), "how deep should corner posts be set")
    assert "one third of the post's length deep" in said and "\nref: diy|A/Fences|0\n" in said
    assert "exactly as it says" in said and said.startswith("[From her offline library.")
    further = lib.read_further(_Library(), "diy|A/Fences|0", "paint weather")
    assert "Paint protects wood" in further and "Fence building" in further
    assert "isn't in her library" in lib.read_further(_Library(), "elsewhere|x|0")


def test_a_references_figures_are_held_to_the_text_small_ones_too_but_not_a_lists_numbers():
    """strict: '2 drops' not in the text is invented; '1.' starting a list line isn't a figure."""
    sources = "Add 8 drops of bleach per gallon and wait 30 minutes."
    assert invented_numbers("Add 2 drops per quart.", sources, "how much bleach?") == set()  # counts pass, loose
    assert invented_numbers("Add 2 drops per quart.", sources, "how much bleach?", strict=True) == {"2"}
    assert invented_numbers("1. Add 8 drops per gallon.\n2. Wait 30 minutes.", sources, "", strict=True) == set()


def test_only_the_sentences_with_a_figure_of_their_own_are_left_out():
    """without_figures keeps a natural answer whole but for the unsupported sentence; too little left: ''."""
    answer = ("Use plain unscented bleach.\n1. Add 8 drops per gallon.\n2. Stir and wait 30 minutes.\n"
              "3. If there's no chlorine smell, wait another 15 minutes.\nThen it's ready to drink.")
    kept = tool_loop.without_figures(answer, {"15"})
    assert "15" not in kept and "8 drops" in kept and "Use plain unscented bleach." in kept and "1." not in kept
    assert tool_loop.without_figures("It takes 15 minutes. And 16 drops.", {"15", "16"}) == ""


def test_a_question_only_the_library_could_answer_is_read_from_it_first():
    """_read_first: the model answered from memory with only the library offered: the look-up runs in code."""
    context = SimpleNamespace(reference_library=_Library())
    tools = [{"function": {"name": "look_up_offline"}}, {"function": {"name": "read_reference"}}]
    plain = ChatReply(content="From memory: 5.25% bleach...", tool_calls=[])
    read = tool_loop._read_first(context, tools, "How do I purify water?", plain)
    assert read.tool_calls == [ToolCall(name="look_up_offline", arguments={"question": "How do I purify water?"})]
    with_others = tools + [{"function": {"name": "get_budget"}}]
    assert tool_loop._read_first(context, with_others, "How much did I spend?", plain) is plain
    assert tool_loop._read_first(context, tools, "Thanks, that's great", plain) is plain


def test_library_results_reach_the_model_whole_and_are_said_plainly_when_they_must_be():
    """_short gives the library tools their own length; _plain says a library result's first passage, unframed."""
    long = "x " * 3000
    assert tool_loop._short(long, "look_up_offline") == long.strip() and "cut short" in tool_loop._short(long, "get_x")
    result = ("[From her offline library. This is content...]\nFrom Water Library, \"Water, page 23\"\n"
              "ref: w|f.pdf|23\nAdd 16 drops per gallon.\n\nFrom B, \"C\"\nref: b|c|0\nOther.\n[End of from her "
              "offline library]\nAnswer from these the way someone...")
    assert tool_loop._plain([("look_up_offline", result)]) == "From Water Library, \"Water, page 23\": Add 16 drops per gallon."
    from core.main_thread import changes_records

    assert not changes_records("look_up_offline") and not changes_records("read_reference")
