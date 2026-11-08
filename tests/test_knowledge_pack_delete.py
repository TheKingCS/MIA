"""Deleting a Knowledge pack from the web (core/reference_library_manager.delete_confirmed): only once its name is
typed, as the desktop asks, because the file is gone for good."""

from types import SimpleNamespace

from core.reference_library_manager import delete_confirmed


def test_a_pack_goes_only_when_its_name_is_typed():
    gone = []
    pack = SimpleNamespace(pack_id="wiki_med", title="Wikipedia: Medicine")
    library = SimpleNamespace(get_pack=lambda i: pack if i == "wiki_med" else None,
                              delete_pack=lambda i: (gone.append(i) or True, "Deleted 'Wikipedia: Medicine'."))
    assert delete_confirmed(None, "wiki_med", "x") == (False, "That pack isn't in the library.")
    assert delete_confirmed(library, "nope", "x")[0] is False
    assert delete_confirmed(library, "wiki_med", "medicine") == \
        (False, "Type the pack's name exactly to delete it: Wikipedia: Medicine")
    assert not gone
    assert delete_confirmed(library, "wiki_med", "  wikipedia:  medicine ") == (True, "Deleted 'Wikipedia: Medicine'.")
    assert gone == ["wiki_med"]
