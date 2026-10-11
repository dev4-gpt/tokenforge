# TokenForge — 90-second submission video

Use actual saved experiments and measurements. Cloud agents optimize the code; the small inference model runs locally.

| Time | Screen | Narration |
|---|---|---|
| 0–12s | Results overview and scalar baseline | “TokenForge is a research team for faster local AI. We start with llama2.c’s scalar matrix-vector kernel.” |
| 12–28s | Six agent instances and recorded attempts | “Six Luminal-hosted DeepSeek agents explore different strategies in parallel. A fixed evaluator compiles each proposal, checks generated text, and measures throughput.” |
| 28–48s | Memory tab: exact failure, retrieved source ID, prompt, repaired code and check | “Atlas preserves experiments and supplies useful feedback to later proposals. Here is a real callback compilation failure, the retrieved evidence, and a new repair checked by the evaluator.” “The repair passed development and validation checks.” |
| 48–65s | Round-zero baseline, three promotions, contemporaneous comparison | “We record every attempt and promotion. We remeasure the kernels together so a noisy chart is not mistaken for progress.” “The big gain is in round one; later promotions remain uncertain. A separate 24-proposal pilot favors shared history in both replicates, but is exploratory.” |
| 65–82s | Held-out chart and local inference | “The submitted champion records 7.82 times the scalar baseline across three fresh workloads. The 110-million-parameter model rises from 13.9 to 110.3 tokens per second on this laptop, with matching generated text on its tested prompt.” |
| 82–90s | Frozen artifact hash and repository | “TokenForge makes research auditable: propose, test, retrieve, and learn. All code, attempts and measured evidence are in the public repository.” |

If the exploratory memory study is neutral, negative or incomplete, state that plainly. Do not narrate a causal memory benefit from the repair trace alone. Record with macOS screen capture, trim to 90 seconds, upload and verify access while signed out. Add the hosted URL to the submission form.
