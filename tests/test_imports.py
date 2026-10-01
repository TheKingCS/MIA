"""
Imports from other apps (core/imports.py), 2026-10-01: calendars (.ics),
contacts (.vcf) and bank statements (.csv).
"""

import time
from types import SimpleNamespace

import pytest

import core.budget_manager as budget_module
import core.calendar_manager as calendar_module
import core.config_manager as config_module
import core.profile_manager as profile_module
import core.relationships_manager as rel_module
from core import imports
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.imports import guess_category, kind_of, parse_bank_csv, parse_ics, parse_vcards
from core.profile_manager import ProfileManager
from core.relationships_manager import RelationshipsManager
from core.undo_log import UndoLog, undo_last

ICS = """BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
SUMMARY:Dentist\\, Dr. Lee\r
DTSTART;VALUE=DATE:20261005\r
DESCRIPTION:Bring the insurance card\\nand forms\r
END:VEVENT\r
BEGIN:VEVENT\r
SUMMARY:Team standup that has a very long name which the calendar app fo\r
 lded onto a second line\r
DTSTART;TZID=America/New_York:20261006T093000\r
RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU\r
LOCATION:Room 4\r
END:VEVENT\r
BEGIN:VEVENT\r
SUMMARY:Mom's birthday\r
DTSTART;VALUE=DATE:19600312\r
RRULE:FREQ=YEARLY\r
END:VEVENT\r
BEGIN:VEVENT\r
SUMMARY:Broken\r
END:VEVENT\r
END:VCALENDAR\r
"""

VCF = """BEGIN:VCARD
VERSION:3.0
N:Lee;Pat;;;
FN:Pat Lee
item1.EMAIL;type=INTERNET:Pat@Example.com
TEL;TYPE=CELL:+1 555 0100
BDAY:1990-04-02
END:VCARD
BEGIN:VCARD
VERSION:4.0
N:;Grandma;;;
BDAY:--0612
END:VCARD
BEGIN:VCARD
VERSION:3.0
ORG:Smith Plumbing
EMAIL:office@smithplumbing.example
END:VCARD
"""

US_BANK = """Account: Checking ****1234
Date,Description,Amount,Balance
10/01/2026,KROGER #123,-54.20,1000.00
10/02/2026,PAYROLL ACME CO,"1,250.00",2250.00
10/03/2026,HOME DEPOT 4521,(89.99),2160.01
10/03/2026,,0.00,2160.01
not a date,Something,-5,
"""

UK_BANK = """Transaction Date,Details,Money Out,Money In
03/10/2026,TESCO STORES,12.50,
04/10/2026,SALARY,,2000.00
"""


# ------------------------------------------------------------------ parsing


def test_ics_events_dates_times_repeats_and_folding():
    events, problems = parse_ics(ICS)
    assert [e.title for e in events] == [
        "Dentist, Dr. Lee", "Team standup that has a very long name which the calendar app folded onto a second line",
        "Mom's birthday"]
    assert events[0].date == "2026-10-05" and events[0].time is None
    assert events[0].notes == "Bring the insurance card\nand forms"
    assert (events[1].date, events[1].time, events[1].recurrence) == ("2026-10-06", "09:30", "biweekly")
    assert events[1].notes == "Where: Room 4" and events[2].recurrence == "yearly"
    assert problems == ["Broken"]


def test_utc_times_become_local():
    events, _ = parse_ics("BEGIN:VEVENT\nSUMMARY:Call\nDTSTART:20261006T150000Z\nEND:VEVENT\n")
    from datetime import datetime, timezone

    local = datetime(2026, 10, 6, 15, 0, tzinfo=timezone.utc).astimezone()
    assert (events[0].date, events[0].time) == (local.date().isoformat(), local.strftime("%H:%M"))


def test_vcards_names_emails_birthdays():
    people, problems = parse_vcards(VCF)
    assert [p.name for p in people] == ["Pat Lee", "Grandma", "Smith Plumbing"]
    assert people[0].email == "pat@example.com" and people[0].birthday == "1990-04-02"
    assert "Phone: +1 555 0100" in people[0].notes
    assert people[1].birthday == "" and "Birthday: 0612 (no year)" in people[1].notes
    assert people[2].email == "office@smithplumbing.example" and problems == []


def test_bank_statements_us_and_uk_layouts():
    found, problems = parse_bank_csv(US_BANK)
    assert [(t.date, t.amount, t.is_income, t.category) for t in found] == [
        ("2026-10-01", 54.20, False, "Groceries"), ("2026-10-02", 1250.0, True, "Other"),
        ("2026-10-03", 89.99, False, "Building Materials")]
    assert len(problems) == 2  # the zero row and the bad date
    uk, _ = parse_bank_csv(UK_BANK, day_first=True)
    assert [(t.date, t.amount, t.is_income) for t in uk] == [("2026-10-03", 12.5, False), ("2026-10-04", 2000.0, True)]
    assert parse_bank_csv("a,b\n1,2\n") == ([], ["no Date and Amount columns found"])


def test_kind_and_category_guesses(tmp_path):
    assert kind_of(tmp_path / "x.ics", "") == imports.CALENDAR
    assert kind_of(tmp_path / "export.txt", "BEGIN:VCARD\n") == imports.CONTACTS
    assert kind_of(tmp_path / "s.csv", "") == imports.BANK and kind_of(tmp_path / "a.pdf", "") is None
    assert guess_category("NETFLIX.COM") == "Entertainment" and guess_category("Mystery shop") == "Other"


# ------------------------------------------------------------------ importing


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    for module, attrs in ((calendar_module, ("_EVENTS_FILE",)), (rel_module, ("_PEOPLE_FILE", "_PETS_FILE")),
                          (budget_module, ("_BILLS_FILE", "_INCOME_FILE", "_EXPENSES_FILE", "_INCOME_SOURCES_FILE",
                                           "_BUDGET_TARGETS_FILE", "_BUSINESS_ENTITIES_FILE", "_DEBTS_FILE"))):
        monkeypatch.setattr(module, "_DATA_DIR", tmp_path / "data")
        for attr in attrs:
            monkeypatch.setattr(module, attr, tmp_path / "data" / getattr(module, attr).name)
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile("Robin")
    context.undo = UndoLog()
    context.calendar = CalendarManager(context)
    context.relationships = RelationshipsManager(context)
    context.budget = BudgetManager(context)
    return context


def test_importing_twice_adds_nothing_twice(ctx, tmp_path):
    for name, text in (("cal.ics", ICS), ("contacts.vcf", VCF), ("bank.csv", US_BANK)):
        (tmp_path / name).write_text(text)
    assert imports.run(ctx, tmp_path / "cal.ics").describe() == "Imported 3 events; 1 couldn't be read."
    again = imports.run(ctx, tmp_path / "cal.ics")
    assert (again.added, again.skipped) == (0, 3) and len(ctx.calendar.all_events()) == 3
    ctx.relationships.add_person("Pat Lee")  # already known, without an email
    contacts = imports.run(ctx, tmp_path / "contacts.vcf")
    assert (contacts.added, contacts.skipped) == (2, 1)
    assert next(p for p in ctx.relationships.all_people() if p.name == "Pat Lee").email == "pat@example.com"
    bank = imports.run(ctx, tmp_path / "bank.csv")
    assert bank.added == 3 and len(ctx.budget.all_expenses()) == 2 and len(ctx.budget.all_income()) == 1
    assert imports.run(ctx, tmp_path / "bank.csv").added == 0
    with pytest.raises(ValueError, match="can import"):
        (tmp_path / "notes.pdf").write_text("x")
        imports.run(ctx, tmp_path / "notes.pdf")


def test_an_import_can_be_undone(ctx, tmp_path):
    (tmp_path / "cal.ics").write_text(ICS)
    imports.run(ctx, tmp_path / "cal.ics")
    assert len(ctx.calendar.all_events()) == 3
    change = undo_last(ctx, ctx.profiles.list_profiles()[0].profile_id)
    assert change.label == "import_calendar"
    assert ctx.calendar.all_events() == []  # re-read from the restored (here: removed) file


def test_outside_the_us_dates_are_day_first(ctx, tmp_path):
    ctx.config.set("region.country", "GB")
    (tmp_path / "bank.csv").write_text(UK_BANK)
    imports.run(ctx, tmp_path / "bank.csv")
    assert ctx.budget.all_expenses()[0].date == "2026-10-03"
