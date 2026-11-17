# MIA OS: notifications and attention (Prompt 10 §12; DEC-0232)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. One pipeline, two doors

```
her own unprompted messages ──▶ communication gate (merge, pace, repeats, log) ──┐
replies, alarms, low battery ─────────────────────────────────────────────────────┼──▶ MIA's history (notifications.html)
apps, the OS, KDE (org.freedesktop.Notifications) ──▶ Plasma's server ──▶ mirrored ┘      with "why" and source
```

- **Hers** go through the gate as now: paced by what he opens or dismisses (DEC-0171), no quiet hours (Q-75).
- **Everything else** uses the standard freedesktop notification service that Plasma provides; MIA's shell shows
  them and keeps them in her history, tagged with the app that sent them.
- **Why:** every entry says its source and, for hers, the gate's reason (`get_message_reason`).

## 2. Kinds and rules

| Kind | Example | Shows | Waits in Immersive |
|---|---|---|---|
| Urgent | alarm, safety, smoke, freezing greenhouse | at once, sound | no |
| Action needed | an approval waiting | badge and card | yes |
| Informational | a digest, a finished job | history | yes |
| Ambient | music changed | strip only | yes |

Grouping by source, deduplication (the gate's repeats; the freedesktop `replaces_id`), dismiss, snooze (back after a
chosen time), and history. Escalation: an urgent one not seen goes to the phone.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-019 | Notifications from MIA, apps and the OS shall share one history, each with its source and, for hers, why it came. | Should | R1 | PC | Partial (hers) | T | DEC-0232 → 10 |
| REQ-DSK-020 | Urgent notifications shall never be held by a mode, the gate or a stop. | Must | MVP | All | Exists (alarms direct) | T | DEC-0232, DEC-0217 → 10 |
