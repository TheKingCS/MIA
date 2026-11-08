"""What the phone will offer the glasses through the relay (DEC-0064). Relay.kt
holds the list; these keep it inside what the glasses may do at all."""

import re
from pathlib import Path

from core.actions import ACTION_TYPES
from core.glasses import GLASSES_KINDS

RELAY = (Path(__file__).parent.parent / "android-phone/app/src/main/java/com/mia/phone/Relay.kt").read_text(encoding="utf-8")


def offered() -> set[str]:
    """The action kinds the phone's relay offers, read from its OFFER_KINDS."""
    block = re.search(r"OFFER_KINDS = setOf\((.*?)\)", RELAY, re.S).group(1)
    return set(re.findall(r'"([a-z_.]+)"', block))


def test_every_offer_is_a_real_glasses_action():
    assert offered() and offered() <= GLASSES_KINDS
    assert offered() <= set(ACTION_TYPES)


def test_nothing_that_spends_or_deletes():
    assert {"mission.complete", "meal.cook", "training.set"} <= offered()  # DEC-0065
    assert "app.favorite" not in offered()
    assert not [k for k in offered() if k.startswith(("bill.", "budget", "debt")) or k.endswith(".delete")]


def test_every_designed_app_reaches_the_glasses():
    """DEC-0066: the engine decides which apps the glasses get, money included;
    the phone no longer cuts them to a list or blanks amounts."""
    assert "HOME_APPS" not in RELAY
    assert "MONEY" not in RELAY.replace("SYNC_CHOICES_ON_MONEY", "")


def test_a_reference_dies_at_approve_too():
    assert "it.at <= OFFER_MS }" in RELAY.split("private fun decide")[1].split("private fun")[0]


def test_talk_runs_only_offered_words():
    talk = RELAY.split("if (path == TALK)")[1].split("}")[0]
    assert "offered(say)" in talk


def test_the_first_boot_step_uses_a_real_route():
    import server.app as server_app

    assert '"/api/actions/propose"' in RELAY and 'engine("/api/actions", ' not in RELAY
    assert '@app.post("/api/actions/propose")' in Path(server_app.__file__).read_text(encoding="utf-8")
