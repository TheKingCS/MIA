"""What MIA can do and how she's built (DEC-0041): the capability map from
the code, "can you…?" answered from it (or "not that I can find", never a
guess), and MIA's own docs searched with the file each answer came from."""

from types import SimpleNamespace

import pytest

from core.capabilities import LIMITS, can_i, capability_map, overview
from core.self_docs import SelfDocs, answer, build
from core.web_surfaces import APPS


@pytest.fixture(scope="module")
def ctx():
    from tests.assistant_registry import build_desktop_registry

    return SimpleNamespace(assistant_actions=build_desktop_registry())


def test_every_app_has_a_limits_entry():
    """Add a line to core/capabilities.LIMITS for a new app ("" if nothing's worth saying)."""
    missing = [a.module_id for a in APPS if a.module_id not in LIMITS]
    assert missing == []
    assert not set(LIMITS) - {a.module_id for a in APPS}  # no entries for apps that are gone


def test_the_map_comes_from_the_code(ctx):
    apps = {a["id"]: a for a in capability_map(ctx)}
    assert apps["budget"]["where"] == "web and desktop" and "list_bills" in apps["budget"]["look_up"]
    assert "mark_bill_paid" in apps["budget"]["change"]
    assert apps["compliance"]["where"] == "web" and apps["household"]["where"] == "desktop"
    assert apps["dashboard"]["where"] == "retired"
    said = overview(ctx)
    assert said.startswith("I have ") and "Compliance:" in said and "Dashboard:" not in said


def test_can_you_answers_from_the_map_or_says_it_cant(ctx):
    assert can_i(ctx, "track my chickens").startswith("Closest match in MIA: Chickens")
    taxes = can_i(ctx, "file my taxes")
    assert taxes.startswith("Closest match in MIA: Compliance") and "never files, pays or signs" in taxes
    assert "Workshop" in can_i(ctx, "sell banana bread at the market")
    assert can_i(ctx, "fly a drone").startswith("I can't find anything in MIA that does \"fly a drone\"")


def test_the_questions_reach_the_tools(ctx):
    from tests.assistant_registry import demo_context, offered_tools

    r = ctx.assistant_actions
    assert r.direct_lookup("What can you do?").name == "what_can_you_do"
    for q in ("What did we decide about eggs?", "Why can't you connect my bank from the phone?"):
        assert r.named_action(q, offered_tools(r, q, demo_context())) == "get_mia_docs", q
    assert "get_capability" in offered_tools(r, "Can you track my chickens?", demo_context())
    assert "get_capability" not in offered_tools(r, "Add milk to the grocery list", demo_context())


def test_docs_search_ranks_decisions_and_labels_history(tmp_path):
    (tmp_path / "specs").mkdir()
    (tmp_path / "DECISIONS.md").write_text(
        "# Decisions\n\n### DEC-0001: Eggs go into cartons\n- Status: APPROVED\n- Decision: eggs are cartoned by the dozen.\n\n"
        "### DEC-0002: Ducks maybe\n- Status: PROPOSED\n- Decision: ducks lay eggs too.\n", encoding="utf-8")
    (tmp_path / "ROADMAP.md").write_text("## Old egg plan\nEggs were going to be sold by the each.\n", encoding="utf-8")
    (tmp_path / "NEXT_SESSION.md").write_text("## Eggs\nBuy egg cartons.\n", encoding="utf-8")
    (tmp_path / "specs" / "FARM.md").write_text("## Eggs\nThe spec asks for egg tracking.\n", encoding="utf-8")
    kinds = {p.heading: p.kind for p in build(tmp_path)}
    assert kinds["DEC-0001: Eggs go into cartons"] == "decision" and kinds["DEC-0002: Ducks maybe"] == "proposal"
    assert kinds["Old egg plan"] == "history" and "Eggs" in kinds  # the spec; NEXT_SESSION isn't indexed
    docs = SelfDocs(tmp_path)
    top = docs.search("What did we decide about eggs?")
    assert top[0][1].heading == "DEC-0001: Eggs go into cartons"
    said = answer("What did we decide about eggs?", docs)
    assert said.startswith("From my own documents, an approved decision: DEC-0001 (Eggs go into cartons) "
                           "(docs/DECISIONS.md). eggs are cartoned by the dozen.")
    assert "Related:" in said and "**" not in said
    assert answer("quantum chromodynamics", docs).startswith("Nothing in my own documents covers that")


def test_the_real_docs_answer_about_mia():
    top = SelfDocs().search("What did we decide about eggs?")
    assert top and top[0][1].heading.startswith("DEC-0037")
