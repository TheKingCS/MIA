"""
core.insurance_actions
========================

The insurance check-up's changes (DEC-0034, core/insurance.py) on the
action contract: policies and quotes are records (add, edit, delete,
undoable); then drafting a quote request (MIA drafts, you press Send),
"Switch To This" (a mission with the steps, no gap in coverage) and "I
Switched" (the policy becomes the quote; what it saves goes in the
history). Grown-ups only.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.insurance import EVERY, KINDS, annual, compare, quote_request
from core.record_actions import Field, Record, record_kinds

COVERAGE_HELP = "Coverage, one per line (Bodily injury: 100,000/300,000)"

POLICY = Record("insurance_policy", "policy", "policy_id", "get_policy", "add_policy", "update_policy", "delete_policy",
                store="insurance", title_attrs=("name", "insurer"), delete_note="Its quotes go with it.", fields=(
                    Field("kind", "Kind", "choice", True, options=KINDS, default="Car"),
                    Field("insurer", "Insurer", "text", True),
                    Field("premium", "Premium", "money", True),
                    Field("every", "Paid every", "choice", options=EVERY, default="6 Months", say="paid every"),
                    Field("renews", "Renews on", "date", say="renews"),
                    Field("deductible", "Deductible", "money"),
                    Field("coverage", COVERAGE_HELP, "textarea"),
                    Field("asset_id", "What it covers (optional)", "asset", say="covers"),
                    Field("name", "Name (like Truck insurance)", "text", say="name"),
                    Field("last_premium", "Last term's premium (to see the change)", "money", say="last term"),
                    Field("policy_number", "Policy number", "text", say="policy number"),
                    Field("agent_email", "Agent's email (for quote requests)", "text", say="agent's email"),
                    Field("note", "Note", "textarea"),
                ))

QUOTE = Record("insurance_quote", "quote", "quote_id", "get_quote", "add_quote", "update_quote", "delete_quote",
               store="insurance", title_attrs=("name", "insurer"), fields=(
                   Field("policy_id", "For which policy", "pick", True, options=("policies",)),
                   Field("insurer", "Insurer", "text", True),
                   Field("premium", "Premium", "money", True),
                   Field("every", "Paid every", "choice", options=EVERY, default="6 Months", say="paid every"),
                   Field("deductible", "Deductible", "money"),
                   Field("coverage", COVERAGE_HELP, "textarea"),
                   Field("received", "Received on", "date", say="received"),
                   Field("note", "Note", "textarea"),
               ))


def forms() -> dict:
    from core.record_actions import record_form

    return {"policy": record_form(POLICY), "quote": record_form(QUOTE)}


def _policy(context, params):
    policy = _need(context, "insurance").get_policy(str(params.get("policy_id") or ""))
    if policy is None:
        raise ActionError("That policy isn't there anymore.")
    return policy


def _quote(context, params):
    book = _need(context, "insurance")
    quote = book.get_quote(str(params.get("quote_id") or ""))
    if quote is None:
        raise ActionError("That quote isn't there anymore.")
    return quote, book.get_policy(quote.policy_id)


def _money(value) -> str:
    from core.region import money

    return money(value)


# -- the quote request (MIA drafts; you press Send)

def _describe_request(context, params) -> str:
    policy = _policy(context, params)
    if getattr(context, "email_drafts", None) is None:
        raise ActionError("Email drafts aren't available here.")
    to = f" to {policy.agent_email}" if policy.agent_email else " (put in who it goes to when you send it)"
    return f"Draft a quote request for your {policy.name.lower()}, with your current coverage,{to}. You press Send"


def _request(context, params) -> str:
    to, subject, body = quote_request(context, _policy(context, params))
    context.email_drafts.create(to, subject, body)
    return "Drafted. Check it, then Send, Copy or open it in your mail app. Ask a few insurers."


# -- choosing a quote, then switching

STEPS = ("Get the new policy's start date and documents", "Make sure the new one starts before the old one ends (no gap)",
         "Cancel the old policy for the day the new one starts", "Ask the old insurer to refund any unused premium",
         "Put the new insurance card in the car or the new policy in your files")


def _describe_choose(context, params) -> str:
    quote, policy = _quote(context, params)
    cmp = next(q for q in compare(policy, [quote])["quotes"])
    saves = f", saving {_money(cmp['saves'])} a year" if cmp["saves"] > 0 else ""
    less = f". It covers less: {'; '.join(cmp['covers_less'])}" if cmp["covers_less"] else ""
    return f"Switch your {policy.name.lower()} to {quote.insurer}{saves}{less}. MIA makes a mission with the steps"


def _choose(context, params) -> str:
    quote, policy = _quote(context, params)
    missions = getattr(context, "missions", None)
    if missions is not None:
        mission = missions.add_mission(f"Switch {policy.name.lower()} to {quote.insurer}", icon="☂️",
                                       summary="Start the new policy before cancelling the old one, so there's never a gap.",
                                       reward_xp=40, profile_id=getattr(context, "profile_id", None))
        for step in STEPS:
            missions.add_objective(mission.mission_id, step, "tally", 1.0)
    context.insurance.update_policy(policy.policy_id, chosen_quote_id=quote.quote_id)
    return "Your switching mission is in Missions. When it's done, press I Switched on the policy."


def _describe_switched(context, params) -> str:
    quote, policy = _quote(context, params)
    saved = annual(policy.premium, policy.every) - annual(quote.premium, quote.every)
    said = f" ({_money(saved)} a year less)" if saved > 0 else ""
    return (f"You switched your {policy.name.lower()} to {quote.insurer}: {_money(quote.premium)} every "
            f"{quote.every.lower()}{said}. Its quotes are cleared")


def _switched(context, params) -> str:
    from core import life_events

    quote, policy = _quote(context, params)
    insurer = quote.insurer
    try:
        policy, saved = context.insurance.switched(policy.policy_id, quote.quote_id)
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    summary = f"Switched {policy.name.lower()} to {insurer}" + (f": saves {_money(saved)} a year" if saved > 0 else "")
    life_events.record(context.insurance, "insurance_switched", summary, [f"policy:{policy.policy_id}"],
                       {"saved_per_year": saved, "insurer": insurer})
    return summary + ". Put in the new renewal date when the policy comes."


def _register() -> None:
    kinds = record_kinds(POLICY) + record_kinds(QUOTE) + [
        ActionType("insurance.request", "Draft A Quote Request", {"policy_id": "the policy"}, _describe_request, _request),
        ActionType("insurance.choose", "Switch To This", {"quote_id": "the quote"}, _describe_choose, _choose),
        ActionType("insurance.switched", "I Switched", {"quote_id": "the quote"}, _describe_switched, _switched),
    ]
    for kind in kinds:
        ACTION_TYPES[kind.kind] = kind


_register()
