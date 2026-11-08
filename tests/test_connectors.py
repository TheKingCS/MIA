"""
tests.test_connectors
=======================

Bringing data in from other apps (core/connectors.py): a rental calendar keeps
only the booked dates (never the guest's details), blocked days aren't stays,
links reach only the public internet over https, a preview counts what's new
and what's already here, and an approved import lands as one change that
"undo that" takes back.
"""

import pytest

from core import connectors as cn

AIRBNB = (
    "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20261120\r\nDTEND;VALUE=DATE:20261123\r\nSUMMARY:Reserved\r\n"
    "DESCRIPTION:Reservation URL: https://www.airbnb.com/hosting/reservations/details/HMABC123\\nPhone Number (Last 4 "
    "Digits): 4421\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20261201\r\nDTEND;VALUE=DATE:20261205\r\n"
    "SUMMARY:Airbnb (Not available)\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20261210\r\nDTEND;VALUE=DATE:20261211\r\n"
    "SUMMARY:Reserved\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")


def test_a_rental_calendar_keeps_only_the_booked_dates():
    """Two stays with their nights; the blocked span is left out and counted."""
    stays, blocked = cn.parse_stays(AIRBNB)
    assert [(s.check_in, s.check_out, s.nights) for s in stays] == [("2026-11-20", "2026-11-23", 3),
                                                                    ("2026-12-10", "2026-12-11", 1)]
    assert blocked == 1


def test_links_are_https_and_never_this_computer_or_the_home_network():
    """webcal reads as https; http, files and private addresses are refused."""
    assert cn.clean_link(" webcal://www.airbnb.com/calendar/ical/1.ics?s=x ") == "https://www.airbnb.com/calendar/ical/1.ics?s=x"
    for bad in ("http://example.com/cal.ics", "file:///C:/cal.ics", "calendar.ics", ""):
        with pytest.raises(cn.LinkError):
            cn.clean_link(bad)
    for private in ("https://127.0.0.1/cal.ics", "https://localhost/cal.ics", "https://192.168.1.10/cal.ics"):
        with pytest.raises(cn.LinkError):
            cn.fetch_link(private)


def test_an_approved_rental_import_adds_check_ins_without_guest_details_and_undoes(tmp_path, monkeypatch):
    """Through the action: four events for two stays, none holding the reservation link or phone digits; a second
    import adds nothing; "undo that" takes the first one back."""
    from core.actions import ActionCenter
    from core.person_settings import person_id
    from core.undo_log import undo_last
    from tests.engine_world import build_world

    w = build_world(tmp_path, monkeypatch)
    center = ActionCenter()
    params = {"text": AIRBNB, "property": "Lake Cabin"}
    proposal = center.propose(w, "connect.rental_calendar", params)
    assert proposal.summary == "Lake Cabin's calendar: Add 4 check-ins and check-outs; 1 blocked span left out."
    assert center.approve(w, proposal.proposal_id).status == "executed"
    events = [e for e in w.calendar.all_events() if "Lake Cabin" in e.title]
    assert sorted((e.title, e.date) for e in events)[:2] == [("Check-in · Lake Cabin", "2026-11-20"),
                                                             ("Check-in · Lake Cabin", "2026-12-10")]
    assert not any("HMABC" in e.notes or "4421" in e.notes or "airbnb.com" in e.notes for e in events)
    again = center.propose(w, "connect.rental_calendar", params)
    assert again.summary.startswith("Lake Cabin's calendar: Nothing new") and "4 already in MIA" in again.summary
    undo_last(w, person_id(w))
    assert not [e for e in w.calendar.all_events() if "Lake Cabin" in e.title]


def test_a_downloaded_file_is_previewed_then_imported_by_its_own_parser(tmp_path, monkeypatch):
    """An .ics file: the preview names what's new; the approved import adds it once."""
    from core.actions import ActionCenter
    from tests.engine_world import build_world

    w = build_world(tmp_path, monkeypatch)
    ics = ("BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART;VALUE=DATE:20261115\nSUMMARY:Market day\nEND:VEVENT\n"
           "END:VCALENDAR\n")
    kind, preview = cn.file_preview(w, "cal.ics", ics)
    assert kind == "calendar" and preview.adds == ["Market day on 2026-11-15"] and preview.already == 0
    center = ActionCenter()
    done = center.approve(w, center.propose(w, "connect.file", {"name": "cal.ics", "text": ics}).proposal_id)
    assert done.status == "executed" and done.result.startswith("Imported 1 event")
    assert cn.file_preview(w, "cal.ics", ics)[1].already == 1
    with pytest.raises(ValueError):
        cn.file_preview(w, "notes.txt", "just some words")
