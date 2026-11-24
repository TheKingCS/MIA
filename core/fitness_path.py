"""
core.fitness_path
===================

Fitness, a learning program on core/paths.py's method (DEC-0289; Zac, 2026-11-23: "Fitness"): a habit with good form,
getting stronger, and endurance and mobility. Its checks are mostly read from his own workout log (core/paths.py
SOURCES: workouts and their minutes, GPS tracks), so passing a stage is shown by what he did, not said. General
fitness guidance, never medical advice: anyone with a heart, joint or other condition, or new to exercise, checks with
a doctor first, as the guidelines themselves say.

Written from: US Department of Health and Human Services, Physical Activity Guidelines for Americans, 2nd edition
(150 to 300 minutes of moderate activity a week, muscle-strengthening on 2 or more days); American College of Sports
Medicine, ACSM's Guidelines for Exercise Testing and Prescription (progression, warm-up, rate of perceived exertion).
Its XP goes to the Strength skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "strength"  # her skill tree's Strength skill (data/skill_definitions.json)

STAGES: tuple[Stage, ...] = (
    Stage(1, "The habit and the form", "training regularly with good form on the basic movements", (
        Lesson("start_safe", "Starting safely", (
            "New to exercise, or with a heart, joint or other condition: check with a doctor first.",
            "Warm up 5 to 10 minutes (easy cardio, then lighter sets of the first exercise).",
            "Judge effort by how hard it feels on a 1 to 10 scale: start around 5 to 6, finishing each set with 2 or "
            "3 good reps left in you.",
            "Stop for sharp pain, chest pain, dizziness or unusual breathlessness."),
            "Starting too hard is the commonest reason people get hurt or quit in the first month.",
            ("Training to failure from day one.", "Skipping the warm-up when short on time.")),
        Lesson("patterns", "The basic movements", (
            "Squat (or a sit to a box): feet shoulder width, chest up, knees tracking over the toes, hips back and "
            "down.",
            "Hinge (a deadlift or hip hinge): a flat back, the hips pushing back, the weight close to the legs.",
            "Push (push-ups, press) and pull (rows): shoulders down and back, a full range of motion.",
            "Carry: hold a weight at your side and walk tall, ribs down."),
            "These five patterns cover nearly everything the body does lifting and moving loads.",
            ("Rounding the back on a hinge.", "Knees caving in on a squat.")),
    ), (
        Check("workouts_8", "Train at least 8 times", "recorded", passes_at=8, unit="workouts", source="workouts"),
        Check("form_said", "Walk MIA through your squat and hinge form cues", "said"),
    )),
    Stage(2, "Getting stronger", "progressing steadily on two to three strength days a week", (
        Lesson("progression", "Progressive overload", (
            "Strength work on 2 or 3 days a week, the same muscles rested a day between.",
            "When you can do every set at the top of the rep range with good form, add a little: a couple of reps, "
            "or about 2 to 10% more weight.",
            "Log every session (MIA's workout log): what, how many, how heavy.",
            "Every few weeks, an easier week."),
            "Muscles grow and get stronger from a little more than last time, repeated; the log is how you know.",
            ("Adding weight before the form is solid.", "Changing the whole routine every week.")),
        Lesson("recovery", "Recovery", (
            "Sleep 7 or more hours; eat enough protein through the day.",
            "Soreness a day or two after is normal; pain in a joint is not."),
            "The getting stronger happens while resting, not during the workout.",
            ("Training the same muscles hard on consecutive days.",)),
    ), (
        Check("workouts_24", "Keep at it: 24 workouts since starting", "recorded", passes_at=24, unit="workouts",
              source="workouts"),
    )),
    Stage(3, "Endurance and mobility", "aerobic fitness at the guidelines' level, and moving freely", (
        Lesson("aerobic", "Aerobic fitness", (
            "Build up to 150 minutes a week of moderate activity (brisk walking, cycling, hiking): you can talk but "
            "not sing.",
            "Or 75 minutes of vigorous activity (only a few words between breaths).",
            "Spread it over the week; any amount counts."),
            "The guidelines' aerobic minutes are where most of exercise's health benefit comes from.",
            ("Doing it all on one day.",)),
        Lesson("mobility", "Mobility", (
            "After training, stretch the hips, hamstrings, chest and shoulders, holding each 20 to 30 seconds.",
            "Move joints through their full range daily; never bounce a stretch."),
            "Range of motion keeps the lifts safe and the body useful for work.",
            ("Stretching hard before lifting instead of warming up.",)),
    ), (
        Check("minutes_600", "Log 600 minutes of workouts since starting (four weeks at the guidelines)", "recorded",
              passes_at=600, unit="minutes", source="workout_minutes"),
        Check("long_hike", "Walk or hike 8 km in one go, tracked", "recorded", passes_at=8, unit="km",
              source="longest_track_km"),
    )),
)

PROGRAM = register(Program(
    "fitness", "Fitness", SKILL, "🏋️", "A training habit with good form, steady strength gains, and the guidelines' "
    "endurance and mobility, checked by your own workout log.",
    ("fitness", "get fit", "get stronger", "strength training", "work out more", "exercise more"), STAGES,
    plan=(40, 3)))
