# TokenForge

**A team of AI agents that makes an on-device LLM generate text faster, round after round, and checks generated text for every measured candidate.**

Entry for c0mpiled-15 (Penn State), **Track 1 · Challenge A: Build a Self-Improving Agent Team** (powered by Luminal).

## What it does

Six agents running on **Luminal Cloud** (`deepseek-ai/DeepSeek-V4.1-Flash`) repeatedly rewrite the hottest function of a small LLM: `matmul` in Karpathy's [llama2.c](https://github.com/karpathy/llama2.c). The model runs locally on an Apple M3 Pro. A fixed harness that the agents cannot change:

1. compiles each candidate with the same flags as the baseline (`clang -O3`),
2. checks source restrictions (disallowed calls, headers and inline assembly) and runs it with network access denied,
3. requires **identical generated text** to the original on every tested greedy-decoding prompt,
4. measures tokens/sec (one untimed warm-up, then the median of 5 runs). The baseline is re-measured every round, and speedup is reported as a ratio.

Every attempt, winning or failing, is stored in **MongoDB Atlas** with an embedding computed on-device by Ollama (`nomic-embed-text`). Before writing code, each agent retrieves the most relevant past wins and failures through **Atlas Vector Search**, to inform later proposals. Actual retrieval methods and supplied context are recorded in new experiments; the historical run did not record this context.

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
The **held-out** split uses stories110M plus new prompts. It was never used during optimization, its SHA-256 was committed in `HELDOUT_HASH.txt` before the final Atlas run (after the earlier local run), and `heldout.py` refuses to run twice.

## Results (Apple M3 Pro)

### Held-out: fresh tests never used during optimization (run once; `results/heldout.json`)

| Model | Baseline (stock llama2.c, `-O3`) | TokenForge champion | Speedup | OpenMP, `-O3` (reference) |
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

- Dev baseline: 148.5 tok/s (stories15M). OpenMP `-O3` reference: 2.34× on dev.
- 48 candidates; 36 correct. Every attempt is stored in Atlas.
- Luminal tokens used: about 226,000.
- The first full run (`r-20261011-163001`, local JSONL memory) reached a similar plateau (about 6.2×). Its correct-candidate rate rose from 83% to 100% by rounds 7–8. An early 1-round smoke test (`r-20261011-162519`) is included as well.

### What we learned (honest read)
- **The big win comes in round 1**, from NEON SIMD plus multithreading with GCD.
- The later promotions (6.0× → 6.67× on dev) each passed the validation gate, but **they are within our timing noise**: the same champion re-measures between 5.6× and 7.1× on a busy laptop. We do not claim a steady climb after round 1.
- **Amdahl's law is a hypothesis for the plateau.** Profiling is needed to establish whether attention, softmax, and RMSNorm dominate after the matmul optimization. The held-out results show gains across all three model sizes (15M 7.1×, 42M 8.4×, 110M 8.0×), but do not by themselves identify the bottleneck.
- Why clang `-O3` doesn't vectorize the baseline: strict IEEE float rules forbid reordering the sum. The agents reorder it on purpose, and the harness checks identical generated text on the tested prompts; this does not establish equality on every possible input.
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

## Submission evidence and replay

- `docs/index.html`: generated, standalone results page, with one shared throughput scale and an explicit round-zero baseline.
- `results/r-20261011-170439.candidates.jsonl`: all 48 Atlas attempts exported with IDs, parent links and source code. Original outcomes are preserved; one rejection matched a harmless comment containing "execution (", fixed in subsequent evaluator versions.
- `results/comparison.json`: contemporaneous, randomized measurements of the three recorded promotions, scalar baseline and OpenMP reference. Observed ranges are not confidence intervals.
- `results/learning-study/repair.json`: an authentic stored-failure → retrieval → Luminal repair → evaluation trace, recorded in this repository.
- `results/learning-study/summary.json`: a bounded exploratory comparison of champion feedback with and without shared history, recorded in this repository. Neutral, negative and partial outcomes are reported.

The Streamlit dashboard has Results, Experiments, Memory and Code tabs. It defaults to local replay; Atlas refresh is explicit. Historical prompts/retrievals were not recorded and are never reconstructed as observed evidence.

```bash
python scripts/build_report.py --offline --run r-20261011-170439
python scripts/build_report.py --refresh-atlas --run r-20261011-170439
python scripts/compare.py --blocks 10
python learning_study.py --repair-only
# learning_protocol.json must be committed unchanged before starting optimization
python learning_study.py --replicates 2 --rounds 2 --agents 3 --max-minutes 25
```

The study uses separate run IDs and output files and never replaces the submitted kernel or the original held-out result. Proposal counts/settings are matched; observed token consumption may differ. Fresh cases and their hash are committed in `learning_protocol.json` before optimization.

Identical generated text does not imply identical logits or floating-point values. Source scanning plus network denial is a prototype restriction, not general isolation against arbitrary hostile C submissions. The OpenMP reference uses `-O3`, unlike upstream's `make runomp` (`-Ofast -march=native`).

### New verification measurements

Ten randomized blocks, with all five kernels compiled once and warmed, measured the submitted champion at **6.32× on dev and 8.11× on validation**. The initial promoted kernel measured 5.99× / 7.69×. Paired block ratios did not consistently distinguish rounds 4 and 5 from their predecessors. These are new supporting measurements, separate from the original 7.82× held-out result.

The callback-signature failure from historical round 3 was retrieved through the run-filtered Atlas vector index. A fresh Luminal proposal repaired it and passed identical-generated-text checks on development and validation prompts. Its exact prompt, retrieved ID, code and reusable lesson are saved in `repair.json`.

The precommitted pilot completed **24 proposals**, two replicates per condition, with counterbalanced order and isolated memory. Shared-history winners scored **7.45× and 7.24×** on the new two-case fresh split; champion-only winners scored **6.71× and 6.46×**. History produced 10/12 valid candidates, compared with 9/12. This is encouraging exploratory evidence, not a statistically conclusive or causal memory advantage. Recorded usage was 41,854 tokens for history and 36,235 for champion-only; both empty-answer attempts still reported token usage. Code-failure signatures did not repeat in either condition. These study winners never replace the submitted champion.

### Challenge mapping

| Requirement | Evidence |
|---|---|
| Starting baseline | Scalar matmul, compiler flags, baseline timings and round-zero point |
| Working parallel agents | Luminal provider records and six strategy/mode instances |
| Successive rounds | All attempts, three recorded promotions and paired remeasurement |
| Fresh tests | Original held-out artifact with 7.82× geometric-mean recorded gain |
| MongoDB contribution | Atlas candidate archive, run-scoped retrieval and the repair trace |
| On-device contribution | Local TinyLlama inference and Ollama embeddings; cloud agents optimize code |

### Hosting and video

GitHub Pages can serve this already-public report from branch `main`, folder `/docs` (Settings → Pages). Hosting setup is separate from code generation. The required submission video must be uploaded to an accessible video host; a local MP4 is not the submission link. See `docs/video-script.md`.
