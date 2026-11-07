---
id: K-0057
kind: implementation
title: How MIA teaches, tracks and verifies a person's skill (guitar)
status: confirmed
by: claude
created: 2026-11-07T08:18:39+00:00
concerns: core/guitar.py, core/guitar_ear.py, web/guitar.js
from: dec:DEC-0111, file:core/guitar.py
---
What: core/guitar.py and core/guitar_ear.py, DEC-0111. A program of stages, each with lessons and skill checks; a personal coach store; weekly homework missions; stats; voice tools; a page that records.
How she verifies: a check is heard, counted or said, and the record keeps which. Heard checks work out a WAV in code: for a single string, the pitch by autocorrelation (an octave guard, interpolation between samples) and cents from standard tuning; for a chord, a chroma (each spectral peak's magnitude folded onto its pitch class) compared with the chord's notes: every chord tone at least 0.25 of the loudest, nothing outside it over 0.35.
How the thresholds were set: on synthesized plucked strings, clean open chords put up to 0.21 outside the chord (overtones), a string fretted wrong 0.43 or more, and the quietest chord tone 0.33. Energy (squared) drowned a single string under three of another note, so magnitudes are summed instead. An extra string that is a chord tone (Am with the low E) is rightly not a fault.
Checked in code too: every chord shape's frets produce exactly its chord's notes (a test), so a lesson can't teach a wrong shape.
Why this shape: it is how MIA grows herself (skills, missions, checks that must be passed by evidence), turned toward a person. The homework mission takes its progress from the log, as her fitness missions do.
