"""The Chronicle (DEC-0028): each week (and year) told as a story from
what really happened. Never made up, never a failure."""

from datetime import date

from core.chronicle import chronicle_page, tell, week_bounds, week_chapter
from tests.engine_world import build_world


def test_week_bounds_and_telling():
    assert week_bounds(date(2026, 10, 17)) == (date(2026, 10, 12), date(2026, 10, 18))
    quiet = tell([])
    assert quiet["name"] == "A Quiet Week" and "Rest counts too" in quiet["story"][0]
    items = [("2026-10-13", "training", "Worked out: Push day"), ("2026-10-14", "training", "Worked out: Legs"),
             ("2026-10-15", "quests", "Completed the mission Clean the garage"), ("2026-10-15", "journal", "")]
    told = tell(items)
    assert told["name"] == "The Training Week"
    assert told["story"] == ["This was a week of sweat.", "You trained twice.", "You finished 1 mission.",
                             "You wrote 1 journal entry."]
    assert told["highlights"][0] == "Completed the mission Clean the garage" and "" not in told["highlights"]
    saturday = week_chapter(items, date(2026, 10, 12), date(2026, 10, 17))
    sunday = week_chapter(items, date(2026, 10, 12), date(2026, 10, 18))
    assert saturday["so_far"] and saturday["name"] == "The Training Week So Far" and saturday["title"] == "Week 42"
    assert sunday["ready"] and sunday["name"] == "The Training Week" and sunday["dates"] == "Oct 12–18"


def test_the_chronicle_from_real_history(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    for _ in range(3):
        world.workout.add_session(duration_minutes=30)
    world.fitness.log_food("lunch", "Chicken bowl")
    page = chronicle_page(world)
    week = page["this_week"]
    assert week["total"] == 4 and week["story"][1] == "You trained 3 times." and "You logged what you ate on 1 day." in week["story"]
    assert all(h.startswith("Worked out") for h in week["highlights"])  # meals eaten are never highlights
    assert page["weeks"] == []  # nothing before this week yet
    year = page["years"][0]
    assert year["so_far"] or year["ready"]
    assert year["story"][0] == "This was a year of sweat."
    assert year["name"] == "The Training Year" and "Your biggest week was Week" in year["story"][-1]
    # Undone things are left out of the story.
    from core import life_events

    first = life_events.events_for(world, types=["workout_logged"])[0]
    life_events.record(world.workout, "undone", "Undid a workout", payload={"reverses": [first.event_id]})
    assert chronicle_page(world)["this_week"]["story"][1] == "You trained twice."



def test_the_yearly_edition_grows_from_the_kept_months():
    """Step 17: each month core/seasons.py keeps as it closes, in the year's edition, oldest first."""
    from core.chronicle import months_of

    kept = {"2026-10": {"lines": ["Nothing recorded in October.", "You trained 12 times, 4 more than September.",
                                  "Eggs: 210", "Money in: 4,000", "A new thing: pickleball"]},
            "2026-09": {"lines": ["You trained 8 times."]}, "2025-12": {"lines": ["Last year's"]},
            "2026": {"lines": ["the year"]}}
    assert months_of(kept, 2026) == [
        {"month": "September", "lines": ["You trained 8 times."]},
        {"month": "October", "lines": ["You trained 12 times, 4 more than September.", "Eggs: 210", "Money in: 4,000"]}]
    assert months_of({}, 2026) == []
