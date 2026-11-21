"""The review of 2026-11-20's low findings, fixed: code beyond Python needs the lab's proof; a taught skill's hold is
refused; the phone removes the PC's greenhouse link once; a summer date gets summer time; a pick with no offer is
learned; a busy port is tried again; a site opens in his browser, not the shell; a sync conflict end to end."""
import json
from datetime import datetime
from types import SimpleNamespace

from core import clock, dev_lab, sync
from core.at_rest import open_text
from tests.test_sync import phone  # noqa: F401  (the fixture)


def test_javascript_and_shell_scripts_need_the_labs_proof_too():
    """Code is Python, the front end's JavaScript and shell scripts; styles, docs and tests aren't."""
    assert dev_lab.needs_proof(["web/apps.js"]) and dev_lab.needs_proof(["os/poc/vm/type_at_prompt.sh"])
    assert not dev_lab.needs_proof(["web/tokens.css", "docs/X.md", "tests/test_x.py", "tests/helper.js"])


def test_the_phone_removes_the_pcs_greenhouse_link_from_the_household_folder(tmp_path):
    """Its profiles' PC-only files and the household's greenhouse link, with their safety copies."""
    profiles, home = tmp_path / "profiles", tmp_path / "data"
    (profiles / "p1").mkdir(parents=True)
    home.mkdir()
    (profiles / "p1" / "activity.json").write_text("{}")
    (home / "greenhouse_link.json").write_text("{}")
    (home / "missions.json").write_text("[]")
    gone = {p.name for p in sync.remove_pc_only_copies(profiles, home)}
    assert gone == {"activity.json", "greenhouse_link.json"} and (home / "missions.json").exists()
    assert sync.PC_ONLY_VERSION >= 2


def test_the_computers_own_zone_gives_each_date_its_own_offset():
    """The fallback zone asks the system for each moment; it agrees with the system's own conversion."""
    for month in (1, 7):
        moment = datetime(2026, month, 15, 12, 0)
        assert moment.replace(tzinfo=clock._LOCAL).utcoffset() == moment.astimezone().utcoffset()


def test_a_pick_with_no_offer_waiting_is_learned_not_chosen_outright(tmp_path, monkeypatch):
    """It rejects the dimension's other ways, so "What I've learned" lists it and can forget it."""
    from core import answer_compare, person_settings
    from core.response_style import DIMENSIONS, StyleBook

    book = StyleBook(data_dir=tmp_path)
    monkeypatch.setattr(answer_compare, "_need_book", lambda context: book)
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: default)
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: None)
    dimension = next(iter(DIMENSIONS))
    answer_compare._pick(None, {"dimension": dimension, "chosen": DIMENSIONS[dimension][0]})
    assert book.picks[-1].rejected and book.learned_only(dimension)


def test_a_busy_port_is_tried_again_and_the_session_file_written_then(monkeypatch):
    """Not written at the start: tried every 30 seconds until it is, then left alone."""
    from core import desktop_session
    from core.runtime import Runtime

    tries = []
    monkeypatch.setattr(desktop_session, "path_from_env", lambda: "x")
    monkeypatch.setattr(desktop_session, "write", lambda context, where: tries.append(where) or len(tries) >= 2)
    fake = Runtime.__new__(Runtime)
    fake.context, fake._session_written, state = None, False, {}
    for now in (100.0, 110.0, 131.0, 162.0, 200.0):
        Runtime._keep_session(fake, now, state)
    assert len(tries) == 2 and fake._session_written


def test_only_her_own_server_and_the_shells_own_pages_open_inside_the_shell():
    """A site opens in his browser: the frameless shell has no way back from it."""
    from gui import os_shell

    assert os_shell.stays_here("http://127.0.0.1:8765/web/", "http") and os_shell.stays_here("data:text/html,x", "data")
    assert not os_shell.stays_here("https://example.com/", "https")
    assert not os_shell.stays_here("http://127.0.0.1.example.com/", "http")


def test_a_field_changed_on_both_devices_is_kept_and_told_through_a_whole_sync(phone, monkeypatch):
    """sync_now end to end: the phone's copy is the newer here, so its value wins; the PC's copy, the loser, is kept in
    the change history, and the note goes to the gate."""
    from tests.test_sync import PretendPC

    offered = []
    monkeypatch.setattr(sync, "keep_loser", lambda pid, path, losing, lost, local_won:
                        offered.append((path.name, json.loads(losing), lost, local_won)) or "note")
    monkeypatch.setattr(sync, "_tell_conflicts", lambda context, told, lock: offered.append(("told", told)))
    pc = PretendPC()
    pc.files["home"]["missions.json"] = json.dumps([{"mission_id": "m1", "name": "Fix fence", "xp": 10}]).encode()
    sync.sync_now(phone, call=pc)
    (phone.dirs["home"] / "missions.json").write_text(json.dumps([{"mission_id": "m1", "name": "Fix fence", "xp": 20}]))
    pc.files["home"]["missions.json"] = json.dumps([{"mission_id": "m1", "name": "Fix fence", "xp": 30}]).encode()
    sync.sync_now(phone, call=pc)
    kept = [o for o in offered if o[0] == "missions.json"]
    assert kept == [("missions.json", [{"mission_id": "m1", "name": "Fix fence", "xp": 30}],
                     [("mission_id=m1", "xp")], True)]
    assert ("told", ["note"]) in offered
    assert json.loads(open_text(phone.dirs["home"] / "missions.json"))[0]["xp"] == 20  # sealed at rest (WP-04)
