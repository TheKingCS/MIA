"""
core.character_stats
======================

Real character stats (DEC-0028, the game layer's fourth piece): six RPG
attributes, each 1 to 20, made from what the person has really done.
Every point says where it came from.

Each stat = 1 + its **training** (the levels earned in the skills it
draws on, up to 12) + its **recent activity** (the last 30 days, up to 7).
A stat never drops below what the skills have earned, so a quiet month
only means less of the recent bonus, never a loss (DEC-0014).

| Stat | Skills | Recent activity |
|---|---|---|
| Strength | strength, calisthenics, athleticism | workouts logged |
| Stamina | endurance, mobility, hiking, kayaking, camping | workout minutes, trips |
| Vitality | recovery, nutrition | meals eaten from your recipes; a watch adds sleep, resting heart rate, HRV |
| Wisdom | the Mind skills | journal entries |
| Charisma | communication, leadership, hospitality, teamwork, teaching | people you caught up with, the people you keep in MIA |
| Craft | Maker, Construction, cooking, Creative skills | workshop jobs finished, meals cooked |

`watch` lists what a smart watch will add to each stat when one is
connected (the plan in docs/GAME_LAYER.md); nothing is made up before then.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

TRAINING_MAX, RECENT_MAX = 12, 7

STATS = (
    ("strength", "Strength", "💪", ("strength", "calisthenics", "athleticism"), (), "Lifting, pushing, holding."),
    ("stamina", "Stamina", "🫀", ("endurance", "mobility", "hiking", "kayaking", "camping"),
     ("Heart-rate zones", "VO2 max", "Steps"), "Going longer and further."),
    ("vitality", "Vitality", "🌿", ("recovery", "nutrition"), ("Sleep", "Resting heart rate", "HRV"),
     "Rest, food and recovery."),
    ("wisdom", "Wisdom", "📘", ("learning", "focus", "problem_solving", "mathematics", "programming", "engineering",
                               "research", "memory"), (), "Learning and reflecting."),
    ("charisma", "Charisma", "🤝", ("communication", "leadership", "hospitality", "teamwork", "teaching"), (),
     "The people in your life."),
    ("craft", "Craft", "🛠", ("3d_printing", "cad", "mechanical_design", "prototyping", "fabrication", "woodworking",
                             "metalworking", "electronics", "soldering", "laser_engraving", "repair", "carpentry",
                             "plumbing", "concrete", "hvac", "drywall", "electrical_wiring", "framing", "cooking",
                             "photography", "videography", "music", "storytelling", "content_creation"),
     (), "Making things: food, builds, art."),
)


def score(training: float, recent: float) -> int:
    """Pure logic. 1 + training (≤12) + recent (≤7): a stat from 1 to 20."""
    return int(1 + min(TRAINING_MAX, max(0, round(training))) + min(RECENT_MAX, max(0, round(recent))))


def _skill_levels(context, profile_id) -> dict[str, int]:
    skills = getattr(context, "skills", None)
    if skills is None or not profile_id:
        return {}
    from core.skill_leveling import compute_skill_level_progress

    return {p.skill_id: compute_skill_level_progress(p.total_xp)[0] for p in skills.progress_for_profile(profile_id)}


def _count(fn) -> float:
    try:
        return float(fn())
    except Exception:
        log.debug("Character stats: a source failed", exc_info=True)
        return 0.0


def _recent(context, today: date) -> dict[str, list[tuple[str, float, float]]]:
    """Per stat: (what, how many, points), from the last 30 days."""
    since = (today - timedelta(days=30)).isoformat()
    workout = getattr(context, "workout", None)
    sessions = lambda: [s for s in workout.all_sessions() if (s.date or "") >= since]  # noqa: E731
    n_sessions = _count(lambda: len(sessions())) if workout is not None else 0.0
    minutes = _count(lambda: sum(s.duration_minutes or 0 for s in sessions())) if workout is not None else 0.0
    trips = getattr(context, "trips", None)
    n_trips = _count(lambda: sum(1 for t in trips.all_trips() if t.status == "completed" and (t.end_date or t.start_date or "") >= since)) \
        if trips is not None else 0.0
    kitchen = getattr(context, "kitchen", None)
    n_meals = _count(lambda: sum(1 for e in kitchen.all_meal_log_entries() if (e.date or "") >= since)) if kitchen is not None else 0.0
    journal = getattr(context, "journal", None)
    n_entries = _count(lambda: sum(1 for e in journal.all_entries() if (e.created_at or "")[:10] >= since)) if journal is not None else 0.0
    people = getattr(context, "relationships", None)
    n_people = _count(lambda: len(people.all_people())) if people is not None else 0.0
    n_caught = _count(lambda: sum(1 for p in people.all_people() if (getattr(p, "last_contact", "") or "") >= since)) \
        if people is not None else 0.0
    jobs = getattr(context, "jobs", None)
    n_jobs = _count(lambda: sum(1 for j in jobs.all_jobs() if j.status == "Complete" and (j.updated_at or "")[:10] >= since)) \
        if jobs is not None else 0.0
    return {
        "strength": [("workouts", n_sessions, n_sessions / 2)],
        "stamina": [("minutes trained", minutes, minutes / 120), ("trips finished", n_trips, n_trips * 2)],
        "vitality": [("meals eaten from your recipes", n_meals, n_meals / 6)],
        "wisdom": [("journal entries", n_entries, n_entries / 2)],
        "charisma": [("people you caught up with", n_caught, n_caught * 1.5), ("people you keep in MIA", n_people, n_people / 3)],
        "craft": [("workshop jobs finished", n_jobs, n_jobs * 2), ("meals cooked", n_meals, n_meals / 8)],
    }


def character_stats(context, profile_id: Optional[str], today: Optional[date] = None) -> list[dict]:
    today = today or date.today()
    levels = _skill_levels(context, profile_id)
    recent = _recent(context, today)
    out = []
    for key, name, icon, skills, watch, what in STATS:
        trained = [(s, levels[s]) for s in skills if levels.get(s, 1) > 1]
        training = sum(level - 1 for _s, level in trained)
        recent_points = sum(points for _w, _n, points in recent.get(key, []))
        value = score(training, recent_points)
        sources = [f"{s.replace('_', ' ').capitalize()} Lv {level}" for s, level in sorted(trained, key=lambda t: -t[1])[:3]]
        sources += [f"{n:g} {w}" for w, n, _p in recent.get(key, []) if n]
        out.append({"key": key, "name": name, "icon": icon, "value": value, "max": 20, "about": what,
                    "training": min(TRAINING_MAX, round(training)), "recent": min(RECENT_MAX, round(recent_points)),
                    "from": sources, "watch": list(watch)})
    return out
