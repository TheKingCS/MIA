"""
tests.test_instance_lock
==========================

One MIA per data folder (core/instance_lock.py) and the desktop's timers
under the store lock (MIAApplication._while_stores_free, roadmap 2.4).
A second holder is a second open of the lock file in this process, which
the operating system refuses just as it refuses another process.
"""

from __future__ import annotations

from types import SimpleNamespace

from core import instance_lock
from core.store_lock import StoreLock


def test_a_second_mia_on_the_same_data_folder_is_refused(tmp_path):
    path = tmp_path / ".mia.lock"
    assert instance_lock.acquire(path)
    assert instance_lock.acquire(path)  # asking again in the same MIA is fine
    first = instance_lock._held.pop(str(path.resolve()))  # now the lock is held by "another" MIA
    try:
        assert not instance_lock.acquire(path)
    finally:
        instance_lock._held[str(path.resolve())] = first
        instance_lock.release(path)
    assert instance_lock.acquire(path)  # free again once that one is gone
    instance_lock.release(path)


def test_a_timer_tick_runs_under_the_store_lock_and_skips_while_it_s_taken():
    from core.application import MIAApplication

    lock, ran = StoreLock(), []
    app = SimpleNamespace(context=SimpleNamespace(store_lock=lock))
    tick = MIAApplication._while_stores_free(app, lambda: ran.append(lock.locked()))
    tick()
    assert ran == [True] and not lock.locked()
    with lock:  # the phone server mid-request
        tick()
    assert ran == [True]  # skipped, not waited for
