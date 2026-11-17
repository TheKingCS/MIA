# MIA OS: the councils (Prompt 07 §7; DEC-0209)

*Claude (Opus), 2026-11-17. Planning only. Agent runtime and autonomy are Prompt 08's.*

## 1. Two councils, one shape

| | The development council (exists) | MIA's own council (proposed) |
|---|---|---|
| Purpose | building MIA | MIA's decisions that matter: a specialist's design, a safety review, a disputed fact |
| Members | Claude Code, Codex, Copilot, local Ollama roles (`work/agents.json`) | local models of **different families** (Qwen, gpt-oss, Mistral, a 70B on the model node) |
| Floor | `core/council_floor.py`: a budget per turn, members ask each other only through MIA's gate, a short context, never the whole chat | the same floor, reused |
| Approves | nothing; Zac approves | nothing; MIA or Zac decides under existing rules |

## 2. How MIA's council works

1. **Independent first:** each member answers the same framed question without seeing the others (no anchoring).
2. **Critique:** a member from another family reviews each answer for errors, against the evidence given.
3. **Synthesis in code where it can be:** where answers are numbers or choices, code compares them; where they're
   prose, the coordinator model writes a synthesis that must cite which member said what.
4. **Disagreement is kept:** the report shows each position and what would settle it. Agreement is never reported as
   proof, and two models of one family agreeing is labelled "not independent" (`specialist_review.py` already does).
5. **Budget and stop:** a council has a call budget shown before it runs, and it is a run, so "stop" ends it.

**When it convenes:** safety-critical specialist work (Q-57), a review that holds a design, or when he asks
("get a second opinion"). Never for chat.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-010 | A council's members shall answer independently before seeing each other's answers. | Must | R1 | PC | New | T: prompts asserted to hold no other member's answer | DEC-0209 → 07 |
| REQ-INT-011 | A council's report shall keep every disagreement with each side's evidence, and mark agreement within one model family as not independent. | Must | R1 | PC | Partial (`specialist_review.py`) | T | DEC-0209 → 07 |
