# TokenForge

**A team of AI agents that makes an on-device LLM generate text faster, round after round, and proves every speedup with byte-exact output checks.**

Entry for c0mpiled-15 (Penn State), **Track 1 · Challenge A: Build a Self-Improving Agent Team** (powered by Luminal).

## What it does

Six agents running on **Luminal Cloud** (`deepseek-ai/DeepSeek-V4.1-Flash`) repeatedly rewrite the hottest function of a small LLM: `matmul` in Karpathy's [llama2.c](https://github.com/karpathy/llama2.c). The model runs locally on an Apple M3 Pro. A fixed harness that the agents cannot change:

1. compiles each candidate with the same flags as the baseline (`clang -O3`),
2. rejects unsafe code (no I/O, syscalls, inline asm or extra libraries) and runs it with network access denied,
3. requires the model's greedy output to be **byte-identical** to the original for every prompt,
4. measures tokens/sec (one untimed warm-up, then the median of 5 runs). The baseline is re-measured every round, and speedup is reported as a ratio.

Every attempt, winning or failing, is stored in **MongoDB Atlas** with an embedding computed on-device by Ollama (`nomic-embed-text`). Before writing code, each agent retrieves the most relevant past wins and failures through **Atlas Vector Search**, so the team learns from its own history.

```
propose (6 Luminal agents, parallel) -> test (harness, sequential) -> learn (MongoDB memory) -> next round
```

### The team
Luminal serves one model, so the team's diversity comes from:
- **Strategy hints:** NEON SIMD, loop unrolling, GCD multithreading, cache blocking, combined approaches, and refining the champion.
- **Two thinking modes:** `fast` (thinking disabled) and `reasoner` (low reasoning effort).

### Promotion rule
A candidate becomes champion only if it beats the current champion by at least 5% on the **dev** split (stories15M) **and** also beats it on the **validation** split (stories42M, which has different matrix shapes).

### Fresh tests
The **held-out** split uses stories110M plus new prompts. It was never used during optimization, its SHA-256 was committed in `HELDOUT_HASH.txt` before the first round, and `heldout.py` refuses to run twice.

## Results (Apple M3 Pro)

### Held-out: fresh tests never used during optimization (run once; `results/heldout.json`)

| Model | Baseline (stock llama2.c, `-O3`) | TokenForge champion | Speedup | Upstream OpenMP build (reference) |
|---|---|---|---|---|
| **stories110M** (never seen) | 13.9 tok/s | **110.3 tok/s** | **7.95×** | 65.4 tok/s |
| stories42M (new prompt) | 43.8 tok/s | 368.7 tok/s | 8.42× | 162.6 tok/s |
| stories15M (new prompt) | 129.1 tok/s | 921.3 tok/s | 7.13× | 346.7 tok/s |
| **Geometric mean** | | | **7.82×** | |

### Final run: `r-20261011-170439` (MongoDB Atlas Vector Search memory)

| Round | Correct candidates | Champion speedup (dev, re-measured) | Promotion |
|---|---|---|---|
| 1 | 5/6 | 6.00× | fast agent |
| 2–3 | 5/6 | 5.8–6.0× | — |
| 4 | 3/6 | 6.37× | fast agent |
| 5 | 4/6 | 6.67× | reasoner agent |
| 6–8 | 4–5/6 | 5.6–7.1× | — |

- Dev baseline: 148.5 tok/s (stories15M). Upstream OpenMP reference: 2.34× on dev.
- 48 candidates; 36 correct. Every attempt is stored in Atlas.
- Luminal tokens used: about 226,000.
- The first full run (`r-20261011-163001`, local JSONL memory) reached a similar plateau (about 6.2×). Its correct-candidate rate rose from 83% to 100% by rounds 7–8. An early 1-round smoke test (`r-20261011-162519`) is included as well.

### What we learned (honest read)
- **The big win comes in round 1**, from NEON SIMD plus multithreading with GCD.
- The later promotions (6.0× → 6.67× on dev) each passed the validation gate, but **they are within our timing noise**: the same champion re-measures between 5.6× and 7.1× on a busy laptop. We do not claim a steady climb after round 1.
- **Amdahl's law explains the plateau.** Once `matmul` is about 6× faster, the code the agents may not touch (attention, softmax, RMSNorm) dominates. The held-out results agree: larger models, where `matmul` is a bigger share of the work, gain more (15M 7.1× → 42M 8.4×, 110M 8.0×).
- Why clang `-O3` doesn't vectorize the baseline: strict IEEE float rules forbid reordering the sum. The agents reorder it on purpose, and the harness proves the output is still byte-identical.
- Next step: when the team plateaus, open the next bottleneck (attention, softmax) to the agents under the same byte-exact check.

## Limitations
- Results come from one laptop (M3 Pro, 12 cores), with other apps running. We report medians and ranges, not best runs.
- Only `matmul` was optimized. All other llama2.c code is unmodified upstream code.
- No Accelerate or BLAS (vendor math libraries) is linked. We claim "faster than stock llama2.c," not "faster than BLAS."
- "Self-improving" means the solution and the team's memory improve. The DeepSeek weights do not change.
- The byte-exact correctness check is strict, so it may reject some valid floating-point reorderings.

## Run it
```bash
python3 -m venv .venv && .venv/bin/pip install openai pymongo streamlit pandas pytest python-dotenv requests
cp .env.example .env            # LUMINAL_BASE_URL, LUMINAL_API_KEY, MODEL_A, MONGODB_URI
ollama pull nomic-embed-text
# models: karpathy/tinyllamas stories15M/42M/110M.bin + llama2.c tokenizer.bin into models/
.venv/bin/python -m pytest -q
.venv/bin/python evolve.py --rounds 8 --agents 6
.venv/bin/python heldout.py      # once
.venv/bin/streamlit run app.py
```

## Files
| File | Role |
|---|---|
| `tokenforge/harness.py` | Referee: compile, sandbox, byte-exact check, timing |
| `tokenforge/agents.py` | Luminal agents (strategy hints, fast/reasoner modes, streaming, retries) |
| `tokenforge/memory.py` | MongoDB Atlas memory with Vector Search over on-device embeddings; JSONL fallback |
| `evolve.py` | Rounds and promotion rule |
| `heldout.py` | One-shot fresh-test evaluation |
| `app.py` | Streamlit dashboard |
| `vendor/run_tf.c` | Upstream `run.c` with `matmul` moved to `kernel.c` (the only change) |

## Credits
- [karpathy/llama2.c](https://github.com/karpathy/llama2.c) and [karpathy/tinyllamas](https://huggingface.co/karpathy/tinyllamas) (MIT): the model runtime and weights. See `vendor/LICENSE`.
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch): inspiration for agents running experiments in a loop.
- Built during c0mpiled-15 on Oct 11, 2026, starting at noon. No code was written before the event.
