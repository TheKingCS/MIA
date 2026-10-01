"""
core.assistant_homestead_actions
===================================

Assistant tools for Finance #2, homestead builds and tools
(core/homestead_costs.py): "I spent $240 on lumber for the greenhouse",
"I bought a DeWalt drill for $199 for the greenhouse", "How much have I
spent on the greenhouse?", "What has the mower cost me?", "Set the
greenhouse budget to $5,000".

A build named for the first time is created as a Project on the spot
and the reply says so, the same "find it or make it, then read it back"
shape as core/assistant_why_actions.py. Tools are Maintenance assets,
found from the user's words by core.assistant_lookup; deletes don't
exist here at all.
"""

from __future__ import annotations

from typing import Optional

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_lookup import name_tokens, resolve_by_name
from core.budget_manager import EXPENSE_CATEGORIES
from core.homestead_costs import (
    all_build_costs, all_tool_costs, build_cost, describe_build, describe_tool, record_tool_purchase, tool_cost,
)
from core.region import money

_S = {"type": "string"}
_N = {"type": "number"}


def _amount(value) -> Optional[float]:
    try:
        amount = float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def _find(items, name: str, get_name, kind: str):
    """(item, None) | (None, question) when ambiguous | (None, None) when nothing like it."""
    item, message = resolve_by_name(items, name, get_name, kind)
    if item is not None:
        return item, None
    wanted = name_tokens(name)
    if wanted and any(wanted & name_tokens(get_name(i)) for i in items):
        return None, message
    return None, None


def _find_or_create_build(context: AppContext, name: str):
    """(project, question, created)."""
    project, question = _find(context.projects.all_projects(), name, lambda p: p.name, "build")
    if project is not None or question is not None:
        return project, question, False
    clean = name.strip().rstrip(".")
    clean = clean[:1].upper() + clean[1:]
    return context.projects.add_project(clean, status="Active"), None, True


def _find_tool(context: AppContext, name: str):
    return _find(context.maintenance.all_assets(), name, lambda a: a.name, "tool")


def _unavailable(context: AppContext) -> Optional[str]:
    if context.budget is None or context.projects is None or context.maintenance is None:
        return "Build and tool costs aren't available right now."
    return None


def _action_log_build_expense(context: AppContext, arguments: dict) -> str:
    problem = _unavailable(context)
    if problem:
        return problem
    amount = _amount(arguments.get("amount"))
    build_name = str(arguments.get("build") or "").strip()
    if amount is None:
        return "How much was it?"
    if not build_name:
        return "Which build was that for?"
    project, question, created = _find_or_create_build(context, build_name)
    if project is None:
        return question
    category = str(arguments.get("category") or "Building Materials")
    if category not in EXPENSE_CATEGORIES:
        category = "Building Materials"
    asset_id = ""
    tool_name = str(arguments.get("tool") or "").strip()
    if tool_name:
        tool, _ = _find_tool(context, tool_name)
        asset_id = tool.asset_id if tool is not None else ""
    description = str(arguments.get("description") or "").strip() or f"For {project.name}"
    context.budget.add_expense(
        amount=amount, category=category, description=description, date=arguments.get("date") or None,
        project_id=project.project_id, asset_id=asset_id,
    )
    cost = build_cost(context, project)
    reply = f"Logged {money(amount, ',.2f')} for {description.lower() if description != f'For {project.name}' else 'it'} on {project.name}"
    reply += " (a new build)." if created else "."
    if cost.budget > 0:
        reply += f" {cost.name}: {money(cost.spent, ',.2f')} of {money(cost.budget, ',.2f')} spent."
    else:
        reply += f" Total so far: {money(cost.spent, ',.2f')}."
    return reply


def _action_record_tool_purchase(context: AppContext, arguments: dict) -> str:
    problem = _unavailable(context)
    if problem:
        return problem
    tool_name = str(arguments.get("tool") or "").strip()
    price = _amount(arguments.get("price"))
    if not tool_name:
        return "What tool did you buy?"
    if price is None:
        return f"What did the {tool_name} cost?"
    project_id, build_note = "", ""
    build_name = str(arguments.get("build") or "").strip()
    if build_name:
        project, question, created = _find_or_create_build(context, build_name)
        if project is None:
            return question
        project_id = project.project_id
        build_note = f" for {project.name}" + (" (a new build)" if created else "")
    existing, _ = _find_tool(context, tool_name)
    if existing is not None and existing.purchase_price == 0:
        # A tool MIA already tracks for maintenance, price never recorded.
        context.maintenance.update_asset(existing.asset_id, purchase_price=price)
        context.budget.add_expense(
            amount=price, category="Tools & Equipment", description=f"Bought {existing.name}",
            date=arguments.get("date") or None, asset_id=existing.asset_id, project_id=project_id, asset_purchase=True,
        )
        return f"Recorded {money(price, ',.2f')} for the {existing.name}{build_note}."
    category = str(arguments.get("category") or "Tool")
    if category not in ("Tool", "Power Equipment", "Vehicle", "Appliance", "Other"):
        category = "Tool"
    clean = tool_name[:1].upper() + tool_name[1:]
    asset, _ = record_tool_purchase(
        context, clean, price, category=category, project_id=project_id, purchase_date=arguments.get("date") or None,
    )
    return f"Added the {asset.name} to your tools, {money(price, ',.2f')}{build_note}. I'll track what it costs you from here."


def _action_get_build_costs(context: AppContext, arguments: dict) -> str:
    problem = _unavailable(context)
    if problem:
        return problem
    name = str(arguments.get("build") or "").strip()
    if name:
        project, question = _find(context.projects.all_projects(), name, lambda p: p.name, "build")
        if project is None:
            return question or f"I don't have a build called '{name}'."
        return describe_build(build_cost(context, project))
    costs = all_build_costs(context)
    if not costs:
        return "You haven't logged any build costs yet. Try: 'I spent $240 on lumber for the greenhouse.'"
    total = sum(c.spent for c in costs)
    lines = [f"{c.name} {money(c.spent, ',.0f')}" + (f" of {money(c.budget, ',.0f')}" if c.budget else "") for c in costs[:5]]
    return f"You've spent {money(total, ',.2f')} across {len(costs)} build{'s' if len(costs) != 1 else ''}: " + "; ".join(lines) + "."


def _action_list_build_purchases(context: AppContext, arguments: dict) -> str:
    """What was bought for a build: receipt line items where filed from the
    inbox (core/inbox_classify.receipt_items), otherwise each expense."""
    problem = _unavailable(context)
    if problem:
        return problem
    name = str(arguments.get("build") or "").strip()
    if not name:
        return "Which build?"
    project, question = _find(context.projects.all_projects(), name, lambda p: p.name, "build")
    if project is None:
        return question or f"I don't have a build called '{name}'."
    expenses = sorted((e for e in context.budget.all_expenses() if e.project_id == project.project_id), key=lambda e: e.date)
    if not expenses:
        return f"Nothing is logged for the {project.name} yet."
    lines: list[tuple[float, str]] = []
    for e in expenses:
        if e.items:
            for item in e.items:
                qty = item.get("quantity")
                text = item.get("description", "") + (f" ×{qty:g}" if qty and qty != 1 else "")
                lines.append((float(item.get("amount", 0)), f"{text} {money(float(item.get('amount', 0)), ',.2f')}"))
        else:
            lines.append((e.amount, f"{e.description or e.payee or e.category} {money(e.amount, ',.2f')}"))
    total = sum(e.amount for e in expenses)
    biggest = [text for _, text in sorted(lines, key=lambda pair: -pair[0])[:8]]
    more = f", and {len(lines) - 8} smaller" if len(lines) > 8 else ""
    return (f"For the {project.name} you've bought ({money(total, ',.2f')} in all, biggest first): "
            + "; ".join(biggest) + more + ".")


def _action_get_tool_costs(context: AppContext, arguments: dict) -> str:
    problem = _unavailable(context)
    if problem:
        return problem
    name = str(arguments.get("tool") or "").strip()
    if name:
        tool, question = _find_tool(context, name)
        if tool is None:
            return question or f"I don't have a tool called '{name}'."
        return describe_tool(tool_cost(context, tool))
    costs = all_tool_costs(context)
    if not costs:
        return "I don't have any tool costs yet. Try: 'I bought a chainsaw for $329.'"
    total = sum(c.total for c in costs)
    lines = [f"{c.name} {money(c.total, ',.0f')}" for c in costs[:5]]
    return f"Your tools and equipment have cost {money(total, ',.2f')} in all. The biggest: " + "; ".join(lines) + "."


def _action_set_build_budget(context: AppContext, arguments: dict) -> str:
    problem = _unavailable(context)
    if problem:
        return problem
    amount = _amount(arguments.get("amount"))
    name = str(arguments.get("build") or "").strip()
    if amount is None or not name:
        return "Tell me the build and the budget, like 'greenhouse, $5,000'."
    project, question, created = _find_or_create_build(context, name)
    if project is None:
        return question
    context.projects.update_project(project.project_id, budget=amount)
    cost = build_cost(context, project)
    reply = f"Set the {project.name} budget to {money(amount, ',.2f')}" + (" (a new build)." if created else ".")
    if cost.spent:
        reply += f" You've spent {money(cost.spent, ',.2f')} of it so far."
    return reply


# ---------------------------------------------------------------------------
# Finance #3: business use of personal equipment (core/business_use.py)
# ---------------------------------------------------------------------------


def _business_tool(context: AppContext, name: str):
    """(asset, question). With no name, the one tool that already has
    business use logged, if there's exactly one."""
    if name:
        tool, question = _find_tool(context, name)
        return tool, (question or (f"I don't have a tool called '{name}'." if tool is None else None))
    ids = context.business_use.assets_with_business_use()
    if len(ids) == 1:
        return context.maintenance.get_asset(ids[0]), None
    return None, "Which tool or piece of equipment was it?"


def _action_log_business_use(context: AppContext, arguments: dict) -> str:
    if getattr(context, "business_use", None) is None or context.maintenance is None:
        return "Business-use tracking isn't available right now."
    hours = _amount(arguments.get("hours"))
    miles = _amount(arguments.get("miles"))
    if hours is None and miles is None:
        return "How many hours was it (or miles, for a vehicle)?"
    tool, question = _business_tool(context, str(arguments.get("tool") or "").strip())
    if tool is None:
        return question
    purpose = "personal" if str(arguments.get("purpose") or "").lower().startswith("personal") else "business"
    for_whom = str(arguments.get("for_whom") or "").strip()
    property_id = entity_id = ""
    if for_whom and getattr(context, "real_estate", None) is not None:
        prop, _ = _find(context.real_estate.all_properties(), for_whom, lambda p: p.name, "property")
        if prop is not None:
            property_id, entity_id = prop.property_id, prop.entity_id
    business_name = str(arguments.get("business") or "").strip()
    if business_name and context.budget is not None:
        entity, _ = _find(context.budget.all_business_entities(), business_name, lambda e: e.name, "business")
        if entity is not None:
            entity_id = entity.entity_id
    entry = context.business_use.log_use(
        tool.asset_id, hours or 0.0, purpose=purpose, use_date=arguments.get("date") or None,
        entity_id=entity_id, property_id=property_id, client=for_whom, note=str(arguments.get("note") or ""),
        miles=miles or 0.0,
    )
    year = int(entry.date[:4])
    unit = "miles" if miles else "hours"
    amount = miles if miles else hours
    logged = sum(e.amount(unit) for e in context.business_use.entries_for(tool.asset_id, year) if e.purpose == purpose)
    target = f" for {for_whom}" if for_whom else ""
    singular = unit[:-1] if amount == 1 else unit
    return (
        f"Logged {amount:g} {purpose} {singular} on the {tool.name}{target}. "
        f"{year} so far: {logged:g} {purpose} {unit}."
    )


def _action_get_business_use(context: AppContext, arguments: dict) -> str:
    if getattr(context, "business_use", None) is None or context.maintenance is None:
        return "Business-use tracking isn't available right now."
    from datetime import date as _date

    from core.business_use import build_worksheet, describe_worksheet

    try:
        year = int(arguments.get("year") or _date.today().year)
    except (TypeError, ValueError):
        year = _date.today().year
    name = str(arguments.get("tool") or "").strip()
    if name:
        tool, question = _business_tool(context, name)
        if tool is None:
            return question
        tools = [tool]
    else:
        tools = [context.maintenance.get_asset(i) for i in context.business_use.assets_with_business_use()]
        tools = [t for t in tools if t is not None]
        if not tools:
            return "You haven't logged any business use yet. Try: 'I mowed the Maple duplex for 2 hours.'"
    summaries = [describe_worksheet(build_worksheet(context, tool, year)) for tool in tools[:3]]
    return " ".join(summaries) + " The full worksheet is in Budget → Builds & Tools. It's records, not tax advice."


def register_homestead_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="log_business_use", domain="business_use",
        description=(
            "Log hours a tool or piece of equipment was used for BUSINESS (a lawn-care client, one of the user's "
            "rentals, contract work), for write-off records. Only when the user says it was for business, a client "
            "or a rental; ordinary home use is not logged."
        ),
        parameters={"type": "object", "properties": {
            "tool": {**_S, "description": "The equipment, e.g. 'mower'."},
            "hours": {**_N, "description": "Hours of use (equipment)."},
            "miles": {**_N, "description": "Miles driven (a vehicle), instead of hours."},
            "for_whom": {**_S, "description": "Client or property, e.g. 'Maple duplex', 'Johnson lawn'."},
            "business": {**_S, "description": "Which of the user's businesses, if said."},
            "purpose": {**_S, "description": "'business' (default) or 'personal'."},
            "date": {**_S, "description": "YYYY-MM-DD if not today."},
            "note": {**_S, "description": "Anything else they said."},
        }, "required": []},
        handler=_action_log_business_use,
        trigger_phrases=("for business", "business use", "business hours", "lawn job", "lawn care", "mowing job",
                         "for a client", "for the client", "mowed the", "contract job", "business miles",
                         "miles for", "drove to"),
    ))
    registry.register(AssistantAction(
        name="get_business_use", domain="business_use",
        description=(
            "The business-use percentage of a tool this year, and the business share of its running costs and "
            "purchase price, from the logged business use and its hour meter. For write-off questions."
        ),
        parameters={"type": "object", "properties": {
            "tool": {**_S, "description": "The equipment, or omit for everything with business use."},
            "year": {"type": "integer", "description": "Tax year, default this year."},
        }, "required": []},
        handler=_action_get_business_use,
        trigger_phrases=("write off", "write-off", "writeoff", "deduct", "deduction", "business use", "business percentage",
                         "business share"),
    ))
    registry.register(AssistantAction(
        name="log_build_expense", domain="homestead_costs",
        description=(
            "Record money spent on one of the user's builds or projects (greenhouse, walipini, fence, shed...): "
            "materials, hardware, rentals, contractors. For buying a TOOL use record_tool_purchase instead."
        ),
        parameters={"type": "object", "properties": {
            "amount": {**_N, "description": "Dollars spent."},
            "build": {**_S, "description": "Which build, in the user's words, e.g. 'greenhouse'."},
            "description": {**_S, "description": "What it was, e.g. 'lumber', '2x4s and screws'."},
            "category": {**_S, "description": "Usually 'Building Materials'. Other options: 'Tools & Equipment', 'Maintenance', 'Other'."},
            "tool": {**_S, "description": "A tool it was for, if any (e.g. 'blades for the chainsaw')."},
            "date": {**_S, "description": "YYYY-MM-DD if not today."},
        }, "required": ["amount", "build"]},
        handler=_action_log_build_expense,
        trigger_phrases=("for the greenhouse", "for the build", "for the shed", "for the fence", "for the walipini",
                         "on the greenhouse", "on lumber", "on materials", "for the coop", "for the barn"),
    ))
    registry.register(AssistantAction(
        name="record_tool_purchase", domain="homestead_costs",
        description="Record that the user bought a tool or piece of equipment, what it cost, and which build it was for if they said.",
        parameters={"type": "object", "properties": {
            "tool": {**_S, "description": "The tool, e.g. 'DeWalt drill', 'chainsaw'."},
            "price": {**_N, "description": "What it cost in dollars."},
            "build": {**_S, "description": "The build it was bought for, if said."},
            "category": {**_S, "description": "'Tool' (default), 'Power Equipment', or 'Vehicle'."},
            "date": {**_S, "description": "YYYY-MM-DD if not today."},
        }, "required": ["tool", "price"]},
        handler=_action_record_tool_purchase,
        trigger_phrases=("bought a", "i bought", "picked up a", "just bought", "purchased a"),
    ))
    registry.register(AssistantAction(
        name="get_build_costs", domain="homestead_costs",
        description="How much the user has spent on a build (vs its budget), or on all builds.",
        parameters={"type": "object", "properties": {"build": {**_S, "description": "One build, or omit for all."}}, "required": []},
        handler=_action_get_build_costs,
        trigger_phrases=("spent on the", "have i spent on", "build costs", "cost of the build", "over budget on", "under budget on",
                         "how much has the"),
    ))
    registry.register(AssistantAction(
        name="list_build_purchases", domain="homestead_costs",
        description="List what the user has bought for a build (receipt items, biggest first).",
        parameters={"type": "object", "properties": {"build": {**_S, "description": "The build, e.g. 'greenhouse'."}},
                    "required": ["build"]},
        handler=_action_list_build_purchases,
        trigger_phrases=("did i buy for", "have i bought for", "what did i get for", "materials for the", "bought for the"),
    ))
    registry.register(AssistantAction(
        name="get_tool_costs", domain="homestead_costs",
        description="What a tool or piece of equipment has cost the user in total (purchase plus upkeep), or all tools.",
        parameters={"type": "object", "properties": {"tool": {**_S, "description": "One tool, or omit for all."}}, "required": []},
        handler=_action_get_tool_costs,
        trigger_phrases=("cost me", "costs me", "cost of ownership", "tool costs", "my tools cost", "spent on tools",
                         "cost per hour", "cost an hour"),
    ))
    registry.register(AssistantAction(
        name="set_build_budget", domain="homestead_costs",
        description="Set how much the user plans to spend on a build.",
        parameters={"type": "object", "properties": {
            "build": {**_S, "description": "The build, e.g. 'greenhouse'."},
            "amount": {**_N, "description": "The budget in dollars."},
        }, "required": ["build", "amount"]},
        handler=_action_set_build_budget,
        trigger_phrases=("budget for the", "build budget"),
    ))
    registry.register_domain_keywords("homestead_costs", ("lumber", "2x4s", "2x4", "rebar", "concrete"))
    registry.register_entity_names(
        "homestead_costs",
        lambda ctx: [p.name for p in ctx.projects.all_projects()] if getattr(ctx, "projects", None) else [],
    )
