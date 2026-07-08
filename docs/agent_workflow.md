# Agent Workflow

## Tools

### evidence_search_tool

Input: `question`, `document_ids`.

Output: ranked chunks with `document_id`, `document_title`, `page_number`, `text`, `score`, `similarity_score`, `keyword_score`, and `retrieval_method`.

### guarded_llm_synthesis

Input: `question` and retrieved evidence chunks.

Output: final answer, evidence list, confidence, synthesis provider, and whether LLM synthesis was used. The backend skips this tool if evidence is weak or empty.

### risk_rule_check_tool

Input: `document_id`.

Output: matched rules with severity, explanation, evidence text, and page number when available.

### cross_doc_diff_tool

Input: `document_a_id`, `document_b_id`.

Output: rows for project name, buyer, supplier, bid deadline, opening time, amount, payment terms, delivery date, acceptance criteria, liability, and dispute resolution.

### report_generator_tool

Input: `document_id`, findings, and evidence.

Output: structured summary and disclaimer that this is not legal advice.

## Routing Logic

The MVP agent is not a multi-agent system. It uses simple intent routing:

- If document comparison IDs are supplied, call `cross_doc_diff_tool`.
- If the objective includes risk/review/check/report, call `risk_rule_check_tool`.
- If the objective asks for a report, call `report_generator_tool`.
- If document IDs are supplied, call `evidence_search_tool`.
- If retrieved evidence passes the backend sufficiency gate, call `guarded_llm_synthesis`.
- If evidence is weak or empty, return the fixed insufficient-evidence response without calling the LLM.

Every tool call is stored in `tool_calls` with input, output, and latency. API trace responses also include status and evidence count summaries. The run is stored in `agent_runs`.

## Failure Behavior

If a document does not exist, the API returns a 404. If evidence search finds no usable chunks, the answer is the fixed insufficient-evidence message. The agent does not invent citations.
