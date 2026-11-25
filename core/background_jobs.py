"""
core.background_jobs
======================

Everything MIA does on a schedule, with no window needed (the MIA Runtime,
DEC-0155; steps 1 and 3 of
`docs/mia_os/preliminary/MIA_OS_INITIAL_IMPLEMENTATION_PLAN.md`).

What it is: the periodic jobs (`JOBS`: alarms, the battery, the daily
checks, the watched folders, the inbox and its mail, the connection,
missions she assigns, and since 2026-11-15 World Intelligence's watches,
DEC-0170) and the daily checks one of them runs; the `homeostasis` property
(core/homeostasis.py, DEC-0173) decides which deferrable ones wait
(`DAILY_CHECKS`: birthdays, the calendar, insights, the Loop, the nightly
backup and the rest). Until 2026-11-15 these were methods of the desktop
window's `MIAApplication` on ten `QTimer`s, so closing the window stopped
reminders and backups. They were moved here unchanged; this file imports
nothing from Qt, `gui/` or `modules/`.

How it's used:
- `BackgroundJobs(context)` holds the jobs for one MIA. `schedule()` puts
  them on a `core.scheduler.Scheduler` with their intervals.
- The desktop (`core/application.py`): `MIAApplication` *is* a
  `BackgroundJobs` (it inherits these methods, so the tests that call
  `MIAApplication._check_...` still do), and one `QTimer` asks the
  scheduler for what's due, on the window's own thread as before.
- A headless runtime calls `Scheduler.run_forever()` on a thread instead.

The rules the jobs keep:
- Every job runs under the store lock or not at this moment (the
  scheduler's rule; `_while_stores_free` is the same rule for one slot).
- A daily check never notifies directly: it offers what it would say
  (`_offer`), and the tick's offers go through the communication gate
  together (`_check_daily_occasions`).
- One failing check never stops the others.

`tests/test_background_jobs.py` pins both lists, so a job or a check can't
be lost on the way to MIA OS.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Callable, Optional

from core.budget_nudges import build_nudge_message
from core.communication_gate import AMBIENT, Candidate, TIMELY
from core.daily_occasions import (
    calendar_events_today,
    is_birthday_today,
    should_run_once_daily,
    should_send_checkin,
)
from core.inbox_manager import describe_new_items
from core.journal_reflection import reflection_due, reflection_notice
from core.maintenance_insights import format_maintenance_insights_message, scan_maintenance_insights
from core.mission_insights import format_mission_insights_message, scan_mission_insights
from core.mission_patterns import format_pattern_insights_message, scan_pattern_insights
from core.online_watch import CAME_BACK, WENT_OFFLINE, transition_message
from core.skill_patterns import (
    format_skill_decline_insights_message,
    format_skill_momentum_insights_message,
    format_skill_pattern_insights_message,
    scan_skill_decline_insights,
    scan_skill_momentum_insights,
    scan_skill_pattern_insights,
)
from core.smart_suggestions import build_smart_suggestions_message, build_walkthrough_suggestion
from core.warranty_watch import due_notices, warranty_message
from core.logger import get_logger

log = get_logger(__name__)

# The periodic jobs: (name, seconds between runs, the method that runs it). The intervals are the old timers'.
JOBS: tuple[tuple[str, int, str], ...] = (
    ("alarms", 20, "_check_alarms"),  # no HH:MM minute is ever skipped between polls
    ("power", 30, "_check_power"),  # a low-battery warning, whichever screen is open
    ("daily_occasions", 300, "_check_daily_occasions"),  # the once-a-day checks (DAILY_CHECKS)
    ("finance_snapshots", 60, "_check_finance_snapshots"),  # a dropped export in the watched folder
    ("homestead_snapshots", 60, "_check_homestead_snapshots"),
    ("lite_captures", 60, "_check_lite_captures"),  # field captures from MIA Lite
    ("inbox", 30, "_check_inbox"),  # dropped, uploaded and emailed files; finished OCR
    ("inbox_mail", 600, "_check_inbox_mail"),  # the mailbox, when set up and unlocked
    ("online", 60, "_check_online"),  # the connection dropping or returning; "remind me when I'm back online"
    ("mission_auto_assignment", 300, "_check_mission_auto_assignment"),
    ("world_intel", 600, "_check_world_intel"),  # World Intelligence: due watches run, new finds offered (DEC-0170)
    ("self_repair", 300, "_check_self_repair"),  # she restarts Ollama, reloads her model, re-runs a stuck job (DEC-0222)
    ("activity_watch", 30, "_check_activity_watch"),  # the app and title in front of him, when he allows it (DEC-0197)
    ("recall_index", 600, "_check_recall_index"),  # his records embedded for recall by meaning (DEC-0210)
)

# The once-a-day checks, in the order they run: (name, the method). Each has its own "already ran today" gate.
DAILY_CHECKS: tuple[tuple[str, str], ...] = (
    ("birthday", "_check_birthday"),
    ("calendar_digest", "_check_calendar_digest"),
    ("checkin", "_check_checkin"),
    ("budget_nudge", "_check_budget_nudge"),
    ("smart_suggestion", "_check_smart_suggestion"),
    ("maintenance_insight", "_check_maintenance_insight"),
    ("mission_insight", "_check_mission_insight"),
    ("pattern_insight", "_check_pattern_insight"),
    ("skill_pattern_insight", "_check_skill_pattern_insight"),
    ("skill_decline_insight", "_check_skill_decline_insight"),
    ("skill_momentum_insight", "_check_skill_momentum_insight"),
    ("recurring_mission", "_check_recurring_missions"),
    ("rewards", "_check_rewards"),
    ("walkthrough_suggestion", "_check_walkthrough_suggestion"),
    ("journal_reflection", "_check_journal_reflection"),
    ("warranty", "_check_warranties"),
    ("chronicle", "_check_chronicle"),
    ("memory_callback", "_check_memory_callbacks"),
    ("grow_alert", "_check_grow_alerts"),
    ("season", "_check_season"),
    ("insurance_renewal", "_check_insurance"),
    ("findings", "_check_findings"),
    ("obligation_reminders", "_check_obligations"),
    ("loop", "_check_loop"),
    ("fix_report", "_check_fix_report"),
    ("workflows", "_check_workflows"),
    ("loops", "_check_loops"),
    ("night_school", "_check_night_school"),
    ("self_report", "_check_self_report"),
    ("self_changes", "_check_self_changes"),
    ("capability_gaps", "_check_capability_gaps"),
    ("seasons_of_memory", "_check_seasons_of_memory"),
    ("operating_journal", "_check_operating_journal"),
    ("good_news", "_check_good_news"),
    ("chronicle_issue", "_check_chronicle_issue"),
    ("promises", "_check_promises"),
    ("vault_captions", "_check_vault_captions"),
    ("dependency_audit", "_check_dependency_audit"),
    ("system_map", "_check_system_map"),
    ("direction_nudge", "_check_direction_nudge"),
    ("capability_reminder", "_check_capability_reminder"),
    ("momentum", "_check_momentum"),
    ("greenhouse", "_check_greenhouse"),
    ("auto_backup", "_check_auto_backup"),
    ("restore_drill", "_check_restore_drill"),
    ("update_waiting", "_check_update_waiting"),
    ("weather_watch", "_check_weather_watch"),
    ("unusual", "_check_unusual"),
    ("garden_week", "_check_garden_week"),
    ("market_eve", "_check_market_eve"),
    ("evening_wrap", "_check_evening_wrap"),
    ("morning_briefing", "_check_morning_briefing"),
    ("habit_offer", "_check_habit_offer"),
)


class BackgroundJobs:
    """MIA's scheduled jobs and daily checks for one context (see the module's opening). `MIAApplication` inherits
    it; a headless runtime makes one directly."""

    def __init__(self, context, module_manager=None) -> None:
        """Keeps the context (and the module manager, when there is one: only the walkthrough suggestion uses
        it), with no offers waiting and the connection not yet observed."""
        from core.online_watch import OnlineWatch

        self.context = context
        self.module_manager = module_manager
        self._online_watch = OnlineWatch()
        self._offers: list = []
        self._offer_day = ""

    def schedule(self, scheduler, first_after: Optional[float] = None) -> None:
        """Puts every job in JOBS on the scheduler with its interval (the scheduler runs each under the store
        lock), and gives the scheduler the say on which jobs wait (a "stop everything" first, core/stop.py, then
        homeostasis's easing off), who hears of a backoff, and the time each run took (her own work's daily
        budget, LS-10), and keeps it for her self-repair (core/self_repair.py). Asks core/stop.py once first, so a "stop everything"
        kept from before a restart is known to `grants.require` from the start (both the PC and the server boot here).
        `first_after` is passed on for each job's first run (None: one interval from now, as the timers did)."""
        try:
            from core import stop

            stop.state(self.context)
        except Exception:  # noqa: BLE001 - a hold that can't be read never stops the boot
            log.exception("Couldn't read whether everything is stopped.")
        for name, seconds, method in JOBS:
            scheduler.add(name, seconds, getattr(self, method), first_after=first_after)
        scheduler.defer = self._defer_reason  # a stop-everything first, then easing off (DEC-0181, DEC-0173)
        self._scheduler = scheduler  # her self-repair re-runs a job that keeps failing (core/self_repair.py)
        scheduler.on_backoff = self.homeostasis.backing_off
        scheduler.on_ran = self.homeostasis.spend  # her own work's daily budget (LS-10)

    def _defer_reason(self, name: str) -> str:
        """Why a job or daily check waits now ("" to run it): he said "stop everything" and it's one that changes
        records on her own or reaches outside (core/stop.py), else MIA's own easing off (core/homeostasis.py)."""
        from core import stop

        return stop.defer_reason(self.context, name) or self.homeostasis.defer_reason(name)

    @property
    def homeostasis(self):
        """This MIA's easing off (core/homeostasis.py), made the first time it's asked for."""
        found = getattr(self, "_homeostasis", None)
        if found is None:
            from core.homeostasis import Homeostasis

            found = self._homeostasis = Homeostasis(self.context)
        return found

    def _check_alarms(self) -> None:
        """Every 20 seconds: rings any alarm that's due now."""
        self.context.alarms.check_due(datetime.now())

    def _check_power(self) -> None:
        """Periodic: warns about a low battery (a direct notification, like alarms)."""
        self.context.power.check_low_battery()

    def _check_mission_auto_assignment(self) -> None:
        """Periodic: lets the mission manager assign the missions it's due to assign."""
        self.context.missions.check_for_auto_assignment()

    def _check_finance_snapshots(self) -> None:
        """Periodic: imports new financial snapshot files and says so for each."""
        newly_imported = self.context.finance.scan_for_new_snapshots()
        for snapshot in newly_imported:
            self.context.notifications.notify(
                "New financial snapshot imported",
                f"Imported an updated snapshot from '{snapshot.source}'.",
            )

    def _check_homestead_snapshots(self) -> None:
        """Periodic: imports new homestead snapshot files and says so for each."""
        newly_imported = self.context.homestead.scan_for_new_snapshots()
        for snapshot in newly_imported:
            self.context.notifications.notify(
                "New homestead snapshot imported",
                f"Imported an updated snapshot from '{snapshot.source}'.",
            )

    def _check_inbox(self) -> None:
        """Periodic: finishes textbook reading in the background, then scans the inbox folder and offers one message
        describing what arrived (fingerprinted by the items, so it's never repeated).
        """
        if self.context.textbooks is not None and self.context.textbooks.finish_reading():
            self.context.events.publish("textbooks.updated")
        if self.context.inbox is None:
            return
        new_items = self.context.inbox.scan()
        if not new_items:
            return
        self.context.events.publish("inbox.updated")
        message = describe_new_items(new_items, self.context)
        candidate = Candidate(
            topic="inbox", title="\U0001F4E5 New in your inbox", message=message, urgency=TIMELY,
            source="inbox", fingerprint="|".join(i.item_id for i in new_items),
        )
        if self.context.communication is not None:
            self.context.communication.offer(candidate)
        elif self.context.notifications is not None:
            self.context.notifications.notify(candidate.title, candidate.message)

    def _check_online(self) -> None:
        """Periodic: watches the connection. On a change it delivers the reminders people asked for "when I'm back
        online" directly (they asked for them), and offers one message about the change (timely going offline, ambient
        coming back), once per kind per day.
        """
        monitor = self.context.connectivity
        if monitor is None:
            return
        kind = self._online_watch.observe(monitor.status)
        if kind is None:
            return
        reminders = self.context.online_reminders.take_all() if kind == CAME_BACK and self.context.online_reminders else []
        if self.context.notifications is not None:
            for what in reminders:  # asked for by the owner: delivered directly, not rate-limited
                self.context.notifications.notify("\U0001F514 Back online", f"You asked me to remind you: {what}")
        title, message = transition_message(kind, 0)
        candidate = Candidate(
            topic="connectivity", title=title, message=message,
            urgency=TIMELY if kind == WENT_OFFLINE else AMBIENT, source="connectivity",
            fingerprint=f"{kind}-{datetime.now().date().isoformat()}",
        )
        if self.context.communication is not None:
            self.context.communication.offer(candidate)

    def _check_inbox_mail(self) -> None:
        """Periodic: checks the mail account for new inbox mail, when one is set up."""
        if self.context.inbox_mail is not None:
            self.context.inbox_mail.check_now()

    def _check_lite_captures(self) -> None:
        """Periodic: picks up field captures from MIA Lite and says each is ready to review."""
        new_proposals = self.context.lite_captures.scan_for_new_captures()
        for proposal in new_proposals:
            self.context.notifications.notify(
                "New field capture ready to review",
                f"'{proposal.journal_title}' is ready to review in Field Captures.",
            )

    def _while_stores_free(self, slot):
        """A timer's slot that runs only when no one is reading or changing stores (the phone server mid-request):
        the lock is tried without waiting, so the desktop never stalls, and a skipped tick runs at the next one."""
        def tick() -> None:
            """One tick of the timer, under the store lock or not at all."""
            lock = self.context.store_lock
            if lock is None:
                slot()
                return
            if not lock.acquire(blocking=False):
                log.debug("Skipped a %s tick: the stores are busy.", getattr(slot, "__name__", "timer"))
                return
            try:
                slot()
            finally:
                lock.release()

        return tick

    def _check_daily_occasions(self, only: Optional[frozenset] = None) -> None:
        """See core/daily_occasions.py's docstring for the full reasoning behind each check (the newest: momentum,
        DEC-0148, the greenhouse node, DEC-0150, and the nightly backup, core/auto_backup.py). A deferrable check
        waits for the next clear tick while MIA eases off (core/homeostasis.py, DEC-0173) or her day's budget for her
        own work is used (each check's time is counted, LS-10), and a check that is her own
        work waits while the person has said "stop everything" (core/stop.py, DEC-0181). The time comes from the one
        clock (core/clock.py), so a replayed week holds it; `only` names the checks a replay runs (core/replay.py).

        Stabilization (2026-09-14) — this used to be one long function
        with 14 sequential `if should_run_once_daily(...):` blocks and
        no exception isolation between them: a real bug in any one
        block (e.g. Calendar digest) would raise, and every later
        block in the list (Budget nudge, all four Pattern Insight
        slices, Rewards, Walkthrough suggestions, ...) would silently
        never run that tick — not because THEY had a problem, but
        because an unrelated earlier one crashed first. Confirmed via
        a real check (not assumed) that PySide6 here calls
        sys.excepthook and keeps the app running rather than aborting
        (see main.py's own handler), so this wasn't an app-crashing
        bug — but it was a silent, indefinite one: if the same block
        kept failing every tick, every check after it would starve
        forever, logged but invisible on a kiosk device nobody's
        watching a terminal on. Refactored into one small method per
        check (same behavior/content as before, just relocated) and a
        loop with the exact same per-callback exception isolation
        core.event_bus.EventBus.publish() already established for the
        same reason — one broken check should never be able to starve
        the rest."""
        from core import clock

        now = clock.now(self.context).replace(tzinfo=None)  # his time, or a replayed day's (LS-07, LS-09)
        today_iso = now.date().isoformat()

        checks: list[tuple[str, Callable[[datetime, str], None]]] = [
            (name, getattr(self, method)) for name, method in DAILY_CHECKS
        ]
        # 2026-09-27, Cognitive Extension slice C: checks no longer notify
        # directly. Each one offers what it would say (_offer()), and the
        # whole tick's offers go through core/communication_gate.py
        # together: one merged message, the daily limit, no repeats,
        # never while the user is mid-vent. Deferred items from earlier
        # ticks are retried there too.
        self._offers = []
        self._offer_day = today_iso
        for name, check in checks:
            if only is not None and name not in only:
                continue  # a replayed week runs only the checks it names (core/replay.py)
            if self._defer_reason(name):
                continue  # stopped by him, or easing off: it waits for the next tick that's clear (DEC-0181, DEC-0173)
            began = time.monotonic()
            try:
                check(now, today_iso)
            except Exception:
                log.exception("Daily occasion check '%s' failed — other checks still ran.", name)
            self.homeostasis.spend(name, time.monotonic() - began)  # her own work's daily budget (LS-10)
        offers, self._offers = self._offers, []
        if self.context.communication is not None:
            self.context.communication.offer_batch(offers, now)
        elif self.context.notifications is not None:
            for c in offers:
                self.context.notifications.notify(title=c.title, message=c.message, level=c.level, source=c.source)

    def _check_auto_backup(self, now: datetime, today_iso: str) -> None:
        """The nightly backup (core/auto_backup.py): once a night from 2 a.m., into the backups folder, rotated."""
        from core import auto_backup

        if auto_backup.due(self.context.config, now):
            auto_backup.run(self.context, now)

    def _check_restore_drill(self, now: datetime, today_iso: str) -> None:
        """The monthly restore drill (core/restore_drill.py, WP-09): the newest backup restored into a scratch folder
        and every store opened, once a month after the nightly backup."""
        from core import restore_drill

        if restore_drill.due(self.context.config, now):
            restore_drill.run(self.context, now)

    def _check_update_waiting(self, now: datetime, today_iso: str) -> None:
        """An update staged on MIA OS, waiting for his restart (core/update_notice.py, Q-114: never a restart by
        herself): said once for each update, through the gate."""
        from core import update_notice

        self._offers.extend(update_notice.offer(self.context, now))

    def _check_weather_watch(self, now: datetime, today_iso: str) -> None:
        """Tonight's frost against the crops in the ground, a cold night against seedlings hardening off, heat and a
        freezing waterer against the flock (core/weather_watch.py): through the gate, once per concern per day. The
        forecast is fetched here when none is kept (never from a test run)."""
        import os

        from core import weather, weather_watch

        fetch = None if os.environ.get("PYTEST_CURRENT_TEST") else weather._fetch_json
        self._offers.extend(weather_watch.offer(self.context, now, fetch))

    def _check_unusual(self, now: datetime, today_iso: str) -> None:
        """What's off from his own normal (core/unusual.py, brainstorm 2.3; first, the hens laying far less): through
        the gate, once a week per finding."""
        from core import unusual

        self._offers.extend(unusual.offer(self.context, now))

    def _check_garden_week(self, now: datetime, today_iso: str) -> None:
        """This week in the garden (core/garden_week.py): his garden plans' steps in the next seven days, once a week,
        through the gate."""
        from core import garden_week

        self._offers.extend(garden_week.offer(self.context, now))

    def _check_market_eve(self, now: datetime, today_iso: str) -> None:
        """The day before a market day (core/market_eve.py): what to bring, from what usually sells, beside what's on
        hand; once per market day, through the gate."""
        from core import market_eve

        self._offers.extend(market_eve.offer(self.context, now))

    def _check_evening_wrap(self, now: datetime, today_iso: str) -> None:
        """The evening wrap (core/evening_wrap.py, DEC-0292): from his hour on, once a day, through the gate."""
        from core import evening_wrap

        self._offers.extend(evening_wrap.offer(self.context, now))

    def _check_morning_briefing(self, now: datetime, today_iso: str) -> None:
        """The morning briefing he asked for (core/morning_briefing.py): from his hour on, once a morning, through the
        gate."""
        from core import morning_briefing

        self._offers.extend(morning_briefing.offer(self.context, now))

    def _check_habit_offer(self, now: datetime, today_iso: str) -> None:
        """A routine offered from a habit of his (core/habit_offers.py, DEC-0294): the same kind of thing on the same
        weekday three weeks running, offered as a weekly reminder once ever, through the gate."""
        from core import habit_offers

        self._offers.extend(habit_offers.offer(self.context, now))

    def _check_loops(self, now: datetime, today_iso: str) -> None:
        """MIA's improvement loops (core/loops.py, DEC-0094): the person's use and the PC's, measured once a
        day; a loop below its floor opens a task, and what's for the person joins this tick's offers."""
        from core import loops

        for scope in ("person", "device"):
            self._offers.extend(loops.run(self.context, scope))

    def _check_night_school(self, now: datetime, today_iso: str) -> None:
        """Night School (core/night_school.py, DEC-0100): inside its window (01:30 by default), once a night,
        started in a process of its own; on the PC only, where the development platform is."""
        from core import night_school

        night_school.maybe_start()

    def _check_self_report(self, now: datetime, today_iso: str) -> None:
        """MIA's weekly self-report (core/self_report.py, step 6): Sundays, to the PC's owner, through the gate."""
        from core import self_report

        self._offers.extend(self_report.offer(self.context, now))

    def _check_self_changes(self, now: datetime, today_iso: str) -> None:
        """The daily summary of the changes she made to herself that went in on Claude's pass (core/self_merges.py,
        DEC-0225), to the PC's owner, through the gate, each with how to undo it; then those changes pushed to GitHub,
        so CI tests them (core/lab_push.py, WP-12, Q-100)."""
        from core import lab_push, self_merges

        self._offers.extend(self_merges.offer(self.context, now))
        lab_push.run(self.context, now)

    def _check_recall_index(self) -> None:
        """Every 10 minutes: what's new or changed in his memories, notes and projects is embedded for recall by
        meaning, and what's gone is dropped (core/recall_index.py, DEC-0210); nothing without an embedding model.
        The embedding runs on its own thread (it can take a minute), never holding the window or the stores."""
        index = getattr(self.context, "recall", None)
        if index is not None:
            index.refresh_later(self.context)  # the records read here; the embedding on its own thread

    def _check_activity_watch(self) -> None:
        """Every 30 seconds: notes the app and window title in front of him, when noting is on (core/activity_watch.py,
        DEC-0197); names and titles only."""
        from core import activity_watch

        activity_watch.sample(self.context)

    def _check_self_repair(self) -> None:
        """Every five minutes (core/self_repair.py, DEC-0222): Ollama started again if it stopped (on its own thread,
        so the window never waits), her model reloaded, a job that keeps failing run again; whatever she did, now or
        on that thread since the last round, is told through the gate."""
        from core import self_repair

        self_repair.check(self.context, getattr(self, "_scheduler", None))  # Ollama's start finishes on its own thread
        gate = getattr(self.context, "communication", None)
        for candidate in self_repair.offer(self.context):
            if gate is not None:
                gate.offer(candidate)

    def _check_capability_gaps(self, now: datetime, today_iso: str) -> None:
        """Self-enablement (core/capability_gaps.py, step 9): what she was asked and couldn't do, grouped; a
        repeated one offered through the gate, with what it would take."""
        from core import capability_gaps

        self._offers.extend(capability_gaps.offers(self.context))

    def _check_seasons_of_memory(self, now: datetime, today_iso: str) -> None:
        """Seasons of memory (core/seasons.py, step 10): each closed month and year kept once, in the person's
        folder, for "how did last month go?" and the Chronicle's yearly edition."""
        from core import seasons

        seasons.close_past(self.context, now.date())

    def _check_operating_journal(self, now: datetime, today_iso: str) -> None:
        """The Operating Journal (DEC-0097): on Sundays, the lines only the person can rate, asked once, gently."""
        from core.operating_journal import weekly_offer

        self._offers.extend(weekly_offer(self.context, now.date()))

    def _check_promises(self, now: datetime, today_iso: str) -> None:
        """A promise with a day (DEC-0054, core/life_notes.py): the day before and on the day, once each."""
        from core.life_notes import reminders

        self._offers.extend(reminders(self.context, now.date()))

    def _check_vault_captions(self, now: datetime, today_iso: str) -> None:
        """The photos this PC keeps for the phone, described at night so they can be found (core/vault_captions.py),
        in a process of its own: the vision model takes a few seconds a photo."""
        from core import vault_captions

        if vault_captions.due(now):
            vault_captions.launch()

    def _check_dependency_audit(self, now: datetime, today_iso: str) -> None:
        """Known vulnerabilities in the packages MIA runs on (core/dependency_audit.py, docs/SECURITY.md step 5):
        weekly, in a process of its own; the last check's findings are offered through the gate, once per set."""
        from core import dependency_audit

        if dependency_audit.due(now):
            dependency_audit.launch()
            return
        said = dependency_audit.offer(dependency_audit.last_result())
        if said is not None:
            title, message, fingerprint = said
            self._offer(topic="dependency_audit", title=title, message=message, urgency=TIMELY, source="system",
                        fingerprint=fingerprint)

    def _check_system_map(self, now: datetime, today_iso: str) -> None:
        """Keep docs/MIA_MAP.md current (DEC-0139): regenerate the one map of everything MIA is, once a day, so what
        she's made of stays easy to see. Rewriting identical content is a no-op to git, so it only changes when MIA
        actually changed."""
        import time as _time

        from core import system_map

        try:
            path = system_map.MAP_FILE
            if not path.exists() or _time.time() - path.stat().st_mtime > 20 * 3600:
                path.write_text(system_map.render(), encoding="utf-8")
        except Exception:
            log.exception("Couldn't regenerate the system map")

    def _check_world_intel(self) -> None:
        """World Intelligence (core/world_intel.py, DEC-0170): when it's on, a finished run's finds are kept and the
        best offered through the gate, and the due watches start on its worker thread (which only reads the web)."""
        from core import world_intel

        world_intel.tick(self.context)

    def _check_good_news(self, now: datetime, today_iso: str) -> None:
        """Good News Radio (core/good_news.py, DEC-0096): when someone switched it on, today's episode is made
        once, in a process of its own (it reads the public feeds and voices four personalities)."""
        from core import good_news

        if good_news.due(self.context, now):
            good_news.launch()

    def _check_chronicle_issue(self, now: datetime, today_iso: str) -> None:
        """The Chronicles' weekly issue (core/chronicle_issue.py, step 17): on Sundays, from the archive events Zac
        approved and no issue has told, drafted, checked and drawn in a process of its own; Zac approves it."""
        from core import chronicle_issue

        if chronicle_issue.due(now.date()):
            chronicle_issue.launch()

    def _check_workflows(self, now: datetime, today_iso: str) -> None:
        """Workflows MIA made whose trigger has come round (core/workflows.py, DEC-0092), and those started by new
        events in his history (DEC-0293; from something she read, each change waits for his yes): run them; what
        they'd tell the person joins this tick's offers, through the gate like the rest."""
        from core.workflows import run_due, run_on_events

        self._offers.extend(run_due(self.context, now))
        self._offers.extend(run_on_events(self.context, now))  # those started by events in his history (DEC-0293)

    def _offer(self, topic: str, title: str, message: str, urgency: str, source: str = "system",
               daily: bool = False, fingerprint: str = "") -> None:
        """Queue something a daily check would like to say this tick.

        `daily=True` is for messages that are meant to repeat daily and
        are only true today (birthday, calendar, check-in, budget
        nudge): today's date is part of what counts as "the same thing
        again", and a deferred one expires at midnight."""
        today_iso = getattr(self, "_offer_day", None) or datetime.now().date().isoformat()
        self._offers.append(Candidate(
            topic=topic, title=title, message=message, urgency=urgency, source=source,
            fingerprint=fingerprint or (f"{today_iso}|{message}" if daily else ""),
            expires=f"{today_iso}T23:59:59" if daily else "",
        ))

    def _check_birthday(self, now: datetime, today_iso: str) -> None:
        """The daily birthday check: once a day, if it's the signed-in person's birthday, offers a happy-birthday message."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_birthday_celebrated_date"), today_iso):
            active_profile = self.context.profiles.get_active_profile() if self.context.profiles else None
            if active_profile is not None and is_birthday_today(active_profile.birthday, now.date()):
                self._offer(
                    topic="birthday",
                    title="\U0001F389 Happy Birthday!",
                    message=f"Happy birthday, {active_profile.name}! Wishing you an amazing day.",
                    urgency=TIMELY,
                    source="system",
                    daily=True,
                )
                config.set("system.last_birthday_celebrated_date", today_iso)
                config.save()

    def _check_calendar_digest(self, now: datetime, today_iso: str) -> None:
        """The daily calendar digest: once a day (should_run_once_daily on the system.last_calendar_digest_date key), lists today's calendar events in one message when there are any. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_calendar_digest_date"), today_iso):
            events_today = (
                calendar_events_today(self.context.calendar.all_events(), today_iso)
                if self.context.calendar is not None
                else []
            )
            if events_today:
                titles = ", ".join(event.title for event in events_today)
                self._offer(
                    topic="calendar_digest",
                    title="Today's calendar",
                    message=f"You have {len(events_today)} event(s) today: {titles}",
                    urgency=TIMELY,
                    source="system",
                    daily=True,
                )
            config.set("system.last_calendar_digest_date", today_iso)
            config.save()

    def _check_checkin(self, now: datetime, today_iso: str) -> None:
        """The daily check-in: once a day, when nobody has talked to MIA yet and it's late enough (should_send_checkin),
        offers a gentle "how's everything going?".
        """
        config = self.context.config
        if should_run_once_daily(config.get("system.last_checkin_date"), today_iso):
            has_activity_today = self.context.conversations is not None and any(
                conversation.updated_at[:10] == today_iso
                for conversation in self.context.conversations.all_conversations()
            )
            if should_send_checkin(now, has_activity_today):
                self._offer(
                    topic="checkin",
                    title="Just checking in",
                    message="Haven't heard from you today — how's everything going?",
                    urgency=AMBIENT,
                    source="system",
                    daily=True,
                )
                config.set("system.last_checkin_date", today_iso)
                config.save()

    def _check_warranties(self, now: datetime, today_iso: str) -> None:
        """A heads-up a month and a week before a warranty ends (core/warranty_watch.py)."""
        maintenance = self.context.maintenance
        if maintenance is None:
            return
        config = self.context.config
        already = dict(config.get("system.warranty_notices", {}) or {})
        notices = due_notices(maintenance.all_assets(), now.date(), already)
        for asset, stage, days_left in notices:
            self._offer(
                topic="warranty", title="\U0001F6E1 Warranty ending",
                message=warranty_message(asset.name, asset.warranty_until, days_left),
                urgency=TIMELY, source="maintenance",
            )
            said = [s for s in str(already.get(asset.asset_id, "")).split(",") if s]
            already[asset.asset_id] = ",".join(said + [f"{asset.warranty_until}|{stage}"])
        if notices:
            config.set("system.warranty_notices", already)
            config.save()

    def _check_journal_reflection(self, now: datetime, today_iso: str) -> None:
        """The opt-in weekly journal reflection (core/journal_reflection.py):
        only a "your reflection is ready" notice, never journal content."""
        # The signed-in person's own setting and journal (core/person_settings.py).
        from core import person_settings

        context = self.context
        journal = context.private_journal
        if not person_settings.get(context, "journal.weekly_reflection", False) or journal is None or not journal.is_set_up():
            return
        if not reflection_due(now, int(person_settings.get(context, "journal.reflection_weekday", 6)),
                              person_settings.get(context, "system.last_journal_reflection_date")):
            return
        notice = reflection_notice(journal.count_since((now - timedelta(days=7)).isoformat(timespec="seconds")))
        if notice is not None:
            self._offer(topic="journal_reflection", title=notice[0], message=notice[1], urgency=TIMELY, source="journal",
                        daily=True)
        person_settings.put(context, "system.last_journal_reflection_date", today_iso)

    def _check_grow_alerts(self, now: datetime, today_iso: str) -> None:
        """A greenhouse reading outside its range (core/grow_lab.py): a note
        through the gate, once per reading. Only ever a warning."""
        if getattr(self.context, "grow_lab", None) is None:
            return
        from core.grow_lab import alert_note
        from core.web_grow import grow_page

        for alert in grow_page(self.context, now.date())["alerts"]:
            title, message, fingerprint = alert_note(alert)
            self._offer(topic="grow_alert", title=title, message=message, urgency=TIMELY, source="greenhouse",
                        fingerprint=fingerprint)

    def _check_season(self, now: datetime, today_iso: str) -> None:
        """MIA as quest-giver (core/questlines.py): once a season, the
        season's questlines, through the gate (it drops a repeat)."""
        if getattr(self.context, "quest_book", None) is None:
            return
        from core import person_settings
        from core.questlines import season_note

        note = season_note(self.context, now.date())
        if note is None or person_settings.get(self.context, "system.last_season_note") == note[2]:
            return
        title, message, fingerprint = note
        self._offer(topic="season", title=title, message=message, urgency=AMBIENT, source="system",
                    fingerprint=fingerprint)
        person_settings.put(self.context, "system.last_season_note", fingerprint)

    def _check_insurance(self, now: datetime, today_iso: str) -> None:
        """A policy renews in about 45 days (core/insurance.py): once per
        renewal, through the gate (its fingerprint drops a repeat)."""
        if getattr(self.context, "insurance", None) is None:
            return
        from core.insurance import renewal_notes

        for title, message, fingerprint in renewal_notes(self.context, now.date()):
            if not self.context.insurance.note_given(fingerprint):
                continue
            self._offer(topic="insurance_renewal", title=title, message=message, urgency=AMBIENT, source="system",
                        fingerprint=fingerprint)

    def _check_findings(self, now: datetime, today_iso: str) -> None:
        """What MIA notices across apps (DEC-0052, core/findings.py): only
        the kinds Zac allowed unprompted go out, through the gate; each
        situation once (its key is the fingerprint)."""
        config = self.context.config
        if not should_run_once_daily(config.get("system.last_findings_check_date"), today_iso):
            return
        from core.findings import as_line, findings

        for f in findings(self.context, now.date()):
            if f.unprompted:
                self._offer(topic=f"finding_{f.key.split(':', 1)[0]}", title=f.title, message=as_line(f),
                            urgency=TIMELY, source="system", fingerprint=f"finding|{f.key}")
        config.set("system.last_findings_check_date", today_iso)
        config.save()

    def _check_loop(self, now: datetime, today_iso: str) -> None:
        """The Loop (DEC-0047, core/the_loop.py): new recurring things get a
        rhythm, days and times are learned once a day, the week's runs are
        planned, and each rhythm's reminder goes out at its time (direct,
        like an alarm the person set up)."""
        from core.the_loop import tick

        tick(self.context, now)

    def _check_fix_report(self, now: datetime, today_iso: str) -> None:
        """The Fix-It Log (DEC-0049): once a day, the fix report into the
        person's own folder (fix_report.md, never the repo), where Claude
        reads it on this computer."""
        from core.failure_log import write_report

        config = self.context.config
        if should_run_once_daily(config.get("system.last_fix_report_date"), today_iso):
            write_report(self.context)
            config.set("system.last_fix_report_date", today_iso)
            config.save()

    def _check_obligations(self, now: datetime, today_iso: str) -> None:
        """Tax and compliance deadlines (core/obligations.py, DEC-0040): at
        90/60/30/14/7 days, on the day and weekly while overdue, each once."""
        if getattr(self.context, "obligations", None) is None:
            return
        from core.obligations import reminder_notes

        for title, message, fingerprint, urgency in reminder_notes(self.context, now.date()):
            if not self.context.obligations.note_given(fingerprint):
                continue
            self._offer(topic="obligation_deadline", title=title, message=message, urgency=urgency, source="system",
                        fingerprint=fingerprint)

    def _check_memory_callbacks(self, now: datetime, today_iso: str) -> None:
        """Remembering at the right moment (DEC-0029): each callback once,
        through the gate (its daily limit and no-repeat rules)."""
        from core.memory_callbacks import as_message, callbacks

        for item in callbacks(self.context, now.date()):
            self._offer(topic="memory_callback", title=f"{item['icon']} {item['title']}", message=as_message(item),
                        urgency=AMBIENT, source="system", fingerprint=item["key"])

    def _check_direction_nudge(self, now: datetime, today_iso: str) -> None:
        """Now and then, a gentle nudge toward one of the person's standing directions (DEC-0141) — e.g. make or
        restore before buying. Occasional (not more than every few days) and through the gate, so it never nags."""
        import random

        book = getattr(self.context, "direction", None)
        if book is None or not hasattr(book, "due_for_nudge") or not book.due_for_nudge(today_iso):
            return
        # Prefer a grounded seed (core/whimsy.py): concrete, seasonal, shelf-aware inspiration toward one of the
        # person's own directions. Falls back to the direction's plain nudge when no seed fits.
        from core import whimsy

        active = book.active()
        blobs = [f"{d.title} {d.statement}" for d in active]
        materials = []
        if getattr(self.context, "materials", None) is not None:
            try:
                materials = [m.name for m in self.context.materials.all_materials()]
            except Exception:
                materials = []
        message = whimsy.a_seed(blobs, materials, now.month, random.random()) or book.a_nudge(random.random())
        if not message:
            return
        self._offer(topic="produce", title="\U0001F331 A nudge", message=message, urgency=AMBIENT, source="system",
                    fingerprint=f"produce:{today_iso}")
        book.mark_nudged(today_iso)

    def _check_capability_reminder(self, now: datetime, today_iso: str) -> None:
        """Now and then, a reminder of what the person can already go and do right now (Zac, 2026-11-08) — a learning
        path a step from advancing, a project they started and parked. A subtle, affirming redirect, paced every few
        days and sent through the gate, so it stays gentle and never a push."""
        import random
        from datetime import date

        config = self.context.config
        last = config.get("system.last_capability_reminder_date")
        if last:
            try:
                if (date.fromisoformat(today_iso) - date.fromisoformat(last)).days < 4:
                    return
            except ValueError:
                pass
        abilities = self._capabilities_on_hand()
        if not abilities:
            return
        from core import capability_reminders

        message = capability_reminders.a_reminder(abilities, random.random())
        if not message:
            return
        self._offer(topic="capability", title="\U0001F4A1 You could, you know", message=message, urgency=AMBIENT,
                    source="system", fingerprint=f"capability:{today_iso}")
        config.set("system.last_capability_reminder_date", today_iso)
        config.save()

    def _check_greenhouse(self, now: datetime, today_iso: str) -> None:
        """The greenhouse node (core/greenhouse_link.py, DEC-0150): once MIA has taken it over, read it every few
        minutes, keep its readings in the grow lab, and offer each new alert through the gate (critical urgent,
        warning timely)."""
        from core import greenhouse_link

        link = getattr(self.context, "greenhouse_link", None)
        if link is None:
            return
        for c in greenhouse_link.tick(self.context, link, now):
            self._offer(topic=c.topic, title=c.title, message=c.message, urgency=c.urgency, source=c.source,
                        fingerprint=c.fingerprint)

    def _check_momentum(self, now: datetime, today_iso: str) -> None:
        """Natural Momentum (core/momentum.py, DEC-0148): in the person's usual hour for a run of getting things done,
        with nothing done yet, one easy start; in the evening before a work day, the prep they've done before. Each at
        most once a day, through the gate (which holds both while they're already in flow)."""
        from core import momentum

        config = self.context.config
        for kind, line, title in (("start", momentum.easy_start(self.context, now), "\u2615 An easy start"),
                                  ("prep", momentum.tomorrow_prep(self.context, now), "\U0001F319 For tomorrow")):
            if not line or config.get(f"system.last_momentum_{kind}_date") == today_iso:
                continue
            self._offer(topic="momentum", title=title, message=line, urgency=AMBIENT, source="system",
                        fingerprint=f"momentum:{kind}:{today_iso}")
            config.set(f"system.last_momentum_{kind}_date", today_iso)
            config.save()

    def _capabilities_on_hand(self) -> list:
        """The real, right-now abilities a reminder can draw from: core/capability_reminders.on_hand (shared with the
        My Directions screen)."""
        from core import capability_reminders

        return capability_reminders.on_hand(self.context)

    def _check_chronicle(self, now: datetime, today_iso: str) -> None:
        """Sundays: this week's chapter of the Chronicle is ready (DEC-0028)."""
        if now.weekday() != 6:
            return
        from core.chronicle import chronicle_page

        config = self.context.config
        week = chronicle_page(self.context, now.date())["this_week"]
        if config.get("system.last_chronicle_week") == week["id"] or not week["total"]:
            return
        self._offer(topic="chronicle", title=f"\U0001F4DC {week['title']}: {week['name']}",
                    message=" ".join(week["story"][:2]) + " Your Chronicle is ready.", urgency=AMBIENT, source="system")
        config.set("system.last_chronicle_week", week["id"])
        config.save()

    def _check_budget_nudge(self, now: datetime, today_iso: str) -> None:
        """The daily budget nudge: once a day (should_run_once_daily on the system.last_budget_nudge_date key), puts overdue and due-soon bills, expected income and categories over this month's targets into one message (build_nudge_message). Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_budget_nudge_date"), today_iso) and self.context.budget is not None:
            bills = self.context.budget.all_bills()
            income_sources = self.context.budget.all_income_sources()
            targets = self.context.budget.all_budget_targets()
            month_start = now.date().replace(day=1).isoformat()
            actual_by_category = self.context.budget.total_expenses_by_category(month_start, None)
            message = build_nudge_message(bills, income_sources, targets, actual_by_category, now.date())
            if message:
                self._offer(
                    topic="budget_nudge",
                    title="Budget check-in",
                    message=message,
                    urgency=TIMELY,
                    source="system",
                    daily=True,
                )
            config.set("system.last_budget_nudge_date", today_iso)
            config.save()

    def _check_smart_suggestion(self, now: datetime, today_iso: str) -> None:
        """The daily smart suggestion: once a day (should_run_once_daily on the system.last_smart_suggestion_date key), batches suggestions from the last workout, the pantry and the people kept in Relationships into one message. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_smart_suggestion_date"), today_iso):
            last_session_date = self.context.workout.last_session_date() if self.context.workout is not None else None
            pantry_items = self.context.kitchen.all_pantry_items() if self.context.kitchen is not None else []
            people = self.context.relationships.all_people() if self.context.relationships is not None else []
            message = build_smart_suggestions_message(last_session_date, pantry_items, people, now.date())
            if message:
                self._offer(
                    topic="smart_suggestion",
                    title="Smart Suggestion",
                    message=message,
                    urgency=AMBIENT,
                    source="system",
                )
            config.set("system.last_smart_suggestion_date", today_iso)
            config.save()

    def _check_maintenance_insight(self, now: datetime, today_iso: str) -> None:
        # "Connective infrastructure" phase 3 (2026-09-11) — the first
        # real observe->insight->recommend scan, piloted in Maintenance.
        # Same should_run_once_daily()-gated, batched-into-one-message
        # shape as the Smart Suggestions check above.
        """The daily maintenance insight: once a day (should_run_once_daily on the system.last_maintenance_insight_date key), scans Maintenance for new insights (observe, insight, recommend) and batches them into one message. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_maintenance_insight_date"), today_iso):
            new_insights = scan_maintenance_insights(self.context, now.date())
            message = format_maintenance_insights_message(new_insights)
            if message:
                self._offer(
                    topic="maintenance_insight",
                    title="\U0001F527 Maintenance check",
                    message=message,
                    urgency=TIMELY,
                    source="insights",
                )
            config.set("system.last_maintenance_insight_date", today_iso)
            config.save()

    def _check_mission_insight(self, now: datetime, today_iso: str) -> None:
        # Missions-stale insights (2026-09-14) — the second domain the
        # observe->insight->recommend loop covers, same gated/batched
        # shape as the Maintenance check above (see
        # core/mission_insights.py's own docstring).
        """The daily mission insight: once a day (should_run_once_daily on the system.last_mission_insight_date key), scans for missions gone stale and batches them into one message. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_mission_insight_date"), today_iso):
            new_mission_insights = scan_mission_insights(self.context, now.date())
            message = format_mission_insights_message(new_mission_insights)
            if message:
                self._offer(
                    topic="mission_insight",
                    title="\U0001F4A4 Mission check-in",
                    message=message,
                    urgency=AMBIENT,
                    source="insights",
                )
            config.set("system.last_mission_insight_date", today_iso)
            config.save()

    def _check_pattern_insight(self, now: datetime, today_iso: str) -> None:
        # Pattern insights (2026-09-14) — the third domain the
        # observe->insight->recommend loop covers, and the first real
        # "learns from history" signal (core/pathway_manager.py's own
        # docstring named this "Phase 6"). Same gated/batched shape as
        # the two checks above — see core/mission_patterns.py's own
        # docstring.
        """The daily pattern insight: once a day (should_run_once_daily on the system.last_pattern_insight_date key), looks for patterns in mission history (core/mission_patterns.py) and batches the new ones into one message. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_pattern_insight_date"), today_iso):
            new_pattern_insights = scan_pattern_insights(self.context, now.date())
            message = format_pattern_insights_message(new_pattern_insights)
            if message:
                self._offer(
                    topic="pattern_insight",
                    title="\U0001F914 Noticed a pattern",
                    message=message,
                    urgency=AMBIENT,
                    source="insights",
                )
            config.set("system.last_pattern_insight_date", today_iso)
            config.save()

    def _check_skill_pattern_insight(self, now: datetime, today_iso: str) -> None:
        # Skill pattern insights (2026-09-14) — the second Pattern
        # Insight slice, scoped directly with the user (not assumed —
        # see core/skill_patterns.py's own docstring). Same gated/
        # batched shape as the check above; a different `kind` under
        # the same "patterns" source_type, tracked fully independently
        # per profile.
        """The daily skill pattern insight: once a day (should_run_once_daily on the system.last_skill_pattern_insight_date key), looks for patterns in skill practice (core/skill_patterns.py) and batches the new ones into one message. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_skill_pattern_insight_date"), today_iso):
            new_skill_pattern_insights = scan_skill_pattern_insights(self.context, now.date())
            message = format_skill_pattern_insights_message(new_skill_pattern_insights)
            if message:
                self._offer(
                    topic="skill_pattern_insight",
                    title="\U0001F3AF Noticed a pattern",
                    message=message,
                    urgency=AMBIENT,
                    source="insights",
                )
            config.set("system.last_skill_pattern_insight_date", today_iso)
            config.save()

    def _check_skill_decline_insight(self, now: datetime, today_iso: str) -> None:
        # Skill decline insights (2026-09-14) — the third Pattern
        # Insight slice, scoped directly with the user. Same gated/
        # batched shape as the check above; a different `kind` under
        # the same "patterns" source_type, tracked fully independently
        # per profile — see core/skill_patterns.py's own docstring.
        """The daily skill decline insight: once a day (should_run_once_daily on the system.last_skill_decline_insight_date key), notices skills slipping (core/skill_patterns.py) and batches them into one message. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_skill_decline_insight_date"), today_iso):
            new_skill_decline_insights = scan_skill_decline_insights(self.context, now.date())
            message = format_skill_decline_insights_message(new_skill_decline_insights)
            if message:
                self._offer(
                    topic="skill_decline_insight",
                    title="\U0001F4C9 Noticed a pattern",
                    message=message,
                    urgency=AMBIENT,
                    source="insights",
                )
            config.set("system.last_skill_decline_insight_date", today_iso)
            config.save()

    def _check_skill_momentum_insight(self, now: datetime, today_iso: str) -> None:
        # Skill momentum insights (2026-09-14) — the fourth Pattern
        # Insight slice, scoped directly with the user. Same gated/
        # batched shape as the check above; a different `kind` under
        # the same "patterns" source_type, tracked fully independently
        # per profile — see core/skill_patterns.py's own docstring.
        """The daily skill momentum insight: once a day (should_run_once_daily on the system.last_skill_momentum_insight_date key), notices skills gaining momentum (core/skill_patterns.py) and batches them into one message. Offered through the communication gate, never notified directly."""
        config = self.context.config
        if should_run_once_daily(config.get("system.last_skill_momentum_insight_date"), today_iso):
            new_skill_momentum_insights = scan_skill_momentum_insights(self.context, now.date())
            message = format_skill_momentum_insights_message(new_skill_momentum_insights)
            if message:
                self._offer(
                    topic="skill_momentum_insight",
                    title="\U0001F4C8 Noticed a pattern",
                    message=message,
                    urgency=AMBIENT,
                    source="insights",
                )
            config.set("system.last_skill_momentum_insight_date", today_iso)
            config.save()

    def _check_recurring_missions(self, now: datetime, today_iso: str) -> None:
        # Recurring Missions (2026-09-13) — same should_run_once_daily()
        # gate as every other check here; ensure_current_missions()
        # itself is idempotent too (checks occurrence_key first), so
        # this gate is a cheap once-a-day skip, not the only thing
        # preventing duplicates.
        """The daily recurring-missions check: once a day, makes sure every active template has its current mission
        (ensure_current_missions is idempotent, so the gate is only a cheap skip), plus the fitness plan's missions for
        whoever is signed in, this week's upkeep as scheduled missions (core/upkeep_missions.py, DEC-0153), and a debt
        payoff mission's steps ticked as each debt is paid off (core/debt_missions.py). Once ever, it also removes the
        old calendar copies of chores (DEC-0052).
        """
        config = self.context.config
        if should_run_once_daily(config.get("system.last_recurring_mission_check_date"), today_iso):
            if self.context.recurring_missions is not None:
                if not config.get("system.chore_calendar_copies_removed"):  # DEC-0052, once
                    self.context.recurring_missions.remove_written_calendar_copies()
                    config.set("system.chore_calendar_copies_removed", True)
                for template in self.context.recurring_missions.all_templates():
                    if template.active:
                        self.context.recurring_missions.ensure_current_missions(template, now.date())
            # The fitness plan's missions (DEC-0020), for whoever's signed in.
            from core.fitness_missions import ensure as ensure_fitness_missions

            ensure_fitness_missions(self.context, now.date())
            # Upkeep as scheduled missions (DEC-0153): this week's, and the ones done since.
            from core import upkeep_missions

            upkeep_missions.settle(self.context, now.date())
            upkeep_missions.ensure(self.context, now.date())
            # A payoff mission's steps ticked as each debt reaches zero, from the budget's record (core/debt_missions.py).
            from core import debt_missions

            debt_missions.tick(self.context)
            config.set("system.last_recurring_mission_check_date", today_iso)
            config.save()

    def _check_rewards(self, now: datetime, today_iso: str) -> None:
        # Rewards (2026-09-14) — same should_run_once_daily() gate;
        # scan_for_new_unlocks() is itself idempotent (checks
        # is_unlocked() first), so this is a cheap once-a-day nudge, not
        # the only thing preventing duplicate notifications. Also called
        # from modules/skills/module.py's own refresh, so a threshold
        # crossed while the app is open unlocks right away rather than
        # waiting up to a day.
        """The daily rewards check: once a day, unlocks any reward and hidden achievement the signed-in person has earned
        (both scans are idempotent; Skills also runs them on refresh so an unlock is immediate).
        Structures built (core/life_milestones.py) are scanned with them.
        """
        config = self.context.config
        if should_run_once_daily(config.get("system.last_rewards_check_date"), today_iso):
            if self.context.rewards is not None and self.context.profiles is not None:
                active_profile = self.context.profiles.get_active_profile()
                if active_profile is not None:
                    self.context.rewards.scan_for_new_unlocks(active_profile.profile_id)
                    # Hidden achievements (2026-09-14) — kept as its own
                    # scan (see core/rewards_manager.py's own docstring),
                    # called alongside scan_for_new_unlocks() everywhere.
                    self.context.rewards.scan_for_new_hidden_achievements(active_profile.profile_id)
                    self.context.rewards.scan_for_new_structures(active_profile.profile_id)
            config.set("system.last_rewards_check_date", today_iso)
            config.save()

    def _check_walkthrough_suggestion(self, now: datetime, today_iso: str) -> None:
        # Modular tutorial system: "never-used feature" walkthrough
        # suggestions (2026-09-14) — its own gate/check, not folded into
        # the combined Smart Suggestion message above, same reasoning
        # as Maintenance Insights/Recurring Missions/Rewards each
        # getting their own check: it has a real reason to fire (or
        # not) independent of workout/pantry/birthday state. At most
        # ONE candidate per day (module_browser excluded — it's always
        # visible chrome, not a discoverable feature), and
        # usage_tracker.mark_suggested() means the same module is never
        # nudged twice — see core/usage_tracker.py's own docstring for
        # why this can't become a recurring nag.
        """The daily walkthrough suggestion: at most one a day, it suggests trying one enabled module the person has never
        opened (never the Modules screen), and marks it suggested so the same one is never nudged twice
        (core/usage_tracker.py).
        """
        config = self.context.config
        if should_run_once_daily(config.get("system.last_walkthrough_suggestion_date"), today_iso):
            if self.context.usage_tracker is not None and getattr(self, "module_manager", None) is not None:
                candidate_modules = [
                    module for module in self.module_manager.enabled_modules()
                    if module.module_id != "module_browser"
                ]
                candidate_ids = [module.module_id for module in candidate_modules]
                never_opened = self.context.usage_tracker.unsuggested_never_opened_module_ids(candidate_ids)
                if never_opened:
                    chosen_id = never_opened[0]
                    chosen_module = next(m for m in candidate_modules if m.module_id == chosen_id)
                    message = build_walkthrough_suggestion(chosen_module.display_name)
                    if message:
                        self._offer(
                            topic="walkthrough_suggestion",
                            title="\U0001F393 Something to try",
                            message=message,
                            urgency=AMBIENT,
                            source="system",
                        )
                        self.context.usage_tracker.mark_suggested(chosen_id)
            config.set("system.last_walkthrough_suggestion_date", today_iso)
            config.save()
