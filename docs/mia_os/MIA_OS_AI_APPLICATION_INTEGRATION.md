# MIA OS: how applications expose capabilities to MIA (Prompt 03 §8)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).*

## 1. What's declared today

| The prompt asks apps to declare | Today | Where |
|---|---|---|
| Available actions | yes | `AssistantAction` (tools), `ActionType` (actions), UAL `ActionSpec` |
| Supported intents | partly | tools' `trigger_phrases` and `subjects`; the router learns from use |
| Required inputs | yes | the tool's JSON schema; the action's `params` |
| Expected outputs | partly | tools return a sentence; screens return data; no output schema |
| Preconditions | in code | `describe()` raises `ActionError` with why |
| Permissions | partly | approval through the contract; child gating; UAL tiers; no per-capability grant (DEC-0156) |
| Side effects | in words | the approval sentence |
| Reversibility | in practice | every store write is undoable; not declared per capability |
| Execution status | yes | the proposal's status (proposed, executed, rejected, failed, expired, undone) |
| Failure conditions | yes | `ActionError`, the Fix-It Log |

MIA understands what an app can do **from code, not from the model's guess**: `core/capabilities.py` builds "what can
you do?" from the registries; `core/self_knowledge.py` answers about herself from records.

## 2. The capability contract, as fields (proposed)

```
CapabilitySpec
  id, version                     e.g. "world_watch.add@1"
  app                             the manifest that owns it
  summary                         one sentence (the tool's description)
  inputs                          JSON schema (exists)
  output                          JSON schema of the data returned, beside the sentence
  tier                            read | prepare | act_reversible | consequential | irreversible
  undo                            exact | backup_only | none
  needs                           stores read/written, network (hosts or "the person's SearXNG"), devices, model
  devices                         where it can run
  approval                        never | first_time | every_time   (from the tier and the person's grants)
  timeout_s, cancellable
  examples                        what a person says (trigger phrases, exists)
```

Built from what's there: the tool gives inputs and examples, the action kind gives the approval sentence and undo,
the UAL spec gives tier and where; the new fields are declared once in the action module. A test (proposed) fails on a
capability with no tier, like `tests/test_parity.py` fails on an undecided gap.

## 3. Read, prepare, reversible, consequential, irreversible

| Tier | Example | Approval today | Under DEC-0156 |
|---|---|---|---|
| read | "what have you found?" | none | observe |
| prepare | an email draft, a buying plan | none to make; saving is an action | suggest |
| act_reversible | add a watch, tick off a need | proposed and approved, or automated with exact undo (Zac's standing rule) | act-within-grant |
| consequential | buy, send, pay, sign in, publish | a person's press every time | act-with-approval |
| irreversible | delete for good, a wire transfer | a person's press every time, with the irreversibility said | act-with-approval; never granted standing |

## 4. Intent resolution

The person's words → candidate capabilities (the tool router: trigger phrases, subjects, learned picks) → the model
fills inputs (on a 3B model, from the person's own words) → `describe()` checks preconditions in code → the tier
decides approval. **Discovery without hardcoding** is the registry: a new app's capabilities are found because they're
registered, not because a prompt mentions them.

## 5. Provider independence

Apps never call a model directly; they ask model access (`core/llm_manager.py`, two backends today: Ollama and
llama.cpp's OpenAI-style server). Cloud models (the council, the UAL's outside-AI step) go through their own gated
paths with consent shown (Q-12, DEC-0165). Every app works without a model (AF-11): facts are computed in code, the
model only phrases. A test proves switching the model changes nothing MIA knows (`tests/test_living_system.py`).
