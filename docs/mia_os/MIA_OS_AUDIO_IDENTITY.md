# MIA OS: audio identity (Prompt 11 §17; DEC-0240)

*Claude (Opus), 2026-11-17. Planning only. Built: the win sounds (`web/sound.js`: an objective's chime, a mission's
arpeggio, a level's fanfare, made in the browser, no files), voiced per theme (`SOUND_SETS`), and one setting
(`sound.on`, plus `sound.voice` for her spoken reward line). Not built: interface sounds. Her voice is Prompt 07's.*

| Sound | When | Character | Default (Q-84) |
|---|---|---|---|
| Listening on | mic opens | a soft rising two-note | on |
| Listening off | mic closes | the same, falling | on |
| Needs you | an approval waits | a gentle single note | on |
| Win | an objective, a mission, a level | the existing chimes, arpeggio, fanfare | on (as today) |
| Done | a change finished | a short bright tick | off |
| Message | a gate message | a soft chime | off |
| Error | something failed | a low two-note | on |
| Alarm | an alarm, safety | distinct, insistent, never soft | always on |

**Rules:** all sounds made or shipped locally (no fetching), the new ones made in the browser like the win sounds;
the one existing setting (`sound.on`) turns them all off, alarms excepted; never a sound alone for something important (every sound has a visual twin); a theme may choose
a sound profile (off, soft, full) but not replace the alarm. Her voice stays as chosen (Piper today).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-023 | Every interface sound shall have a visual twin, be turned off with one setting, and never replace the alarm's sound. | Must | R1 | All | New | T | DEC-0240 → 11 |
