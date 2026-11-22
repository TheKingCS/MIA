"""
tests.test_move_rehearsal
===========================

FW-07b: the move to MIA OS rehearsed on synthetic data (os/poc/vm/move_rehearsal.py), here as in the VM: a real backup
of stores laid out as on Windows, restored by MIA's own code into a fresh folder, matches store for store; a record
changed afterwards is named.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_the_move_restores_every_store_and_a_damaged_record_is_caught(tmp_path):
    """The rehearsal passes: three stores matched, the changed one named."""
    spec = importlib.util.spec_from_file_location("move_rehearsal", ROOT / "os" / "poc" / "vm" / "move_rehearsal.py")
    rehearsal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rehearsal)
    assert rehearsal.rehearse(tmp_path) == {"matched": 3, "caught": "inventory_items.json"}
