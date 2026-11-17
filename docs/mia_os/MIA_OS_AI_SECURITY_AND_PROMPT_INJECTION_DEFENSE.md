# MIA OS: AI security and prompt injection (Prompt 13 §9; DEC-0249)

*Claude (Opus), 2026-11-18. Planning only. OWASP Top 10 for LLM Applications (2025) is the checklist.*

## 1. The design rule

**The model has no authority.** It may read anything and propose anything; every proposal is parsed, validated
against its kind's schema, checked against policy (tier, grants, stop), authorised (a card or a grant), executed only
through the action's own code, and recorded. So an injected instruction can at most produce a proposal he sees.

| OWASP LLM risk | MIA's control |
|---|---|
| LLM01 Prompt injection | content marked as data (`untrusted`, OUTSIDE_MARK); no change without a card or grant; spoken approval only from his own words (`core/spoken_approval.py`) |
| LLM02 Sensitive information disclosure | the private journal and private-mode turns never in context or the recall index; secrets never in prompts |
| LLM03 Supply chain | models pulled from Ollama's library, recorded by digest; Claude inspects specialists' models (DEC-0200) |
| LLM04 Data and model poisoning | training only on his yes per dataset (DEC-0212); the bench before a model is used |
| LLM05 Improper output handling | model output never executed; numbers computed in code; HTML escaped in screens (CSP) |
| LLM06 Excessive agency | tiers, grants, the never list, the stop |
| LLM07 System prompt leakage | prompts hold no secrets |
| LLM08 Vector weaknesses | the recall index holds refs only, re-reads each hit from its store |
| LLM09 Misinformation | facts from records with provenance; "I don't know" said |
| LLM10 Unbounded consumption | the GPU queue, timeouts, rate limits |

## 2. Where content enters

Web pages (her browser, lookups), email (the inbox), documents and files he shares, messages, photos (Look), other
agents' workspace notes, the greenhouse's exports, World Intelligence feeds. **Each arrives marked**, and tool results
are labelled as results, never as his words.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-019 | Every piece of outside content shall reach the model marked as data, and no proposal it leads to shall run without a card or a grant he gave. | Must | MVP | All | Partial (web pages) | T: injection tests per source | DEC-0249 → 13 |
| REQ-SEC-020 | An injection test set (pages, emails, documents with embedded instructions) shall run with the suite and show no change made without a card. | Must | R1 | All | New | T | DEC-0249 → 13 |
