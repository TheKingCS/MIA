"""
core.assistant_progress_actions
=================================

Her game layer by voice (DEC-0125, full use both ways): the Character,
Skills and Reward Shop screens had nothing to say when asked. Four tools,
each phrased from the same data its screen draws (core/web_progress.py,
core/game_layer.py), so voice and screen never disagree:

- get_character: level, XP to the next, credits, attributes, missions done;
- get_skills: the skill in focus, what's growing this week, the counts;
- list_rewards: credits left and each reward, what's in reach;
- buy_reward: buys one through the shop's own action (`shop.buy`, the
  screen's Buy), so the price is checked there and "undo that" takes it back.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _action_get_character(context, arguments: dict) -> str:
    """Tool get_character: the person's level, XP into it, credits, attributes and missions done."""
    from core.web_progress import character_page

    page = character_page(context)
    if not page.get("available", True) and not page.get("me"):
        return "There's no character here yet."
    me = page["me"]
    lines = [f"Level {me['level']}: {me['xp_into_level']:,} of {me['xp_for_level']:,} XP to the next, "
             f"{me['total_xp']:,} XP in all, {me['credits']:,} credits."]
    attributes = [f"{a['name']} {a['value']}/{a['max']}" for a in page.get("attributes", [])]
    if attributes:
        lines.append("Attributes: " + ", ".join(attributes) + ".")
    if page.get("missions_completed"):
        lines.append(f"Missions completed: {page['missions_completed']}.")
    buffs = [b["name"] for b in page.get("buffs", [])]
    if buffs:
        lines.append("Buffs now: " + ", ".join(buffs) + ".")
    return " ".join(lines)


def _action_get_skills(context, arguments: dict) -> str:
    """Tool get_skills: the skill in focus and XP to its next level, this week's growing skills, and the counts; one
    skill's level and status when named."""
    from core.web_progress import skills_page

    page = skills_page(context)
    if not page.get("available"):
        return "There are no skills here yet."
    skills = page.get("skills", [])
    wanted = " ".join(str(arguments.get("skill") or "").lower().split())
    if wanted:
        found = [s for s in skills if wanted in s["name"].lower()]
        if not found:
            return f"I don't see a skill called {wanted}."
        return " ".join(f"{s['name']}: level {s['level']}, {s['xp_into_level']:,} of {s['xp_for_level']:,} XP to the "
                        f"next, {s['status']}" + (f", {s['this_week']} XP this week." if s["this_week"] else ".")
                        for s in found[:3])
    lines = []
    focus = page.get("focus") or {}
    if focus.get("name"):
        lines.append(f"In focus: {focus['name']}, {focus['to_next']:,} XP to its next level.")
    growing = sorted((s for s in skills if s["this_week"]), key=lambda s: -s["this_week"])[:5]
    if growing:
        lines.append("Growing this week: " + ", ".join(f"{s['name']} (+{s['this_week']} XP)" for s in growing) + ".")
    counts = page.get("counts", {})
    lines.append(f"{counts.get('touched', 0)} of {counts.get('skills', len(skills))} skills started, "
                 f"{counts.get('demonstrated', 0)} demonstrated.")
    return " ".join(lines)


def _action_list_rewards(context, arguments: dict) -> str:
    """Tool list_rewards: credits left, and each open reward with its cost: ready now, or how many to go."""
    from core.game_layer import shop_page

    page = shop_page(context)
    if not page.get("available"):
        return "There's no reward shop here."
    left = page["credits"]["left"]
    rewards = [r for r in page["rewards"] if r["available"]]
    if not rewards:
        return f"You have {left:,} credits and no rewards set yet. Add some in the Reward Shop."
    ready = [f"{r['name']} ({r['cost']:,})" for r in rewards if r["affordable"]]
    later = [f"{r['name']} ({r['to_go']:,} to go)" for r in rewards if not r["affordable"]]
    lines = [f"You have {left:,} credits."]
    if ready:
        lines.append("Ready now: " + ", ".join(ready) + ".")
    if later:
        lines.append("Saving for: " + ", ".join(later[:6]) + ".")
    return " ".join(lines)


def _action_buy_reward(context, arguments: dict) -> str:
    """Tool buy_reward: buys the named reward with the person's credits through shop.buy (refused there when it costs
    more than they have or was a one-time reward already claimed); undoable."""
    from core.actions import ActionError

    shop = getattr(context, "reward_shop", None)
    actions = getattr(context, "actions", None)
    if shop is None or actions is None:
        return "There's no reward shop here."
    wanted = " ".join(str(arguments.get("reward") or "").lower().split())
    found = [r for r in shop.all_rewards() if wanted and wanted in r.name.lower()]
    if len(found) != 1:
        names = ", ".join(r.name for r in (found or shop.all_rewards())[:8])
        return (f"Which one? {names}." if names else "There are no rewards set yet.")
    try:
        done = actions.approve(context, actions.propose(context, "shop.buy", {"reward_id": found[0].reward_id},
                                                        proposed_by="mia").proposal_id)
    except ActionError as problem:
        return str(problem)
    if done.status != "executed":
        return done.result or "That didn't work; nothing was spent."
    return f"{done.result} (Say “undo that” to take it back.)"


def register_progress_actions(registry: AssistantActionRegistry) -> None:
    """Registers get_character (domain character), get_skills (skills), list_rewards and buy_reward (reward_shop)."""
    registry.register_domain_keywords("character", ("character", "xp", "attributes", "buffs"))
    registry.register_domain_keywords("skills", ("skill", "skills"))
    registry.register_domain_keywords("reward_shop", ("reward", "rewards", "credits"))
    registry.register(AssistantAction(
        name="get_character", domain="character",
        description="The user's character: level, XP to the next level, credits, attributes, missions completed.",
        parameters={"type": "object", "properties": {}},
        handler=_action_get_character,
        trigger_phrases=("what level am i", "my level", "how much xp", "my character", "my attributes", "my stats"),
    ))
    registry.register(AssistantAction(
        name="get_skills", domain="skills",
        description="The user's skills: the one in focus, what grew this week, or one skill's level when named.",
        parameters={"type": "object", "properties": {
            "skill": {"type": "string", "description": "A skill's name, or empty for all of them."},
        }},
        handler=_action_get_skills,
        trigger_phrases=("which skills", "my skills", "skill tree", "what level is my", "skills am i growing"),
    ))
    registry.register(AssistantAction(
        name="list_rewards", domain="reward_shop",
        description="The user's credits and the rewards in the Reward Shop: which they can buy now and what's next.",
        parameters={"type": "object", "properties": {}},
        handler=_action_list_rewards,
        trigger_phrases=("what can i buy with my credits", "how many credits", "reward shop", "my rewards",
                         "what rewards"),
    ))
    registry.register(AssistantAction(
        name="buy_reward", domain="reward_shop",
        description="Buy a reward from the Reward Shop with the user's credits, when they ask to.",
        parameters={"type": "object", "properties": {
            "reward": {"type": "string", "description": "The reward's name, as the user said it."},
        }, "required": ["reward"]},
        handler=_action_buy_reward,
        trigger_phrases=("buy the reward", "buy a reward", "spend my credits", "cash in", "redeem"),
    ))
