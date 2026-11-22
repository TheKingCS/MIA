"""
tests.test_lab_push
=====================

WP-12 (Q-100, DEC-0264): her merged changes are pushed to GitHub with the daily summary, only hers, never forced or
rebased, held when anything else is waiting or GitHub has newer commits, and never from the test suite itself.
"""
from types import SimpleNamespace

from core import lab_push


class _Git:
    """A pretend git: answers by the command's first words; records what ran."""

    def __init__(self, branch="master", log="", newer="0", push_ok=True):
        """What this repository looks like."""
        self.branch, self.log, self.newer, self.push_ok = branch, log, newer, push_ok
        self.ran = []

    def __call__(self, *args):
        """One git command."""
        self.ran.append(args[0])
        if args[0] == "rev-parse":
            return 0, self.branch
        if args[0] == "log":
            return 0, self.log
        if args[0] == "fetch":
            return 0, ""
        if args[0] == "rev-list":
            return 0, self.newer
        if args[0] == "push":
            return (0, "") if self.push_ok else (1, "rejected")
        return 1, "unknown"


HERS = ("a1\tMIA Lab\tlab: tidy the greenhouse alert\n"
        "b2\tTheKingCS\tFrom the lab: tidy the greenhouse alert (p-0042)\n"
        "c3\tTheKingCS\tRevert \"From the lab: tidy the greenhouse alert (p-0042)\"")


def test_only_her_own_commits_are_pushed():
    """Her commits, the merges of them and their Undo are hers; anyone else's isn't."""
    assert lab_push.hers("MIA Lab", "lab: x") and lab_push.hers("TheKingCS", "From the lab: x (p-1)")
    assert lab_push.hers("TheKingCS", 'Revert "From the lab: x (p-1)"')
    assert not lab_push.hers("TheKingCS", "WP-12: something of Claude's") and not lab_push.hers("Claude", "Fix a bug")


def test_her_waiting_merges_are_pushed_without_force():
    """Three of hers waiting, GitHub with nothing newer: pushed as they are, to master."""
    git = _Git(log=HERS)
    assert lab_push.push(git) == {"pushed": 3}
    assert git.ran.count("push") == 1


def test_nothing_waiting_asks_nothing_of_the_network():
    """No commit waiting: no fetch, no push."""
    git = _Git(log="")
    assert lab_push.push(git) == {"pushed": 0} and "fetch" not in git.ran and "push" not in git.ran


def test_anything_not_hers_holds_the_push_for_its_owner():
    """One of Claude's or Zac's commits waiting: nothing is pushed past it."""
    git = _Git(log=HERS + "\nd4\tClaude\tWP-12: her merges pushed")
    held = lab_push.push(git)
    assert "not hers" in held["held"] and "push" not in git.ran and "fetch" not in git.ran


def test_newer_commits_on_github_or_another_branch_hold_it():
    """Never a rebase or a force: it waits until the running copy has GitHub's commits; off master it does nothing."""
    git = _Git(log=HERS, newer="2")
    assert "newer" in lab_push.push(git)["held"] and "push" not in git.ran
    assert lab_push.push(_Git(branch="lab-branch", log=HERS)) == {"held": "the running copy isn't on master"}
    assert "push failed" in lab_push.push(_Git(log=HERS, push_ok=False))["error"]


def test_the_outcome_is_kept_and_the_suite_never_uses_the_real_git():
    """With the daily summary: kept in lab.pushed when something was tried; under pytest the real git isn't run."""
    kept = {}
    context = SimpleNamespace(config=SimpleNamespace(set=kept.__setitem__, save=lambda: None))
    assert lab_push.run(context, git=_Git(log=HERS))["pushed"] == 3 and kept["lab.pushed"]["pushed"] == 3
    assert lab_push.run(context) == {"pushed": 0}  # the real git, inside the suite: never


def test_the_push_rule_is_out_of_her_reach():
    """On the lab's protected list, so a change of hers can't widen what may be pushed."""
    from core.dev_lab import PROTECTED

    assert "core/lab_push.py" in PROTECTED
