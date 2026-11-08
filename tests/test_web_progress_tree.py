"""The Skills page's tree (core/web_progress.skill_tree): a column per tier, prerequisites from other categories in a
first column marked outside, and a line from each prerequisite to the skill it opens, lit once the prerequisite has
XP."""

from core.web_progress import TREE_BOX_W, TREE_COL, skill_tree


def row(sid, name, category, tier, requires=(), xp=0, unlocked=True):
    """One skill as the progress tree reads it."""
    return {"id": sid, "name": name, "category": category, "tier": tier, "requires": list(requires), "total_xp": xp,
            "unlocked": unlocked}


def test_a_category_is_drawn_by_tier_with_its_prerequisite_lines():
    rows = [row("code", "Coding", "Technology", 1, xp=40), row("weld", "Welding", "Maker", 1),
            row("elec", "Electronics", "Technology", 2, ["code"], unlocked=True),
            row("robot", "Robotics", "Technology", 3, ["elec", "weld"], unlocked=False)]
    t = skill_tree(rows, "Technology")
    at = {n["id"]: (n["x"], n["y"], n["outside"]) for n in t["nodes"]}
    assert at["weld"] == (0, 0, True)  # from Maker: the first column
    assert at["code"][0] == TREE_COL and at["elec"][0] == 2 * TREE_COL and at["robot"][0] == 3 * TREE_COL
    lines = {(e["from"], e["to"]): e for e in t["edges"]}
    assert lines[("code", "elec")]["met"] and not lines[("weld", "robot")]["met"]
    assert lines[("code", "elec")]["x1"] == TREE_COL + TREE_BOX_W and t["w"] == 3 * TREE_COL + TREE_BOX_W
    assert skill_tree(rows, "Maker") == {"w": 0, "h": 0, "nodes": [], "edges": []}
