# Answering Well with Tools: Research for MIA

*Claude, 2026-10-30, at Zac's request ("research how to set up MIA for
answering questions and functioning best for tool calls"). What the
research says, checked against MIA herself and the home computer, and
what goes into her build. Feeds DEC-0052 (`docs/REASONING_PLAN.md`) and
the Intelligence Benchmark (`docs/INTELLIGENCE_BENCHMARK.md`).*

## 1. What the research says

1. **Fewer, more relevant tools beat more tools.** Cutting the tools a
   model sees raises both its success rate and how often it picks the
   right one ([Less is More, arXiv 2411.15399](https://arxiv.org/pdf/2411.15399)).
   Choosing a small set **by meaning** (embeddings of each tool's
   description, compared with the question) improves accuracy and saves
   most of the prompt ([Semantic Tool Discovery, arXiv 2603.20313](https://arxiv.org/html/2603.20313v1);
   [Dynamic ReAct, arXiv 2509.20386](https://arxiv.org/pdf/2509.20386);
   [ToolScope, arXiv 2510.20036](https://arxiv.org/pdf/2510.20036v1)).
   For multi-step questions, choose tools from the question *and* what's
   been looked up so far ([arXiv 2512.17052](https://arxiv.org/pdf/2512.17052.pdf)).
2. **Small models are weak planners; split the work.** A planner, a
   caller and a summarizer each do better than one model doing all three
   ([Small LLMs Are Weak Tool Learners](https://huggingface.co/papers/2401.07324);
   [planner-executor](https://llmbestpractices.com/glossary/planner-executor)).
   Practitioners see 7B models fail the second call of a chain; 14B is
   the practical floor for multi-step work, with a narrow tool set and
   short tool results fed back ([n8n thread](https://community.n8n.io/t/tool-calling-chain-with-local-ollama-models-7b-14b-2nd-tool-never-executed/280320);
   [local agents guide](https://insiderllm.com/guides/local-ai-agents-guide/)).
3. **Model choice matters a lot.** Docker's evaluation of 21 local
   models ranked qwen3:14b first at choosing tools (F1 0.971), well ahead
   of qwen2.5:7b (0.753) ([Docker](https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/)).
   Qwen 2.5 uses the Hermes tool format natively, and Ollama supports it
   ([Qwen docs](https://qwen.readthedocs.io/en/stable/run_locally/ollama.html)).
4. **Temperature 0 and a checked format** make tool calls repeatable;
   validate every call and repair once rather than trusting it
   ([Ollama structured outputs](https://registry.ollama.ai/blog/structured-outputs);
   [local tool calling guide](https://llmconfigurator.com/en/guides/coding-agents/tool-calling-local-models)).
5. **A silent context cut-off is a classic trap.** Ollama doesn't error
   when a prompt is longer than its window: it drops the start, which is
   where the instructions and tools are
   ([Ollama context window](https://fast.io/resources/ollama-context-window/);
   [Open WebUI](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama.md)).

## 2. MIA, measured (2026-10-30, the home computer)

| What | Found |
|---|---|
| Model | qwen2.5:14b (Q4_K_M) on Ollama 0.40.7, all on the graphics card; qwen2.5:32b and llama3.2 also installed |
| Context window in use | 32,768 tokens (from the server, not set by MIA) |
| Temperature | 0 (`llm.temperature`), already |
| Tool format | native (the model reports "tools" capability) |
| All 220 tools at once | about 24,000 tokens: never sendable in one turn |
| Tools a turn gets today | 0 to 18, chosen by words in the question; 77 of Zac's 112 benchmark questions get none |
| Tool descriptions | median 93 characters, longest 704 |
| Tool calls per turn | one round; results said as they are, never combined |

## 3. What goes into MIA's build

| # | Change | From | Status |
|---|---|---|---|
| R1 | **Set the context window in every request** (`options.num_ctx` from `llm.num_ctx`, default 16384), so a computer whose Ollama defaults to 2048 or 4096 never silently cuts the instructions | 1.5 | build now |
| R2 | **Choose tools by meaning, not only words**: each tool's name, description and subjects embedded once (a small local embedding model, nomic-embed-text), compared with the question; joined with the keyword matches and the domains linked to them; at most about 10 a turn; keyword matching alone when the embedding model isn't there (the phone) | 1.1 | build, measured with the routing audit |
| R3 | **Code plans the common questions** (the question plans): code is the planner, the model phrases | 1.2 | DEC-0052 step 2a |
| R4 | **A short loop for the rest**: results go back to the model, compact (long results trimmed to their first lines and totals), up to 3 more lookups, the tools re-chosen from the question plus what's been found; stop when a lookup repeats | 1.1, 1.2 | DEC-0052 step 2b |
| R5 | **Answer from a fact sheet** whose lines are marked fact, calculation, estimate or missing (Zac's answer protocol), and a number check: every amount in the answer must be in a result | 1.4 | with R3/R4 |
| R6 | **Check every call's arguments** against the tool's own schema before running it; one repair try with the error said plainly | 1.4 | with R4 |
| R7 | **Benchmark qwen3:14b against qwen2.5:14b** on MIA's own golden set and the Intelligence Benchmark (`tools/pc_model_check.py`), before any switch | 1.3 | experiment; switching models stays Zac's call (DEC-0022) |
| R8 | Keep temperature 0 and native tool calls; keep tool descriptions short (what it answers, and when) | 1.3, 1.4 | kept |

## 4. What this doesn't change

Facts and arithmetic stay in code; the model chooses and phrases.
Changes still go through Propose → Approve. The phone keeps its smaller
model and its keyword matching, and gains the question plans, which need
no model to gather.
