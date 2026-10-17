"""MIA's voice (DEC-0029, docs/design/MIA_VOICE.md): what she writes on
her own never guilts the person (DEC-0014)."""

from datetime import date, timedelta

from core.buffs import buffs
from core.chronicle import THREADS, tell
from core.personality import guilt_in
from tests.engine_world import build_world


def test_the_check_itself():
    assert guilt_in("You failed to log a workout and you're behind.") == ["failed", "behind"]
    assert guilt_in("A quiet week. Rest counts too.") == []


def test_what_mia_writes_is_kind(tmp_path, monkeypatch):
    texts = []
    for key, _types, name, lead, say in THREADS:
        texts += [name, lead, say(1), say(5)]
    texts += tell([])["story"] + [tell([])["name"]]
    w = build_world(tmp_path, monkeypatch)
    today = date.today()
    for n in (0, 1, 2):
        w.workout.add_session(date_str=(today - timedelta(days=n)).isoformat(), duration_minutes=30)
    w.fitness.log_food("lunch", "Chicken bowl")
    texts += [b["why"] + " " + b["name"] + " " + b["lasts"] for b in buffs(w, today)]
    from core.memory_callbacks import as_message, callbacks
    from core.relationships_manager import RelationshipsManager

    w.relationships = RelationshipsManager(w, data_dir=tmp_path / "rel")
    w.relationships.add_person(name="Jordan", birthday=(today + timedelta(days=1)).replace(year=1994).isoformat(),
                               gift_ideas="A chalk bag")
    texts += [as_message(c) for c in callbacks(w, today)]
    assert len(texts) > 30
    found = {t[:60]: guilt_in(t) for t in texts if guilt_in(t)}
    assert found == {}
