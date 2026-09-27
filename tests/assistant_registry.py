"""
tests.assistant_registry
==========================

Builds the real desktop Assistant action registry (exactly what
core/application.py registers) without booting Qt or any managers, and
reports how a prompt would be routed. Shared by the routing tests and
the audit script. `demo_context()` supplies realistic record names
(a mower, tomato beds, a venison chili recipe…), because matching on the
user's own records is part of routing.
"""

from __future__ import annotations

from types import SimpleNamespace

from core.assistant_actions import AssistantActionRegistry
from core.assistant_chat import looks_like_how_to_question, looks_like_teaching_request


def build_desktop_registry() -> AssistantActionRegistry:
    from core.app_context import AppContext
    from core.application import MIAApplication
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus

    app = MIAApplication.__new__(MIAApplication)
    app.context = AppContext(config=ConfigManager(), events=EventBus())
    app.config = app.context.config
    app._register_assistant_actions()
    return app.context.assistant_actions


def _named(*names):
    return [SimpleNamespace(name=n) for n in names]


def demo_context() -> SimpleNamespace:
    """Just enough of an AppContext for the entity-name providers."""
    return SimpleNamespace(
        maintenance=SimpleNamespace(all_assets=lambda: _named(
            "Riding Mower", "Pickup Truck", "Chainsaw", "Tomato Bed", "Pepper Plants", "Blueberry Bushes",
        )),
        budget=SimpleNamespace(all_debts=lambda: _named("Chase Freedom", "Capital One Quicksilver", "Truck Loan")),
        kitchen=SimpleNamespace(
            all_recipes=lambda: _named("Venison Chili", "Garden Omelette"),
            all_pantry_items=lambda: _named("Flour", "Rice"),
            all_grocery_items=lambda: [SimpleNamespace(name=n, checked=False) for n in ("Eggs", "Milk")],
        ),
        components=SimpleNamespace(all_components=lambda: [
            SimpleNamespace(name="Resistor", value="10k"), SimpleNamespace(name="LED", value="Red"),
        ]),
        materials=SimpleNamespace(all_materials=lambda: _named("Plywood", "Pine 2x4")),
        products=SimpleNamespace(all_products=lambda: _named("Cutting Board", "Birdhouse")),
        workout=SimpleNamespace(all_exercises=lambda: _named("Back Squat", "Bench Press", "Deadlift")),
        relationships=SimpleNamespace(all_people=lambda: _named("Sarah", "Uncle Ray"), all_pets=lambda: _named("Biscuit")),
        recurring_missions=SimpleNamespace(all_templates=lambda: [
            SimpleNamespace(name=n, category="Household", active=True) for n in ("Laundry", "Dishes")
        ]),
        classroom=SimpleNamespace(
            all_subjects=lambda: [SimpleNamespace(name="Electrical", subject_id="s1")],
            courses_for_subject=lambda sid: [SimpleNamespace(name="Residential Wiring", course_id="c1")],
            lessons_for_course=lambda cid: _named("Circuit Breakers", "GFCI Outlets"),
        ),
    )


def offered_tools(registry: AssistantActionRegistry, prompt: str, context=None) -> list[str]:
    """The tool names build_chat_request() would attach for `prompt`."""
    if looks_like_teaching_request(prompt) or looks_like_how_to_question(prompt):
        return []
    return [a.name for a in registry.matching_actions(prompt, context)]
