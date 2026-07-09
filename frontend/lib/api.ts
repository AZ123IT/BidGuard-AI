const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DocumentSummary = {
  id: number;
  title: string;
  filename: string;
  content_type: string;
  status: string;
  page_count: number;
  created_at: string | null;
};

export type DocumentDetail = DocumentSummary & {
  chunk_count: number;
  embedding_status: string;
  risk_finding_count: number;
  extracted_fields: Record<
    string,
    { value: string | null; page_number: number | null; confidence: number; evidence_text: string | null }
  >;
  chunks: DocumentChunk[];
  error_message: string | null;
};

export type DocumentChunk = {
  id: number;
  chunk_index: number;
  page_number: number;
  text: string;
  token_count: number;
  embedding_provider: string | null;
  embedding_model: string | null;
  embedding_dimension: number | null;
};

export type Evidence = {
  chunk_id: number | null;
  document_id: number;
  document_title: string;
  page_number: number;
  text: string;
  score: number;
  similarity_score?: number;
  keyword_score?: number;
  retrieval_method?: string;
};

export type QAResponse = {
  answer: string;
  evidence: Evidence[];
  confidence: number;
  llm_synthesis_used?: boolean;
  synthesis_provider?: string | null;
};

export type RiskFinding = {
  document_id: number;
  rule_name: string;
  category: string;
  severity: "low" | "medium" | "high";
  explanation: string;
  evidence_text: string | null;
  page_number: number | null;
};

export type DiffRow = {
  field: string;
  document_a_value: string | null;
  document_b_value: string | null;
  document_a_page: number | null;
  document_b_page: number | null;
  document_a_confidence: number;
  document_b_confidence: number;
  status: "same" | "changed" | "uncertain";
};

export type ToolCall = {
  id: number;
  tool_name: string;
  input_payload: Record<string, unknown>;
  output_payload: unknown;
  latency_ms: number;
  created_at?: string | null;
  status?: "success" | "failed";
  evidence_count?: number;
};

export type AgentRun = {
  id: number;
  objective: string;
  status: string;
  answer: QAResponse | Record<string, unknown> | null;
  latency_ms: number;
  created_at?: string | null;
  tool_calls: ToolCall[];
};

export type DocumentReport = {
  document_id: number;
  document_title: string;
  format: "markdown";
  content: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store"
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof detail.detail === "string" ? detail.detail : "Request failed");
  }
  return response.json() as Promise<T>;
}

export const api = {
  apiBase: API_BASE,
  dashboard: () =>
    request<{ document_count: number; risk_finding_count: number; recent_agent_runs: AgentRun[] }>("/api/dashboard"),
  documents: () => request<{ items: DocumentSummary[] }>("/api/documents"),
  document: (id: number) => request<DocumentDetail>(`/api/documents/${id}`),
  documentReport: (id: number) => request<DocumentReport>(`/api/documents/${id}/report`),
  uploadDocument: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<DocumentDetail>("/api/documents/upload", { method: "POST", body: formData });
  },
  ask: (question: string, documentIds: number[]) =>
    request<QAResponse>("/api/qa", { method: "POST", body: JSON.stringify({ question, document_ids: documentIds }) }),
  riskCheck: (documentId: number) =>
    request<{ document_id: number; findings: RiskFinding[] }>("/api/risk-check", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId })
    }),
  diff: (documentAId: number, documentBId: number) =>
    request<{ document_a_id: number; document_b_id: number; differences: DiffRow[] }>("/api/diff", {
      method: "POST",
      body: JSON.stringify({ document_a_id: documentAId, document_b_id: documentBId })
    }),
  runAgent: (objective: string, documentIds: number[], documentAId?: number, documentBId?: number) =>
    request<AgentRun>("/api/agent/run", {
      method: "POST",
      body: JSON.stringify({
        objective,
        document_ids: documentIds,
        document_a_id: documentAId,
        document_b_id: documentBId
      })
    }),
  agentRuns: () => request<{ items: AgentRun[] }>("/api/agent/runs")
};
