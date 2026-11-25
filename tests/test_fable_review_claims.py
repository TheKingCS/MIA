"""
tests.test_fable_review_claims
================================

The Fable review of the claim check (2026-11-25): a true reply is never replaced with "I didn't set that up": a
negation, a question back, how it works, words drafted for him and a story stay; a real claim of a change no tool
made is still caught.
"""

from core.claim_check import HONEST, honest


def test_true_replies_stay():
    for prompt, reply in (
            ("cancel my alarm", "No alarm is set, so there's nothing to cancel."),
            ("delete my 6 am alarm", "There isn't one: the only alarm is set for 7:30."),
            ("move my dentist appointment to Friday",
             "Which one? One appointment is scheduled for Tuesday and one for Thursday."),
            ("remind me to check the oil Saturday", "I need a time before a reminder is set. Morning or afternoon?"),
            ("remind me to call the vet", "Tell me when and I'll remind you then."),
            ("what can you do?", "When you ask for a reminder, I'll send you a notification at its time."),
            ("how do reminders work?", "When you ask, I set a reminder on your calendar and it shows up on your phone."),
            ("tell me a story", "Once, I set an alarm for dawn and the rooster beat it."),
            ("help me write a text to the contractor saying I sent the invoice",
             "Hi, I sent the invoice on Monday. I've added a note about the extra lumber. Thanks!"),
            ("what should I say to my landlord",
             'Try: "I\'ve scheduled the repair for Friday and I\'ll send you the invoice."')):
        assert honest(None, prompt, reply) == reply, prompt


def test_a_claim_no_tool_made_is_still_caught():
    assert honest(None, "remind me to check the oil Saturday", "Done! I've added a reminder for Saturday.") == HONEST
    assert honest(None, "how are you?", "I'm good. I'll remind you when your bills are due.") == "I'm good."


def test_the_reply_cleaning_keeps_what_is_meant():
    from core.response_composer import polish, without_repeats

    code = "```python\nx = 1\n\nprint(x)\n\nprint(x)\n```"
    assert polish(code, "x") == code
    assert without_repeats("2 + 2 = 4\n\n2 * 2 = 4") == "2 + 2 = 4\n\n2 * 2 = 4"
    recipe = "Dough\n\nIngredients:\n\n- flour\n\nSauce\n\nIngredients:\n\n- tomatoes"
    assert without_repeats(recipe) == recipe
    assert without_repeats("Yes.\n\nThe north bed is ready.\n\nThe south bed?\n\nYes.").endswith("Yes.")
    line = "The project you're planning: goats. It touches: money, materials, time, goals."
    assert without_repeats("\n\n".join([line] * 5)) == line  # back to back, still once
    assert polish("Absolutely not. That wire is live.") == "Absolutely not. That wire is live."


def test_the_project_picture_is_all_said_to_him():
    from core import project_ripple, question_plans as qp

    sheet = qp.Sheet("project picture", "What a project touches")
    project_ripple.gather(None, sheet, "I'm planning a garden")
    said = sheet.plain()
    assert " him" not in said and "from rain or from him" not in said and " he " not in f" {said} "
    assert not qp._not_for("projects", "which of my projects are for the shop?")


def test_a_call_in_qwens_own_tags_or_with_nothing_is_caught():
    from types import SimpleNamespace

    from core.assistant_turn import _garbled

    context = SimpleNamespace(assistant_actions=SimpleNamespace(_actions={"add_alarm": 1, "list_alarms": 1}))
    assert _garbled('<tool_call>{"name": "add_alarm", "arguments": {"time": "6:30"}}</tool_call>', context)
    assert _garbled('{"name": "list_alarms"}', context)
    assert not _garbled('{"name": "Zac", "age": 30}', context)
