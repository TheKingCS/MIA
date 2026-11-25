"""
tests.test_tax_question_reaches_its_tool
==========================================

A tax set-aside question about the business is tax_set_aside's (live sweep, 2026-11-25): "how much should I set
aside for taxes on my side business?" had gone to the business month's plan ("check with a professional"), and "how
much do I owe in quarterly taxes?" matched no tool; the business month's own questions stay its.
"""

from core.question_plans import NOT_FOR


def test_a_tax_question_is_not_the_business_months_and_its_tool_knows_the_words():
    import logging

    logging.disable(50)
    import tests.live_model_check as live

    assert NOT_FOR["business month"].search("How much should I set aside for taxes on my side business?")
    assert not NOT_FOR["business month"].search("How's the business doing this month?")
    registry = live._build_context().assistant_actions
    lowered = " how much do i owe in quarterly taxes? "
    assert any(p in lowered for p in registry._actions["tax_set_aside"].trigger_phrases)
