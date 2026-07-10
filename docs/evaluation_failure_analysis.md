# Evaluation Failure Analysis

## What Was Run

On 2026-07-10, BidGuard AI ran:

- a 36-case workflow regression set covering Q&A, refusal, risk, diff, routing, hard negatives, and prompt injection;
- a separate 16-case retrieval challenge containing direct questions, paraphrases, similar-but-wrong clauses, document-version conflicts, and adversarial text;
- PostgreSQL + pgvector with local Ollama `embeddinggemma` at 64 dimensions;
- a second isolated pgvector experiment using the model's native 768 dimensions;
- guarded synthesis through the real DeepSeek `deepseek-v4-flash` API.

The final workflow eval passed `36/36`. That proves the current end-to-end regression expectations, including the exact insufficient-evidence behavior. It must not be confused with perfect general retrieval quality.

## Retrieval Comparison

| Mode | Dimension | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | Page hit | Answer correctness | Avg query latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Keyword | - | 0.5000 | 0.5625 | 0.5625 | 0.5208 | 0.5312 | 0.5625 | 0.4375 | 0.159 ms |
| Local deterministic hash | 64 | 0.5000 | 0.5625 | 0.5625 | 0.5208 | 0.5312 | 0.5625 | 0.4375 | 0.194 ms |
| Ollama semantic hybrid | 64 | 0.5625 | 0.6875 | 0.6875 | 0.6250 | 0.6414 | 0.6875 | 0.4375 | 95.271 ms |
| PostgreSQL pgvector + Ollama | 64 | 0.5625 | 0.6875 | 0.6875 | 0.6250 | 0.6414 | 0.6875 | 0.4375 | 98.110 ms |
| Ollama semantic hybrid | 768 | 0.5625 | 0.6250 | 0.6250 | 0.5938 | 0.6019 | 0.6250 | 0.4375 | 104.042 ms |
| PostgreSQL pgvector + Ollama | 768 | 0.5625 | 0.6250 | 0.6250 | 0.5938 | 0.6019 | 0.6250 | 0.4375 | 110.710 ms |

Latency is machine- and corpus-dependent. Ollama has zero external API price, but local compute is not literally free. The benchmark uses deterministic sentence selection after retrieval, not DeepSeek synthesis, so answer correctness intentionally isolates a separate extraction limitation. Better retrieval did not automatically improve that metric.

## Real Retrieval Failures

The stronger 64-dimensional semantic row still missed five labelled targets within the top five usable chunks:

- paraphrased dispute handling under the original agreement;
- `financial exposure` phrasing for a liability cap;
- `hand over` phrasing for revised delivery;
- disagreement/forum phrasing for the Riverside tender;
- `end the agreement` phrasing for the termination cure window.

The keyword and local-hash baselines missed those five plus paraphrased deadline and acceptance-test cases. Semantic embeddings therefore improved Recall@5 from `0.5625` to `0.6875`, but did not solve all domain paraphrases and hard negatives.

## Failure Progression

The first real workflow run passed `31/36` and exposed two genuine test-system problems:

1. Three missing-identifier cases returned the exact refusal sentence but still sent weak semantic evidence to DeepSeek. This violated the guard requirement even though the final text was safe.
2. Two correct LLM answers failed brittle contiguous-string checks, including `price is weighted at 40%` versus the expected phrase `Price 40%`.

The identifier gate was made question-aware and now requires a labelled identifier value before synthesis. The keyword metric now permits a bounded number of filler words while a negative test verifies that swapped percentages still fail. The next run passed `35/36`; after retaining actual answer text in reports and correcting the metric, the final run passed `36/36`.

One benchmark run also observed a transient pgvector fallback. The database query path had silently swallowed its exception. Vector-query failures now raise a specific error internally, are logged, and attach a fallback reason when production fallback is used. A strict diagnostic run and the final benchmark both completed through pgvector.

## Cost And Latency

The final 36-case real run recorded:

- total provider tokens: `7,318`;
- embedding tokens: `1,546`;
- LLM tokens: `5,772`;
- aggregate embedding request latency: `3,893.957 ms`;
- aggregate LLM request latency: `29,554.023 ms`;
- average workflow-case latency: `922.112 ms`;
- estimated DeepSeek cost: `$0.00062828`;
- external embedding API cost: `$0` because Ollama ran locally.

Cost uses provider-reported cache-hit, cache-miss, and output token counts with the configured 2026-07-10 DeepSeek USD rates. Prices can change; the report records its cost basis rather than claiming permanent pricing.

## Decision

Do not add a reranker in this phase. The benchmark now demonstrates material ranking failures, so a reranker is a defensible future experiment, but dimension alone did not fix them and 768 dimensions performed worse on this set. The next comparison should first test model-specific query/document encoding or query expansion on a larger human-labelled corpus. A reranker should be added only as another measured row, not as an architecture decoration.

## Residual Risks

- The labelled corpus is synthetic and small.
- The 36/36 workflow result is partly deterministic regression coverage, not legal-quality certification.
- Prompt-injection detection is regex-based and cannot cover every adversarial instruction.
- Answer correctness is rule-based and does not replace human faithfulness review.
- The 64-versus-768 result may not generalize to public Chinese tender documents.
- Local Ollama performance and cost differ from a hosted embedding service.
