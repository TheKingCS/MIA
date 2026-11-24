---
id: K-0424
kind: implementation
title: The weekend, planned from everything
status: confirmed
by: claude
created: 2026-11-24T15:06:43+00:00
concerns: core/question_plans.py, core/weather.py
from: dec:DEC-0052
---
The question plan weekend (what should I do this weekend?): each weekend day forecast (core/weather.py now asks Open-Meteo for 7 days and read() keeps each whole day by its date in days; tomorrow and today unchanged), what is due this week, the garden week, learning paths and projects, with a guidance line on fitting outdoor work to the drier day. weekend_days: this Saturday and Sunday, or what is left of it. The week review plan no longer takes weekend questions (its words had no closing word boundary, so this weekend matched this week).
