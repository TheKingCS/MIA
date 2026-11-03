"""What the phone will offer the glasses through the relay (DEC-0064). Relay.kt
holds the list; these keep it inside what the glasses may do at all."""

import re
from pathlib import Path

from core.actions import ACTION_TYPES
from core.glasses import GLASSES_KINDS

RELAY = (Path(__file__).parent.parent / "android-phone/app/src/main/java/com/mia/phone/Relay.kt").read_text(encoding="utf-8")


def offered() -> set[str]:
    block = re.search(r"OFFER_KINDS = setOf\((.*?)\)", RELAY, re.S).group(1)
    return set(re.findall(r'"([a-z_.]+)"', block))


def test_every_offer_is_a_real_glasses_action():
    assert offered() and offered() <= GLASSES_KINDS
    assert offered() <= set(ACTION_TYPES)


def test_nothing_that_pays_out_or_takes_from_the_pantry():
    assert not offered() & {"mission.complete", "meal.cook", "app.favorite"}
    assert not [k for k in offered() if k.startswith(("training.", "bill.", "budget", "debt"))]


def test_no_money_app_reaches_the_glasses():
    apps = set(re.findall(r'"([a-z_]+)"', re.search(r"HOME_APPS = listOf\((.*?)\)", RELAY).group(1)))
    assert apps == {"missions", "calendar", "workout", "kitchen", "garage", "greenhouse"}


def test_the_first_boot_step_uses_a_real_route():
    import server.app as server_app

    assert '"/api/actions/propose"' in RELAY and 'engine("/api/actions", ' not in RELAY
    assert '@app.post("/api/actions/propose")' in Path(server_app.__file__).read_text(encoding="utf-8")
