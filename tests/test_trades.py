"""
tests.test_trades
===================

Trade Master's jobs and diagnoses (core/trades.py, core/trade_jobs.py, DEC-0149): every one meets the standard Zac
asked MIA be held to ("thorough and complete instructions"), the standard catches what a weak one leaves out, a job's
own words call for its stop rules, a diagnosis always ends somewhere real, and the words someone uses find the job.
"""

from dataclasses import replace

import pytest

from core import trades
from core.trades import DiagCheck, Phase, Step

trades._loaded()


@pytest.mark.parametrize("item_id", sorted(trades.JOBS) + sorted(trades.DIAGNOSES))
def test_every_job_and_diagnosis_meets_the_standard(item_id):
    """Each one written is complete before it's ever offered, and stays drafted until a person confirms it."""
    item = trades.JOBS.get(item_id) or trades.DIAGNOSES[item_id]
    assert trades.problems(item) == [], item_id
    assert item.status in (trades.DRAFTED, trades.CONFIRMED)


def test_the_standard_catches_what_a_thin_job_leaves_out():
    """A job with no hold points, a reason missing, no permit note, a step that digs with no utility locate and one
    source is refused for each of them."""
    job = trades.JOBS["chicken_coop"]
    thin = replace(job, permit="Probably fine.", sources=("A blog",), stop_if=("injury",),
                   phases=tuple(Phase(p.name, tuple(replace(s, hold="", why="ok") for s in p.steps))
                                for p in job.phases))
    found = trades.problems(thin)
    for gap in ("a permit note that points to the local building department", "a reason (why) for every step",
                "a hold point in every phase but the first, and one in the last",
                "the utilities stop rule (its steps call for it)", "at least 2 sources, each named in full"):
        assert gap in found, gap


def test_a_diagnosis_must_end_somewhere_real_and_reach_every_check():
    """A branch to nowhere, a cause naming a job that isn't written, and an unreachable check are each refused."""
    d = trades.DIAGNOSES["toilet_running"]
    broken = replace(d, checks=d.checks[:-1] + (DiagCheck("fill_valve", d.checks[-1].ask, d.checks[-1].why,
                                                          "cause:the fill valve is worn|no_such_job", "nowhere"),
                                              DiagCheck("orphan", "Is it?", "Never reached by any branch.",
                                                        "pro:a plumber, said what was found", "pro:a plumber too")))
    found = trades.problems(broken)
    assert "a cause that's named, with a written job if any (fill_valve)" in found
    assert "a branch that ends somewhere (fill_valve)" in found and "every check reachable" in found


def test_every_stop_rule_says_what_to_do_instead_and_the_words_find_the_job():
    """The rules are complete; the way someone asks finds the job or diagnosis; what's written counts toward WANTED in
    Zac's order."""
    assert all(len(r.instead) > 30 and r.when for r in trades.STOP_RULES.values())
    assert trades.find("walk me through building the coop").id == "chicken_coop"
    assert trades.find("I want to build a greenhouse").id == "hoop_house"
    assert trades.find("my toilet keeps running").id == "toilet_running"
    assert trades.find("bake a cake") is None
    d = trades.depth()
    assert d["written"] >= 5 and d["failing"] == [] and trades.WANTED[:4] == ("hoop_house", "chicken_coop",
                                                                             "workshop", "cold_room")
    assert "not yet confirmed by a person" in trades.outline(trades.JOBS["workshop"])


def test_a_new_step_is_one_place_to_add_depth():
    """Adding a step is data: a job stays to the standard as it grows."""
    job = trades.JOBS["hoop_house"]
    deeper = replace(job, phases=job.phases[:-1] + (Phase(job.phases[-1].name, job.phases[-1].steps + (
        Step("Mark the film's install date on the end wall.", "Film is rated for a set number of years; the date "
             "says when to replace it.", ("Use a paint pen.",)),)),))
    assert trades.problems(deeper) == []
