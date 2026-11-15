# Which Claude model does which MIA work

*Zac, 2026-11-15: "there are things Opus is capable of doing well and things
that are more inclined to be handled by Fable so lets designate those tasks
going forward and we will switch models when needed." DEC-0166.*

## What's documented about the two (Anthropic's model docs, cached 2026-11-03)

| | Claude Opus 5.5 | Claude Fable 5.2 |
|---|---|---|
| Positioning | the current Opus, the default model | Anthropic's most capable widely released model, "for the most demanding reasoning and long-horizon agentic work" |
| Price (API, per million tokens) | $4 in / $20 out | $8 in / $40 out (2×) |
| Context / output | 1M / 128K | 1M / 128K |
| Behaviour | faster turns; fast mode available | single requests on hard tasks "can run many minutes"; prompts written for earlier models are often too prescriptive for it |

**The split below is Claude's recommendation from those facts.** It is not
a measured benchmark on MIA's tasks. A Claude Code subscription bills
differently from the API, so "cost" here means usage limits more than
dollars.

## The assignment

**Fable 5.2** gets work where getting it right the first time matters most,
and where a mistake is expensive or hard to undo:
- The **MIA OS architecture prompts with the most cross-cutting judgement**:
  - Prompt 05: core OS architecture;
  - Prompt 08: autonomy and agents;
  - Prompt 13: security, privacy and permissions;
  - Prompt 14: boot, recovery and updates;
  - Prompt 16: implementation roadmap;
  - Prompt 17: final consolidation, which also needs the independent review.
- **Security-sensitive design and review:**
  - DEC-0156 (grants);
  - the System Manager helper (DEC-0158);
  - key backends (R-02);
  - the UAL's permission model and injection defences.
- **Long, multi-file refactors of foundations:**
  - extracting the MIA Runtime (DEC-0155), which moves the scheduler, server and store lock out of a 6,000-line file;
  - the key-backend change and its re-key path.
- **Independent review of Opus-written work** before a foundational merge: "the reviewer is not the author".
- **Root-causing hard failures:** an order-dependent test, a sync conflict, a crash that only happens on the PC.

**Opus 5.5** gets most day-to-day building, where speed and turn count
matter more than the last bit of reasoning depth:
- Features on the existing patterns: Smart Closet's later stages, LEP's stages, UAL actions (U3), new screens, voice tools, glasses cards.
- Bounded MIA OS prompts: 02, 03, 04, 06 (hardware), 07 (intelligence), 09–12, 15.
- Documentation, hub upkeep, decisions logging, regenerating the atlas, parity and loop reports.
- Test writing, CI fixes, phone-build babysitting, small refactors.
- Audits that are mostly reading the code and reporting what's there (like Prompt 01).

**Either one:** answering Zac's questions, planning a session, summaries for Chat.

## How it works in practice

- **NEXT_SESSION.md marks each queued task** with *(Fable)* or *(Opus)*. When the next task needs the other model, Claude says so before starting, so Zac can switch with `/model`.
- **One session doesn't switch models in the middle of a task.** It finishes or hands off through the hub files, which carry everything.
- **When unsure, start with Opus.** Escalate to Fable if Opus's review or tests show the work needs more (two failed attempts at the same problem is the signal).
- **Revisit after a month** of real use (DEC-0166's review clause): which tasks Fable improved, which it didn't.
