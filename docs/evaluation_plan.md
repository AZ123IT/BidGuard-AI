# Evaluation Plan

Phase 2.1 ships a small deterministic runner:

```bash
cd backend
.venv/bin/python -m app.evaluation.run_eval
```

The runner loads `data/eval_cases/rag_smoke.json`, ensures the sample tender is available, runs Q&A or agent calls, and prints JSON metrics.

## Metrics

- Retrieval hit rate: whether expected evidence appears in the top-k retrieved chunks.
- Context recall: whether enough supporting context is retrieved for the answer.
- Faithfulness: whether generated answers are fully supported by cited evidence.
- Answer relevance: whether the answer addresses the user question.
- Tool call accuracy: whether the agent selected the right tool sequence.
- Latency: endpoint and tool-call execution time.
- Token cost: future LLM and embedding provider usage cost.

## Test Sets

1. Direct lookup questions where the answer is present on one page.
2. Missing-evidence questions where refusal is expected.
3. Risk-rule cases with known payment, acceptance, dispute, and scoring findings.
4. Cross-document comparisons with one controlled field changed.
5. Agent objectives that should trigger retrieval only, risk plus retrieval, or diff plus retrieval.

## Scoring Approach

Start with deterministic checks:

- expected page appears in top 3 evidence chunks,
- unsupported questions return the exact insufficient-evidence sentence,
- expected risk rule names appear,
- changed fields are marked changed,
- uncertain fields are not presented as certain.

Only after this baseline should LLM-judged faithfulness or Ragas integration be introduced.
