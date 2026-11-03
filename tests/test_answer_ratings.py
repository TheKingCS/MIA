"""Rating her answers (DEC-0067, core/answer_ratings.py): a 👍 is kept as a
rating, a 👎 is kept and still reaches the Fix-It Log, and each person's
ratings are their own."""

import pytest

from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


@pytest.fixture
def mia(shop):  # noqa: F811
    from core.answer_ratings import AnswerRatings
    from core.failure_log import FailureLog

    shop.failures = FailureLog(shop, data_dir=shop.my_dir)
    shop.ratings = AnswerRatings(shop, data_dir=shop.my_dir)
    return shop


def _rate(world, **params):
    from core.actions import ACTION_TYPES

    kind = ACTION_TYPES["answer.rate"]
    kind.describe(world, params)
    return kind.execute(world, params)


def test_a_thumbs_up_is_kept_as_a_rating(mia):
    import core.failure_actions  # noqa: F401  (registers answer.rate)

    said = _rate(mia, rating="up", prompt="morning MIA", reply="Morning! Big day?", surface="glasses")
    assert said == "Thanks: noted."
    r = mia.ratings.ratings[-1]
    assert (r["rating"], r["asked"], r["answer"], r["surface"]) == ("up", "morning MIA", "Morning! Big day?", "glasses")
    assert not any(e["kind"] == "thumbs_down" for e in mia.failures.events())


def test_a_thumbs_down_is_kept_and_still_reaches_the_fix_it_log(mia):
    import core.failure_actions  # noqa: F401

    _rate(mia, rating="down", prompt="tell me a joke", reply="Here is a joke.", surface="phone", note="not funny")
    assert mia.ratings.ratings[-1]["rating"] == "down" and mia.ratings.ratings[-1]["note"] == "not funny"
    assert mia.failures.events()[-1]["kind"] == "thumbs_down"


def test_a_rating_needs_a_reply_and_a_direction(mia):
    from core.actions import ACTION_TYPES, ActionError

    import core.failure_actions  # noqa: F401

    with pytest.raises(ActionError):
        ACTION_TYPES["answer.rate"].describe(mia, {"rating": "up", "reply": ""})
    with pytest.raises(ActionError):
        ACTION_TYPES["answer.rate"].describe(mia, {"rating": "sideways", "reply": "x"})


def test_ratings_are_kept_on_disk_and_read_back(tmp_path):
    from core.answer_ratings import AnswerRatings

    AnswerRatings(data_dir=tmp_path).rate("up", "hi", "hey", "pc")
    again = AnswerRatings(data_dir=tmp_path)
    assert again.counts() == {"up": 1, "down": 0} and again.ratings[0]["surface"] == "pc"


def test_ratings_are_a_personal_store():
    from core.personal_data import PERSONAL_ATTRIBUTES

    assert "ratings" in PERSONAL_ATTRIBUTES
