---
id: K-0468
kind: test-procedure
title: Today s new tools checked against the PC model: four never offered, all fixed
status: confirmed
by: claude
created: 2026-11-24T22:55:38+00:00
concerns: core/youtube_actions.py, core/canning_fix.py, core/repertoire_actions.py, core/assistant_achievement_actions.py
from: file:tests/live_model_check.py
---
Ran 12 prompts twice each through build_chat_request and qwen2.5:14b (scratchpad live_new.py, like live_some.py). Four failed because the tool was never offered: which achievement am I closest to (no phrase), find X on YouTube (words between find and on youtube; fixed with youtube as a music domain keyword), I learned X on guitar (only learning_lesson offered; added i learned phrases and a past-tense line in the description), 7 jars of tomatoes, not 70 (only put_up_jars offered; added correction phrases like , not and i meant). Neighbours checked: put up 7 quarts still put_up_jars, teach me the G chord still learning_lesson. Also the model says my canning mission, so _named drops my/the and mission. All 24 runs pass; the 12 are GOLDEN_CASES now and model_bench regenerated. Lesson: offered-or-not is the first failure to look for; the model chose right every time once offered.
