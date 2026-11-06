"""MIA's weekly self-report and the standing mission (build plan step 6): what got better and what's slipping,
from the loops' own history; Sundays, to the PC's owner only, through the gate; the "Keep MIA healthy" mission
works the loops' tasks."""

from datetime import datetime
from types import SimpleNamespace

from core import loops, self_report, work_runner
from core.work_tasks import Task


def test_what_got_better_and_what_slipped():
    history = {
        "dev.vulnerable": [{"at": "2026-11-01T00:00:00", "state": "below"}, {"at": "2026-11-06T00:00:00", "state": "ok"}],
        "gate.dismissed": [{"at": "2026-11-01T00:00:00", "state": "ok"}, {"at": "2026-11-05T00:00:00", "state": "slid"}],
        "pc.disk": [{"at": "2026-11-01T00:00:00", "state": "ok"}, {"at": "2026-11-06T00:00:00", "state": "ok"}],
        "dev.new": [{"at": "2026-11-05T00:00:00", "state": "below"}],  # no reading before the week: not a change
        "dev.thin": [{"at": "2026-11-01T00:00:00", "state": "below"}, {"at": "2026-11-06T00:00:00", "state": "thin"}],
    }
    assert self_report.changes(history, "2026-11-03T00:00:00") == (["dev.vulnerable"], ["gate.dismissed"])


def profiles(*made):
    return SimpleNamespace(list_profiles=lambda: [SimpleNamespace(profile_id=p, created_at=c) for p, c in made])


def test_sundays_to_the_owner_only(monkeypatch):
    import core.person_settings as ps

    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    monkeypatch.setattr(self_report, "report", lambda now=None: "Better: dev.vulnerable.")
    sunday, monday = datetime(2026, 11, 8, 18), datetime(2026, 11, 9, 18)
    context = SimpleNamespace(profiles=profiles(("kid", "2026-10-02"), ("zac", "2026-10-01")))
    monkeypatch.setattr(ps, "person_id", lambda c: "zac")
    offered = self_report.offer(context, sunday)
    assert offered[0].topic == "self_report" and offered[0].message == "Better: dev.vulnerable."
    assert self_report.offer(context, monday) == []
    monkeypatch.setattr(ps, "person_id", lambda c: "kid")
    assert self_report.offer(context, sunday) == []  # not the PC's owner
    monkeypatch.setattr(loops, "_has_repo", lambda: False)
    monkeypatch.setattr(ps, "person_id", lambda c: "zac")
    assert self_report.offer(context, sunday) == []  # the phone: no development here


def test_the_standing_mission_works_the_loops_tasks(tmp_path):
    m = work_runner.Mission(id="M-0001", goal="Keep MIA healthy", scope=["core/"], takes=["loop:", "night:"])
    work_runner.save(m, tmp_path)
    again = work_runner.missions(tmp_path)["M-0001"]
    assert again.takes == ["loop:", "night:"]
    assert again.works(Task(id="T-1", title="x", source="loop:dev.suite"))
    assert again.works(Task(id="T-2", title="x", source="M-0001"))
    assert not again.works(Task(id="T-3", title="x", source="docs/ROADMAP.md"))
