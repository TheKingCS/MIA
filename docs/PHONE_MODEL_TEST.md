# Can MIA think on the phone? (the model test, DEC-0019)

*Claude, 2026-10-07. Zac asked whether MIA's AI will still be good
enough on a phone. This is how we find out, on his own phone (Galaxy
A54: 6 GB of memory, Exynos 1380 with 4 fast and 4 slow cores).*

## What the model does in MIA (and what it doesn't)

MIA's facts (bills, missions, what's due) come from her own code, and
code decides which handful of tools to offer for each thing a person
says (`core/assistant_actions.py`, tests/assistant_routing_corpus.py).
The model's job is narrower: understand the sentence, pick the right
tool from those offered, fill in the person's words and numbers, and
phrase replies. That's why a small model can be enough.

## The pieces

| Piece | What it does |
|---|---|
| `core/llm_manager.py` `OpenAIBackend` | Talks to llama.cpp's server (`llm.backend: "openai"`), same tools as Ollama. Keeps the server's own speed numbers. |
| `android-phone/build_llama_server.sh` | Builds llama.cpp's server (pinned release) for phones (arm64, with the dot-product instructions every recent phone has) and the CI emulator; it ships inside the app. |
| `core/local_model.py` | Downloads a model once from Hugging Face (and carries on after a break), starts the server on 127.0.0.1 with 4 threads, points Talk at it, remembers it for the next start. |
| `core/model_bench.py` | Asks the model the things people say to MIA and scores the answer the same way as `tests/live_model_check.py`. |
| `data/model_bench_cases.json` | Those cases, frozen by `python -m tools.make_model_bench`: the exact messages and tools MIA builds on a computer (placeholder records only). |
| `web/model-test.html` | The screen: Settings → MIA's model on this phone → Model test. |
| CI: `android-phone.yml` | Builds it all, then on the emulator starts the smallest model, runs 5 cases and a Talk turn. |
| CI: `model-check.yml` | Runs each model through 80 cases on GitHub's computer: which model picks the right tool most often (accuracy doesn't depend on the device). |

## The models offered

All 4-bit (Q4_K_M), the usual size/quality trade for phones.

| Model | Download | Why |
|---|---|---|
| Qwen 2.5 · 1.5B | about 1.1 GB | The fastest; most likely to feel quick |
| Qwen 2.5 · 3B | about 2.1 GB | Better at tools, slower |
| Llama 3.2 · 3B | about 2.0 GB | What MIA runs on a computer today: the comparison |

## What to watch

- **Reading speed** matters most. A request MIA sends is about 2,000 to
  2,500 tokens (the tools' descriptions are most of it; the largest about
  7,000). The answer is usually 20 to 60 tokens. If reading is slow, the
  fixes are in MIA, not the phone: shorter tool descriptions, fewer tools
  per request, and keeping the parts that don't change cached between
  turns.
- **Right tool, of N:** the share of cases where the model did what MIA
  needed (right tool, right words and numbers, nothing when nothing was
  needed, nothing destructive by mistake).
- Loading the model takes a while the first time after MIA starts.

## Zac's steps

1. Install the newest **MIA-Phone-Test.apk** (phone-spike release).
2. Gear → Settings → **Model test**. Download **Qwen 2.5 · 1.5B** on
   Wi-Fi (about 1.1 GB; you can leave and come back, it carries on).
3. Tap **Start**, then **Quick test**. Keep MIA open; plugged in is best.
4. Screenshot the results. Then try Talk: it uses the model now.
5. If there's time, do the same with a 3B model.

## Results

### Accuracy (CI "Model check", 2026-10-07, 80 of the 213 cases each)

| Model | Right tool | Typical case on GitHub's 4-core computer | Reading | Writing |
|---|---|---|---|---|
| Qwen 2.5 · 1.5B | **65 of 80 (81%)** | 9 s | 101 tokens/s | 31 tokens/s |
| Qwen 2.5 · 3B | **76 of 80 (95%)** | 25 s | 31 tokens/s | 13 tokens/s |
| Llama 3.2 · 3B (the PC's model) | **77 of 80 (96%)** | 32 s | 28 tokens/s | 11 tokens/s |

- **Both 3B models are about as good as MIA on a computer.** Their few
  misses are near-misses (a similar tool: "add grocery item" for "add
  the chili's ingredients", "adjust quantity" for "remove from inventory").
- **The 1.5B mostly misses one way:** asked a question ("What trips do I
  have?", "When is my next alarm?"), it answers in words instead of
  calling the lookup tool. 11 of its 15 misses are that. MIA can fix that
  in code: when the only tools offered are lookups, look it up first and
  let the model phrase the answer (MIA's "facts from code" rule).

### On Android (CI emulator, 2026-10-07)

The whole chain works with no computer: the app's own llama.cpp server
loaded the 1.5B model in 5.6 s, the test ran, and **Talk answered from
the phone's own model** ("Hello, world!"). The emulator has 2 slow cores
(7.9 tokens/s reading), so its speed says nothing about a real phone.

### On Zac's Galaxy A54

*(Waiting on Zac's Quick test screenshots.)*
