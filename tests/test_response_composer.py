"""The response composer (core/response_composer.py, DEC-0067): what she says
on each device, composed for it, never a sentence cut in half."""

from types import SimpleNamespace

from core.response_composer import BUDGET, GLASSES, PC, PHONE, compose, first_sentences, grounded, tidy, words


class Model:
    def __init__(self, said):
        self.said, self.asked = said, []

    def generate(self, prompt, timeout=None):
        self.asked.append((prompt, timeout))
        return self.said


def test_tidy_drops_filler_lists_markdown_and_the_closing_offer():
    said = tidy("Certainly! Here's today:" + chr(10) + "- **Gym** at 6" + chr(10) + "- Call Sam" + chr(10) + "Let me know if you need anything else.")
    assert said == "Here's today: Gym at 6. Call Sam."


def test_a_short_answer_is_said_as_is():
    context = SimpleNamespace(llm=Model("should not be asked"))
    out = compose(context, "Eggs are on the list.", GLASSES)
    assert out.say == "Eggs are on the list." and not context.llm.asked


def test_the_phone_and_pc_get_the_whole_answer():
    long = "One. " * 200
    for surface in (PHONE, PC):
        assert compose(SimpleNamespace(llm=None), long, surface).say == long


def test_her_own_opening_comes_first_when_it_fits():
    model = Model("should not be asked")
    out = compose(SimpleNamespace(llm=model), "I'm here, Zac. Want to talk it through? " + "More detail here. " * 20, GLASSES)
    assert out.say.startswith("I'm here, Zac. Want to talk it through?") and not model.asked


def test_an_opening_too_long_to_speak_is_rewritten():
    model = Model("You've got the gym at 6 and a call with Sam.")
    out = compose(SimpleNamespace(llm=model), "Today you have the gym at 6 " + "and more " * 30 + "today. Then more.", GLASSES)
    assert out.say == "You've got the gym at 6 and a call with Sam."
    assert out.full.startswith("Today you have")
    assert model.asked and model.asked[0][1] <= 6


def test_a_rewrite_that_adds_a_number_is_refused():
    model = Model("You've got the gym at 7.")
    out = compose(SimpleNamespace(llm=model), "Today you have the gym at 6 " + "and more " * 30 + "today.", GLASSES)
    assert "7" not in out.say and out.say.startswith("Today you have the gym at 6")


def test_without_a_model_she_says_her_own_first_sentences_whole():
    out = compose(SimpleNamespace(llm=None), "First point is short. " * 20, GLASSES)
    assert words(out.say) <= BUDGET[GLASSES] and out.say.endswith(".")


def test_one_long_sentence_is_kept_whole_not_cut():
    assert first_sentences("word " * 40 + "end.", 10).endswith("end.")


def test_grounded_numbers():
    assert grounded("Rent is 1,200 on the 3rd.", "Rent of 1,200 is due on the 3rd.")
    assert not grounded("Rent is 1,500.", "Rent of 1,200 is due.")
