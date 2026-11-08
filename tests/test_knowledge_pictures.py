"""
tests.test_knowledge_pictures
===============================

Pictures in Knowledge articles (core/reference_library_manager.article_images): which <img> tags become pictures
fetched from the pack, resolved against the article's own path.
"""

from core.reference_library_manager import article_images


def test_relative_pictures_resolve_against_the_article_folder():
    html = b'<p>Text</p><img src="../I/Oak.jpg" alt="An oak"><img src="leaf.png">'
    assert article_images(html, "A/Trees/Oak") == [{"path": "A/I/Oak.jpg", "alt": "An oak"}, {"path": "A/Trees/leaf.png", "alt": ""}]


def test_web_links_inline_data_and_small_icons_are_left_out():
    html = (b'<img src="https://x.org/a.jpg"><img src="data:image/png;base64,AA"><img src="//cdn/a.png">'
            b'<img src="flag.png" width="20" height="14"><img src="big.png" width="300">')
    assert [i["path"] for i in article_images(html, "A/Page")] == ["A/big.png"]


def test_each_picture_once_outside_the_pack_never_and_at_most_the_limit():
    html = b"".join(b'<img src="p%d.jpg">' % (n % 3) for n in range(10)) + b'<img src="../../../etc/x.png">'
    assert [i["path"] for i in article_images(html, "A/Page")] == ["A/p0.jpg", "A/p1.jpg", "A/p2.jpg"]
    many = b"".join(b'<img src="p%d.jpg">' % n for n in range(20))
    assert len(article_images(many, "A/Page", limit=5)) == 5


def test_query_strings_and_escaped_names_are_cleaned():
    assert article_images(b'<img src="I/Caf%C3%A9.jpg?w=2#x">', "A/Page") == [{"path": "A/I/Café.jpg", "alt": ""}]
