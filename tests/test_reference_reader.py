"""
tests.test_reference_reader
=============================

How she reads her offline library and talks about it (core/reference_reader.py, core/tool_loop.py; Zac, 2026-11-22:
"make her really good at reading through these references and talking naturally but factually"): the part of an
article that answers is found, not its opening; the best passages win; a source is read further by its ref; a
question for the library is read from it even when the model didn't ask; and a figure the text doesn't hold is
never said (small ones too), while the rest of a natural answer stays. Fable's review (2026-11-22): every pack
searched, spoken how-tos read first, "tell me more" left to the model. Then, from live answers on the whole
library (2026-11-23): numbers spelled out, each index's own best, canning as the word that matters, rare words over
common ones, meaning over words, and the rarer words together before any word; word forms as one word, pairs
of words last; and the floor: canning a low-acid food is never told as a water bath. Fable's review (2026-11-23):
the floor stands aside for pickles and "can I eat", keeps a right answer whole; no -er stemming; a few dozen queries
an index; a steady mirror is never failed. Then, live: no pickle recipes for a plain canning question, an ice bath
isn't canning, "a pressure canner or water bath" is unsafe, the guide's own page given instead, cut where another
food's times begin.
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


def test_fable_review_every_pack_is_searched_before_any_is_read_and_each_packs_best_comes_first():
    """74 packs: all searched; the reads go to each pack's first hit before any pack's second."""
    searched = []

    class Many(_Library):
        """Seventy-four packs."""

        def list_packs(self):
            """Packs P00 to P73."""
            return [SimpleNamespace(pack_id=f"p{i:02}", title=f"P{i:02}", file_path=f"p{i:02}.zim") for i in range(74)]

        def search(self, pack_id, query, limit=2):
            """Two hits a pack, noted."""
            searched.append(pack_id)
            return [SimpleNamespace(path=f"A/{n}", title="Fence building") for n in range(2)]

    found = rr.gather(Many(), "how deep should corner posts be set")
    assert len(set(searched)) == 74 and {f["ref"].split("|")[0] for f in found} >= {"p00", "p73"}


def test_fable_review_spoken_how_tos_are_read_from_the_library_and_tell_me_more_is_left_to_the_model():
    """'how do I purify water' (no question mark) reads first; 'tell me more about that?' doesn't force a look-up."""
    context = SimpleNamespace(reference_library=_Library())
    tools = [{"function": {"name": "look_up_offline"}}, {"function": {"name": "read_reference"}}]
    plain = ChatReply(content="From memory", tool_calls=[])
    assert tool_loop._read_first(context, tools, "how do I purify water", plain).tool_calls
    assert tool_loop._read_first(context, tools, "tell me more about that?", plain) is plain


def test_a_figure_the_text_spells_out_may_be_said_in_digits():
    """'Sink a third of the post, about two feet' allows '1/3 of the post' and '2 feet'; '3 feet' still isn't."""
    text = "Sink a third of the post's length, about two feet for a six-foot post."
    assert invented_numbers("Set 1/3 of the post in the ground, about 2 feet for a 6-foot post.", text, "",
                            strict=True) == set()
    assert invented_numbers("About 3 feet.", text, "", strict=True) == {"3"}


def test_each_index_keeps_its_own_best_so_a_small_guide_isnt_drowned_by_a_big_one(tmp_path):
    """per_index: every index's best few come back, whatever their bm25 next to a big index's."""
    from core import pack_index

    def index(name, rows):
        """One index with these pages."""
        pack = tmp_path / f"{name}.zim"
        out = pack_index.index_path(tmp_path, pack)
        out.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3

        db = sqlite3.connect(out)
        db.execute("CREATE VIRTUAL TABLE docs USING fts5(path UNINDEXED, title, page UNINDEXED, body)")
        db.executemany("INSERT INTO docs VALUES (?, ?, ?, ?)", rows)
        db.commit()
        db.close()

    index("big", [(f"p{i}", f"Bean town {i}", 0, "bean " * 50) for i in range(30)])
    index("usda", [("g.pdf", "Home canning guide", 4, "Green beans: pressure can them; never water-bath can beans.")])
    library = SimpleNamespace(list_packs=lambda: [SimpleNamespace(file_path=str(tmp_path / "big.zim"), pack_id="big",
                                                                  title="Big"),
                                                  SimpleNamespace(file_path=str(tmp_path / "usda.zim"), pack_id="usda",
                                                                  title="USDA")])
    hits = pack_index.search(tmp_path, library, "canning green beans", full=True, per_index=2)
    assert "USDA" in {h.pack_title for h in hits} and sum(h.pack_title == "Big" for h in hits) <= 2


def test_canning_is_the_word_that_matters_and_rare_words_outweigh_common_ones():
    """'safely can green beans' keeps canning; the canning guide's page outranks a pet answer that holds the common
    words (green, safely, home) and a bean word."""
    assert rr.terms("How do I safely can green beans at home?")[0] == "canning"
    assert "canning" not in rr.terms("Can I plant beans in shade?")
    wanted = rr.terms("How do I safely can green beans at home?")
    guide = {"pack": "USDA", "article": "Guide 4", "ref": "u|1|4", "distinct": 3,
             "text": "Canning snap beans: pressure can green beans; beans are low-acid."}
    others = [{"pack": f"Q&A {i}", "article": "What green things can I safely feed at home?", "ref": f"q|{i}|0",
               "distinct": 3, "text": "Green leaves are safe at home; beans too, safely cooked."} for i in range(4)]
    for p in [guide, *others]:
        p["score"] = rr.score(wanted, p["article"], p["text"])
    ranked = rr.rank([*others, guide], keep=5, wanted=len(wanted), words=wanted)
    assert "USDA" in [p["pack"] for p in ranked]  # kept among them; meaning settles the order (below)


def test_passages_closest_in_meaning_come_first_when_her_embedding_model_answers(monkeypatch):
    """by_meaning embeds the question and the best passages; rank then puts the nearest first, words breaking ties;
    with no embedding model it says so (None) and the words' ranking stands."""
    from core import meaning

    found = [{"pack": "Cooking", "article": "Prickly pears", "text": "how to cut prickly pears", "ref": "c|1|0",
              "score": 50, "distinct": 2},
             {"pack": "Outdoors", "article": "Treating a wound", "text": "press on the cut to stop bleeding",
              "ref": "o|1|0", "score": 30, "distinct": 2}]

    class Backend:
        """A pretend embedding model: the wound passage is near the question, the pears far."""

        def __init__(self, *a):
            """Nothing."""

        def embed(self, model, texts, timeout):
            """Vectors by their words."""
            return [[1.0, 0.0] if ("deep cut" in t or "wound" in t) else [0.0, 1.0] for t in texts]

    monkeypatch.setattr(meaning, "_base_url", lambda c: "http://127.0.0.1:11434")
    monkeypatch.setattr("core.llm_manager.OllamaBackend", Backend)
    meant = rr.by_meaning(SimpleNamespace(config=None), "How do I treat a deep cut?", found)
    assert rr.rank(meant, keep=2, wanted=2)[0]["pack"] == "Outdoors"
    monkeypatch.setattr(meaning, "_base_url", lambda c: None)
    assert rr.by_meaning(SimpleNamespace(config=None), "How do I treat a deep cut?", found) is None


def test_when_no_page_holds_every_word_the_rarer_words_together_come_before_any_word(tmp_path):
    """'canning safely green beans home': no page has all five; the green-bean page (canning, green, beans) is found
    among the sets of all but one or two words, even where 'canning' is the commonest word in the index."""
    import sqlite3

    from core import pack_index

    pack = tmp_path / "usda.zim"
    out = pack_index.index_path(tmp_path, pack)
    out.parent.mkdir(parents=True)
    db = sqlite3.connect(out)
    db.execute("CREATE VIRTUAL TABLE docs USING fts5(path UNINDEXED, title, page UNINDEXED, body)")
    rows = [("i.pdf", "Intro", n, "home canning home canning safely guide " * 5) for n in range(1, 8)]
    rows += [("t.pdf", "Table", n, "safely store green vegetables at home") for n in range(1, 4)]
    rows.append(("g.pdf", "Guide 4", 3, "Canning green beans: pressure can snap beans; green beans are low-acid."))
    db.executemany("INSERT INTO docs VALUES (?, ?, ?, ?)", rows)
    db.commit()
    db.close()
    library = SimpleNamespace(list_packs=lambda: [SimpleNamespace(file_path=str(pack), pack_id="usda", title="USDA")])
    hits = pack_index.search(tmp_path, library, "canning safely green beans home", full=True, per_index=2)
    assert "Guide 4, page 3" in [h.article_title for h in hits]


def test_canning_a_low_acid_food_is_never_told_as_a_water_bath_and_the_pressure_rule_is_always_said():
    """The floor (Fable's review, 2026-11-23): an answer telling green beans into a water bath isn't said at all,
    only the rule; a correct pressure-canner answer is kept whole, lines and all, with the rule after it; pickled
    beans, "can I eat", tomatoes and other questions are handled as their own."""
    unsafe = "Pack the beans into jars. Fill a water bath canner. Process the pints for 10 minutes."
    said = rr.floor("How do I safely can green beans at home?", unsafe)
    assert "10 minutes" not in said and "pressure canner" in said and "won't give a water-bath method" in said
    right = ("Process pints 20 minutes at 10 pounds in a pressure canner; never use a boiling-water bath.\n"
             "Cover with boiling water, leaving 1-inch headspace.")
    kept = rr.floor("How do I can green beans?", right)
    assert kept.startswith(right) and "low-acid foods like green beans" in kept
    assert rr.floor("how do I can pickled beans (dilly beans)?", "Boiling-water canner, 5 minutes.") == \
        "Boiling-water canner, 5 minutes."
    assert rr.floor("can I eat green beans raw?", "Yes.") == "Yes."
    assert rr.floor("How deep should fence posts be set?", "About 2 feet.") == "About 2 feet."
    assert "bottled lemon juice" in rr.floor("How do I can tomatoes?", "Use a water bath.")
    assert rr.floor("and how long in a water bath?", "Fill a water bath canner.") == "Fill a water bath canner."
    assert "won't give" in rr.floor("and how long in a water bath? how to can corn", "Fill a water bath canner.")


def test_word_forms_are_one_word_and_two_words_together_are_tried_last():
    """canning, canner and canned stem alike (never as the modal "can"); no -er (corner isn't corn); the query
    rounds go down to pairs."""
    from core import pack_index

    assert rr._stem("canning") == rr._stem("canner") == rr._stem("canned") == "canning" != rr._stem("can")
    assert rr._stem("posts") == "post" and rr._stem("seeds") == "seed"
    assert [rr._stem(w) for w in ("corner", "butter", "herring", "summer")] == ["corner", "butter", "herring", "summer"]
    assert rr._hits("You can grow beans; they can climb.", ["canning"]) == (0, 0)
    rounds = pack_index._queries(["canning", "safely", "green", "beans"])
    assert any(q == '"green" AND "beans"' for q in rounds[-2])


def test_fable_review_canning_is_asked_only_when_preserving_food_is_meant():
    """"can my chickens eat corn", "what can the dog eat", "can tomatoes grow in shade" aren't canning."""
    for q in ("can my chickens eat corn", "what can the dog eat", "can tomatoes grow in shade",
              "can potatoes be stored with onions", "how long do canned beans keep", "can I eat green beans raw?"):
        assert not rr.canning_asked(q), q
    for q in ("How do I safely can green beans at home?", "how to can corn", "pressure canning chicken"):
        assert rr.canning_asked(q), q


def test_fable_review_a_long_question_asks_each_index_a_few_dozen_queries_not_thousands():
    """search keeps only the question's words that matter, at most WORDS of them."""
    from core import pack_index

    words = rr.terms("how long should I boil water to make it safe to drink at high altitude")[:pack_index.WORDS]
    assert len(words) <= 5 and sum(len(r) for r in pack_index._queries(words)) <= 30


def test_fable_review_a_steady_mirror_that_bursts_first_is_never_failed(tmp_path, monkeypatch):
    """A mirror that probed at 20 MB/s and then delivers 3 MB/s is no crawler (the floor is capped at 4 x SLOW)."""
    import hashlib
    import io

    from core import offline_library as lib

    body = b"x" * 4000
    now = [0.0]

    class Steady:
        """Probes fast, then sends at a steady 3 MB/s."""

        def __call__(self, url, timeout=60, headers=None):
            """Every read costs time at 3 MB/s (scaled)."""
            start = int((headers or {}).get("Range", "bytes=0-")[6:].split("-")[0] or 0)

            class Answer(io.BytesIO):
                """Each block costs its size at 3 MB/s, scaled up."""
                status = 206 if start else 200
                headers = {}

                def read(self, n=-1):
                    """One block."""
                    block = super().read(min(n if n > 0 else 100, 100))
                    now[0] += len(block) * 1000 / 3e6
                    return block
            return Answer(body[start:])

    monkeypatch.setattr(lib, "ranked", lambda urls, get, clock: [(u, 20e6) for u in urls])
    monkeypatch.setattr(lib, "PROBE", 1)
    monkeypatch.setattr(lib, "STALL", 1)
    meta = {"name": "p.zim", "size": len(body), "sha256": hashlib.sha256(body).hexdigest(),
            "urls": ["https://m1.example/p", "https://m2.example/p"]}
    lib.download(meta, tmp_path / "p.partial", Steady(), clock=lambda: now[0])
    assert (tmp_path / "p.partial").read_bytes() == body



def test_what_the_references_call_it_is_searched_too():
    """Green beans are snap beans in the USDA's guide: 'snap' joins the words, near the front."""
    words = rr.terms("How do I safely can green beans at home?")
    assert words[:2] == ["canning", "snap"]
    assert "summer" in rr.terms("how to grow zucchini")


def test_a_plain_canning_question_doesnt_read_the_pickle_recipes():
    """Canning green beans: the dilly-bean (pickled) page is left out; asking about pickled beans keeps it."""
    pages = [{"pack": "USDA", "article": "Guide 4, page 8", "text": "Snap beans: process in a pressure canner."},
             {"pack": "USDA", "article": "Guide 6, page 14", "text": "PICKLED DILLY BEANS: 5 cups vinegar..."}]
    assert [p["article"] for p in rr.not_pickling("How do I can green beans?", pages)] == ["Guide 4, page 8"]
    assert len(rr.not_pickling("How do I can pickled beans?", pages)) == 2
    assert len(rr.not_pickling("How deep should fence posts be set?", pages)) == 2


def test_an_ice_bath_isnt_canning_an_or_offers_the_bath_and_the_guides_page_is_given_instead():
    """Cooling beans in an ice water bath is fine; 'a pressure canner or water bath canner' is unsafe; replaced, the
    answer gives the USDA's own page for the food from what she read."""
    assert not rr.unsafe_bath("Blanch, then move them to an ice water bath to cool.")
    assert rr.unsafe_bath("Process them in a pressure canner or water bath canner.")
    sources = ("[From her offline library.]\nFrom USDA Guide to Home Canning, \"Guide 4, page 8\"\nref: u|g4|8\n"
               "BEANS, SNAP AND ITALIAN. Green and wax. Process in a pressure canner: pints 20 minutes, 11 pounds.")
    said = rr.floor("How do I can green beans?", "Use a pressure canner or water bath canner.", sources)
    assert "Here is the guide's own page" in said and "pints 20 minutes, 11 pounds" in said



def test_the_guides_page_stops_where_another_foods_times_begin():
    """Snap beans' steps, then lima beans' table on the same PDF page: the lima table is never given for green beans."""
    sources = ("From USDA Guide to Home Canning, \"Guide 4, page 8\"\nref: u|g4|8\n"
               "BEANS, SNAP. Procedure: Wash beans. Adjust lids and process. Lima beans Recommended process time for "
               "Lima Beans in a dial-gauge pressure canner Hot Pints 40 min 11 lb")
    page = rr.usda_passage(sources, "green beans")
    assert "Adjust lids and process." in page and "40 min" not in page and "Lima" not in page
