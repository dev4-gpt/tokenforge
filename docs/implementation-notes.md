# TokenForge implementation notes

The existing stack stays small: Python, Streamlit, llama2.c, Luminal and MongoDB Atlas. The reviewed projects informed patterns rather than adding frameworks:

- Autoresearch: a fixed evaluator, bounded experiment budget, and saved keep/fail decisions.
- Hermes: reusable lessons carry a source failure ID and verified scope.
- Cognee: retrieval is scoped to an experiment, records its actual method, and keeps the supplied context inspectable.
- Archify: explicit boundaries between proposer, evaluator, memory, and presentation; both interfaces consume validated evidence.

The original champion and held-out JSON are byte-identical to Claude's `752b6f8` version. New measurements, repair and pilot outputs are separate supporting evidence. Historical prompts and retrieval context are unknown; they are not reconstructed as observed records.

The pilot protocol was committed and pushed before the new optimization began. It completed 24 proposals within the 25-minute limit. All four frozen winners passed the new generated-text checks. Shared history scored higher in both pairs, but two replicates do not establish a conclusive memory advantage. No study winner was substituted into the submitted result.

Verification: 25 tests pass, offline report generation succeeds, candidate counts and champion identity are validated, and both interfaces were inspected at 1280, 768 and 390 pixels in light and dark appearance. Tables and code may scroll within their own panels; the page itself does not scroll horizontally.
