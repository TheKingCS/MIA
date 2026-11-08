"""Look It Up Online on the web (DEC-0053, T-0017): the page says whether a lookup may run and the rules; a search the
person asks for sends only the scrubbed words and shows what was sent; a problem is said, never thrown."""

import json
from types import SimpleNamespace

from core import web_lookup


def _config(**values):
    """A config holding only the given keys."""
    return SimpleNamespace(get=lambda key, default=None: values.get(key, default))


def test_the_page_says_whether_a_lookup_may_run_and_the_rules():
    page = web_lookup.screen(SimpleNamespace(config=_config()))
    assert page["allowed"] and page["own_engine"] and "never your records" in page["rules"]
    off = web_lookup.screen(SimpleNamespace(config=_config(**{"online.lookup": False})))
    assert not off["allowed"] and "turned off" in off["why"]


def test_a_search_sends_only_the_scrubbed_words_and_shows_what_was_sent():
    sent = []

    def fetch(url):
        """A stand-in SearXNG answering one result."""
        sent.append(url)
        return json.dumps({"results": [{"title": "Garlic", "url": "https://extension.example.edu/garlic",
                                        "content": "Plant in October."}]}).encode()

    found = web_lookup.look(SimpleNamespace(config=_config()), "garlic zone 6 me@example.com", fetch=fetch)
    assert "example.com" not in found["query"] and "example.com" not in sent[0].split("q=")[1].split("&")[0]
    assert found["results"][0]["source"] == "extension.example.edu" and found["at"]


def test_a_search_that_cant_run_says_why():
    def down(url):
        """A search engine that isn't answering."""
        raise OSError("refused")

    assert "isn't answering" in web_lookup.look(SimpleNamespace(config=_config()), "garlic", fetch=down)["problem"]
    off = web_lookup.look(SimpleNamespace(config=_config(**{"online.lookup": False})), "garlic")
    assert "turned off" in off["problem"]
