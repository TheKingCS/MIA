"""
tests.test_project_time
=========================

The hours he puts into his projects (core/project_time.py, 2026-11-25): "log 2 hours on the shed build" adds them to
that project's time log, undoable, only for a project of his; the hours are read back by project or by day; the time
log survives a save and a reload; hours on a project he doesn't have name his projects, a machine's stay its own.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from core import assistant_turn, project_time
from core.project_manager import ProjectManager


@pytest.fixture
def book(tmp_path):
    """A project book with the shed build and the deck."""
    context = SimpleNamespace(events=SimpleNamespace(publish=lambda *a, **k: None))
    projects = ProjectManager(context, data_dir=tmp_path)
    projects.add_project("Shed Build")
    projects.add_project("Back Deck")
    return projects


def _context(projects):
    """A context whose tools run the real project-time tools."""
    tools = {"log_project_time": project_time._log_tool, "project_hours": project_time._hours_tool}
    context = SimpleNamespace(projects=projects)
    context.assistant_actions = SimpleNamespace(execute=lambda c, n, a: tools[n](c, a))
    return context


def test_hours_said_in_his_words_are_read():
    assert project_time.hours_said("2 hours") == 2
    assert project_time.hours_said("an hour") == 1
    assert project_time.hours_said("half an hour") == 0.5
    assert project_time.hours_said("90 minutes") == 1.5
    assert project_time.hours_said("2 hours and a half") == 2.5
    assert project_time.hours_said("the shed") is None


def test_logging_hours_on_the_shed_build_adds_them_to_it(book):
    context = _context(book)
    said = assistant_turn._project_time_reply(context, "Log 2 hours on the shed build")
    assert said == "Logged 2 hours on Shed Build. 2 hours on it in all."
    assert assistant_turn._project_time_reply(context, "I spent 3 hours on the shed yesterday").startswith(
        "Logged 3 hours on Shed Build on ")
    shed = book.all_projects()[0]
    assert [t["hours"] for t in shed.time_log] == [2, 3]
    assert shed.time_log[1]["date"] == (date.today() - timedelta(days=1)).isoformat()
    reloaded = ProjectManager(book.context, data_dir=book.data_dir)
    assert [t["hours"] for t in reloaded.all_projects()[0].time_log] == [2, 3]


def test_hours_on_something_that_isnt_his_project_are_never_logged(book):
    """His truck's hours stay the truck's, the phone and the plant are no project, and nothing is logged."""
    context = _context(book)
    context.maintenance = SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Truck")])
    for words in ("log 2 hours on the truck", "I spent 3 hours on the phone", "I worked 8 hours at the plant"):
        assert assistant_turn._project_time_reply(context, words) is None, words
    assert all(not p.time_log for p in book.all_projects())


def test_the_hours_are_read_back_by_project_and_by_day(book):
    context = _context(book)
    assistant_turn._project_time_reply(context, "I worked on the back deck for 90 minutes")
    assert assistant_turn._project_time_reply(context, "how many hours have I put into the deck?") == \
        "1.5 hours on Back Deck in all, 1.5 this week."
    assert assistant_turn._project_time_reply(context, "what did I work on today?") == \
        "Project hours today: Back Deck 1.5."
    assert assistant_turn._project_time_reply(context, "what did I work on yesterday?") == \
        "No project hours logged yesterday."


def test_a_day_of_more_than_24_hours_is_refused(book):
    with pytest.raises(ValueError):
        book.log_time(book.all_projects()[0].project_id, 30)


def test_logging_hours_on_a_project_he_doesnt_have_names_his_projects(book):
    """Only when his words say it's a project ("the chicken coop build"); never an oven timer or the mower."""
    context = _context(book)
    context.maintenance = SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Riding Mower")])
    said = assistant_turn._project_time_reply(context, "Log 2 hours on the chicken coop build")
    assert said.startswith("I don't have a project called 'the chicken coop build'.") and "Shed Build" in said
    assert assistant_turn._project_time_reply(context, "add 30 minutes to the oven timer") is None
    assert assistant_turn._project_time_reply(context, "log 2 hours on the mower") is None  # its engine hours
    assert all(not p.time_log for p in book.all_projects())
