"""
tests.test_fable_review_routes
================================

The Fable review of the code routes that write (2026-11-25): each acts only on a sentence it reads whole, and
anything else (another day, a debt, a retraction, a price with a quote, a non-job after "needs", a project named in
part) goes to the model, which can ask. Every sentence the review found misread is here, with what Fable's check of
the fixes found they then refused and shouldn't (ground beef, a tune up, the coop's hours), the claim check's own
doing caught again, and the briefing turned off politely.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from core import assistant_turn as turn


def _recorder(**stores):
    """A context whose tools only record what they'd run."""
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "ok"),
                              **stores)
    return ran, context


def test_spending_it_cant_read_whole_is_never_recorded():
    ran, context = _recorder()
    for words in ("I paid $300 on my student loans", "I paid $200 on my credit cards", "I paid $1200 for the mortgages",
                  "I paid $300 for the car payment", "I paid $500 on the truck", "I dropped $20 on the floor",
                  "I spent $30 on groceries two days ago", "I spent $30 on groceries on November 20",
                  "I spent $30 on groceries on the 20th", "I spent $300 on tools last month",
                  "I spent $300 on tools last year", "I spent $40 on gas last night",
                  "paid $50 for firewood delivery tomorrow", "I spent $30 on groceries, scratch that",
                  "I spent $4 on stamps at the post office"):
        assert turn._spent_reply(context, words) is None, words
    assert ran == []


def test_spending_its_category_reads_right():
    ran, context = _recorder()
    for words, category in (("I spent $40 on chicken wire", "Building Materials"),
                            ("I spent $300 on the chicken coop", "Building Materials"),
                            ("I spent $25 on a board game", "Entertainment"),
                            ("I spent $12 on hay fever medicine", "Medical"),
                            ("I spent $30 on groceries", "Groceries")):
        turn._spent_reply(context, words)
        assert ran[-1][1]["category"] == category, words


def test_a_reminders_day_is_the_one_after_the_task():
    ran, context = _recorder()
    turn._reminder_reply(context, "remind me to send the invoice by Friday on Monday")
    day = date.fromisoformat(ran[-1][1]["date"])
    assert day.weekday() == 0 and day > date.today()
    turn._reminder_reply(context, "remind me to plan for this Friday on Thursday")
    assert date.fromisoformat(ran[-1][1]["date"]).weekday() == 3


def test_a_quote_with_more_than_the_job_is_the_models():
    ran, context = _recorder()
    for words in ("make a quote for Sarah's 12 by 16 deck for $4,800",
                  "make a quote for Sarah's 12 by 16 deck with 20 hours of labor at 40 an hour",
                  "do a quote for a 12 by 16 deck and a 200 foot fence for Sarah",
                  "make an estimate for the 10x12 shed I want to build",
                  "write a quote for an 8 by 10 chicken coop repair"):
        assert turn._job_quote_reply(context, words) is None, words


def test_a_need_is_a_task_only_for_an_upkeep_job():
    ran, context = _recorder(maintenance=SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Truck"),
                                                                              SimpleNamespace(name="Tractor")]))
    for words in ("the truck needs no work", "my truck needs me", "the truck needs a name",
                  "the tractor needs a bigger shed", "the truck needs brakes I think"):
        assert turn._upkeep_reply(context, words) is None, words
    assert not any(n == "add_maintenance_task" for n, _ in ran)


def test_project_hours_only_for_his_project_whole_and_a_day_it_reads():
    """Another day, the phone about the deck, a timer, practice or 99999 hours never logs anything."""
    from core import project_time

    projects = [SimpleNamespace(name="Garden Fence", project_id="g", time_log=[]),
                SimpleNamespace(name="Deck", project_id="d", time_log=[])]
    ran, context = _recorder(projects=SimpleNamespace(all_projects=lambda: projects))
    for words in ("I spent 3 hours on the deck on Saturday", "I spent 3 hours on the deck last week",
                  "I spent 3 hours on the deck two days ago", "I spent 2 hours on the phone about the deck",
                  "log 99999 hours on the deck", "add 10 minutes to my alarm", "log 30 minutes for guitar practice",
                  "log 30 minutes on the treadmill", "add an hour to the roast"):
        assert turn._project_time_reply(context, words) is None, words
    assert ran == []
    assert project_time.hours_said("2 hours 30 minutes") == 2.5
    assert project_time.hours_said("2 and a half hours") == 2.5
    assert project_time.hours_said("ten hours") == 10
    assert project_time.hours_said("log extra hours") is None


def test_a_day_has_24_hours_across_his_projects(tmp_path):
    import pytest

    from core.project_manager import ProjectManager

    book = ProjectManager(SimpleNamespace(events=SimpleNamespace(publish=lambda *a, **k: None)), data_dir=tmp_path)
    shed = book.add_project("Shed")
    deck = book.add_project("Deck")
    book.log_time(shed.project_id, 20)
    with pytest.raises(ValueError):
        book.log_time(deck.project_id, 20)


def test_a_date_that_cant_be_read_or_doesnt_exist_is_asked():
    from core import calendar_move
    from core.budget_manager import ExpenseEntry

    assert calendar_move.event_day("2026-02-30") is None
    assert calendar_move.day_of("on 2026-02-30") is None
    healed = ExpenseEntry.from_dict({"amount": 5, "date": "null", "created_at": "2026-11-24T10:00:00"})
    assert healed.date == "2026-11-24"


def test_what_the_narrowing_had_refused_and_shouldnt():
    ran, context = _recorder()
    for words in ("I spent $40 on ground beef", "I spent $25 on floor mats", "I spent $90 on a week of groceries",
                  "I spent $8 on playing cards"):
        assert turn._spent_reply(context, words) == "ok", words
    ran, context = _recorder(maintenance=SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Truck")]))
    for words in ("the truck needs a tune up", "the truck needs a new clutch", "the truck needs a new windshield"):
        assert turn._upkeep_reply(context, words) == "ok", words
    projects = [SimpleNamespace(name="Chicken Coop", project_id="c", time_log=[]),
                SimpleNamespace(name="Kitchen Floor", project_id="k", time_log=[])]
    ran, context = _recorder(projects=SimpleNamespace(all_projects=lambda: projects))
    for words in ("I worked on the coop for an hour", "log 2 hours on the kitchen floor"):
        assert turn._project_time_reply(context, words) == "ok", words


def test_the_claim_check_still_catches_her_own_false_doing():
    from core.claim_check import HONEST, honest

    for prompt, reply in (("remind me to call the vet tomorrow", "I'll remind you before your appointment."),
                          ("remind me to call the vet tomorrow", "I'll remind you when you get home."),
                          ("remind me to call the vet tomorrow",
                           "I've added a reminder to your calendar so you will not forget."),
                          ("add milk to my list", "I've added milk to your list, nothing else."),
                          ("set an alarm for 6", "Your alarm is set for 6:00 AM. Want me to add a label?"),
                          ("remind me tomorrow", "I've set a reminder for tomorrow. Is there anything else you need?"),
                          ("i got a text from the vet, my appointment is friday at 3", "I've added it to your calendar."),
                          ("write a note that the hens need grit", "I've saved the note.")):
        assert honest(None, prompt, reply) != reply, (prompt, reply)


def test_the_briefing_can_be_turned_off_politely():
    from core import morning_briefing as mb

    for words in ("can you stop the morning briefing", "would you cancel my morning briefing",
                  "please stop the morning briefing, I don't need it"):
        assert mb.asked(words) == ("off", None), words
    assert mb.asked("can you set up a morning briefing at 7?") == ("on", 7)
    assert mb.asked("every morning tell me the forecast and my schedule") == ("on", 7)
