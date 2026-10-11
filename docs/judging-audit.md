# Luminal judging evidence audit — October 11, 2026

This maps observed evidence to the supplied rubric; it is not a predicted score or promise of winning.

| Criterion | Weight | Observed evidence | Limits |
|---|---:|---|---|
| Measurable improvement | 40% | Original frozen champion: 7.82× geometric mean on held-out prompts and the unseen 110M model. Same compiler flags and generated-text checks. New ten-block comparison: 6.32× dev / 8.11× validation. | One laptop; tested prompts, not proof for every input. Later promotion gains are not clearly distinguishable. |
| Improvement-loop design | 30% | Six distinct strategy slots, fast/reasoner modes, compile/correctness gates, validation-gated promotion; 48 historical attempts and three promotions. Atlas vector retrieval repaired a real compiler failure. A separate precommitted 24-proposal history pilot favors history in both replicates. | Historical retrieval context is unrecorded. The repair proves feedback use, not a causal memory advantage. Two pilot replicates are exploratory. |
| Effective parallelism | 20% | New matched three-proposal probe: parallel 3.73 seconds / serial 10.70 seconds; all six pass dev checks. Start/end intervals and exact proposals are saved. CPU timing remains sequential. | One batch, parallel first, fast mode only; not a six-agent scaling estimate or quality ablation. Serial best dev gain is 3.78× versus parallel 3.39×. |
| Demo and clarity | 10% | Four-tab working dashboard; standalone offline report; shared validated bundle; reproducible commands and tests; narrated video assembled from actual UI captures and recorded evidence. | Video must be uploaded to an accessible host and checked before submission. |

## Sponsor claims under the latest organizer clarification

- Transpose/Luminal: the self-improving code optimization team is directly aligned. The product is a prototype research workflow; the kernel and memory improve, not model weights.
- MongoDB: actual Atlas storage and run-filtered vector retrieval are verified, with an exact failure → retrieval → repair → evaluation trace and reusable lesson.
- AGI: inference and embeddings are local, but the proposer/decision models run on Luminal. The stricter wording “on-device agents” is not fully established by current evidence. Do not claim eligibility as certain.
- AWS: local S3-export code is prepared. There is no live upload and no AWS payment-system integration. Under the newly supplied clarification, S3 alone does not establish eligibility. The organizer's exact payment product is unknown.
- Bloomerang: no nonprofit interview, validated coordinator workflow or customer demo has been completed.
- Engineering Entrepreneurship: no real sales, signed LOI, invoice, or customer feedback has been recorded. Do not invent evidence.

## Reproduce

```bash
python -m pytest -q
python scripts/build_report.py --offline --run r-20261011-170439
streamlit run app.py
# The one-shot probe is already recorded; the runner refuses to overwrite it.
# Original champion / held-out artifacts remain unchanged.
```

The report identifies historical validation scores, measurement noise, unrecorded retrieval context and the historical false rejection explicitly. The narration uses the original held-out score and the independently recorded parallelism probe; it does not replace the champion with study winners.
