"""
tests.test_voice_parity_tools
===============================

The tools that made Character, Skills, the Reward Shop, Insurance, Kept,
the Operating Journal, Play and Files usable by voice (DEC-0125):
each answers from its screen's own data, and buying a reward goes
through the shop's own action.
"""

from types import SimpleNamespace

from core import assistant_progress_actions as progress
from core import assistant_records_actions as records
from core.actions import ActionError


def test_character_says_level_xp_credits_and_attributes(monkeypatch):
    """Phrased from the Character screen's data."""
    page = {"available": True, "me": {"level": 4, "xp_into_level": 120, "xp_for_level": 400, "total_xp": 1520,
                                     "credits": 300},
            "attributes": [{"name": "Strength", "value": 6, "max": 10}], "missions_completed": 12, "buffs": []}
    monkeypatch.setattr("core.web_progress.character_page", lambda context: page)
    said = progress._action_get_character(None, {})
    assert "Level 4" in said and "120 of 400 XP" in said and "300 credits" in said
    assert "Strength 6/10" in said and "Missions completed: 12" in said


def test_skills_name_one_skill_or_say_it_is_not_there(monkeypatch):
    """A named skill gets its level; an unknown one is said plainly."""
    skill = {"name": "Welding", "level": 3, "xp_into_level": 50, "xp_for_level": 200, "status": "learning",
             "this_week": 40}
    monkeypatch.setattr("core.web_progress.skills_page", lambda context: {"available": True, "skills": [skill]})
    assert "Welding: level 3" in progress._action_get_skills(None, {"skill": "weld"})
    assert "don't see a skill called knitting" in progress._action_get_skills(None, {"skill": "knitting"})


def test_rewards_split_what_is_ready_from_what_is_saved_for(monkeypatch):
    """Credits left, the rewards in reach and how many to go for the rest."""
    page = {"available": True, "credits": {"left": 500}, "rewards": [
        {"name": "Movie night", "cost": 300, "available": True, "affordable": True, "to_go": 0},
        {"name": "New boots", "cost": 2000, "available": True, "affordable": False, "to_go": 1500}]}
    monkeypatch.setattr("core.game_layer.shop_page", lambda context: page)
    said = progress._action_list_rewards(None, {})
    assert "500 credits" in said and "Ready now: Movie night (300)" in said and "New boots (1,500 to go)" in said


class _Shop:
    """A reward shop with two rewards."""

    def all_rewards(self):
        """Movie night and Movie snacks."""
        return [SimpleNamespace(reward_id="r1", name="Movie night"), SimpleNamespace(reward_id="r2", name="Movie snacks")]


class _Actions:
    """Records each proposal, and approves it, or refuses as shop.buy would."""

    def __init__(self, refuse=""):
        """Nothing proposed yet."""
        self.proposed, self.refuse = [], refuse

    def propose(self, context, kind, params, proposed_by):
        """Keeps the proposal, refusing when told to."""
        if self.refuse:
            raise ActionError(self.refuse)
        self.proposed.append((kind, params))
        return SimpleNamespace(proposal_id="p1")

    def approve(self, context, proposal_id):
        """Runs it."""
        return SimpleNamespace(status="executed", result="Bought Movie night.")


def test_buying_a_reward_goes_through_the_shop_action_and_can_be_undone():
    """One match: shop.buy with its id, and the reply says undo works."""
    actions = _Actions()
    said = progress._action_buy_reward(SimpleNamespace(reward_shop=_Shop(), actions=actions), {"reward": "movie night"})
    assert actions.proposed == [("shop.buy", {"reward_id": "r1"})] and "undo that" in said


def test_buying_asks_which_when_the_name_matches_more_than_one():
    """"Movie" could be either: nothing is bought."""
    actions = _Actions()
    said = progress._action_buy_reward(SimpleNamespace(reward_shop=_Shop(), actions=actions), {"reward": "movie"})
    assert said.startswith("Which one?") and not actions.proposed


def test_buying_says_why_when_the_shop_refuses():
    """Too few credits: the shop action's own words."""
    actions = _Actions(refuse="Movie night costs 300 credits; you have 100. 200 to go.")
    said = progress._action_buy_reward(SimpleNamespace(reward_shop=_Shop(), actions=actions), {"reward": "night"})
    assert "200 to go" in said


def test_insurance_names_each_policy_its_cost_and_renewal(monkeypatch):
    """From the Insurance page: cost a year, renewal, deductible, a check, and the total."""
    policy = {"name": "Truck insurance", "kind": "Auto", "insurer": "Acme", "covers": "Truck", "per_year": 1200.0,
              "renews": "2026-12-01", "deductible": 500.0, "checks": [{"text": "Renews in 24 days."}]}
    page = {"available": True, "policies": [policy], "summary": {"per_year": 1200.0, "could_save": 0}}
    monkeypatch.setattr("core.insurance.insurance_page", lambda context: page)
    said = records._action_get_insurance(None, {})
    assert "Truck insurance with Acme" in said and "renews 2026-12-01" in said and "Renews in 24 days." in said
    assert "don't see a policy for boat" in records._action_get_insurance(None, {"policy": "boat"})


def test_kept_lists_open_notes_of_the_kind_asked(monkeypatch):
    """Promises asked: only the open promises, with their due date."""
    kinds = [{"kind": "commitment", "title": "Promises", "notes": [
                 {"line": "Fix the gate for Sam", "status": "open", "due": "2026-11-10"},
                 {"line": "Call the vet", "status": "done", "due": ""}]},
             {"kind": "idea", "title": "Ideas", "notes": [{"line": "Sell honey", "status": "open", "due": ""}]}]
    monkeypatch.setattr("core.life_notes.screen", lambda context: {"kinds": kinds})
    said = records._action_list_kept(None, {"kind": "promises"})
    assert said == "Promises: Fix the gate for Sam (by 2026-11-10)."


def test_find_my_files_stays_inside_the_persons_folder(tmp_path, monkeypatch):
    """Found by name, shown relative to My Files; a file outside it is never found."""
    from core.my_files import MyFiles

    root = tmp_path / "my_files"
    (root / "money").mkdir(parents=True)
    (root / "money" / "taxes 2025.pdf").write_text("x")
    (tmp_path / "taxes outside.pdf").write_text("x")
    monkeypatch.setattr(MyFiles, "for_context", classmethod(lambda cls, context: cls(root)))
    said = records._action_find_my_files(None, {"name": "taxes"})
    assert "money/taxes 2025.pdf" in said and "outside" not in said
    assert "money/" in records._action_find_my_files(None, {})
