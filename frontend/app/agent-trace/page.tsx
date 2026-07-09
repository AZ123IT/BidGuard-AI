"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Play, RefreshCw } from "lucide-react";

import { DocumentSelect } from "@/components/DocumentSelect";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { PageHeader } from "@/components/PageHeader";
import { api, type AgentRun, type DocumentSummary } from "@/lib/api";

export default function AgentTracePage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentId, setDocumentId] = useState<number | "">("");
  const [objective, setObjective] = useState("Run a risk review and summarize the evidence.");
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [documentData, traceData] = await Promise.all([api.documents(), api.agentRuns()]);
    setDocuments(documentData.items);
    setRuns(traceData.items);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function runAgent() {
    if (!documentId) {
      setError("Select a document first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.runAgent(objective, [documentId]);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Agent Trace"
        title="Every workflow shows which tool was called."
        body="The agent is intentionally lightweight: it chooses retrieval, risk checking, comparison, and report tools, logs inputs and outputs, and exposes latency."
      />
      <ErrorBanner message={error} />
      <section className="panel-strong grid gap-4 p-5">
        <DocumentSelect label="Document" documents={documents} value={documentId} onChange={setDocumentId} />
        <label className="field-label">
          Objective
          <textarea className="control min-h-24" value={objective} onChange={(event) => setObjective(event.target.value)} />
        </label>
        <div className="flex flex-wrap gap-2">
          <button className="btn flex items-center gap-2" onClick={runAgent} disabled={busy}>
            <Play size={17} />
            {busy ? "Running" : "Run Agent"}
          </button>
          <button className="btn btn-secondary flex items-center gap-2" onClick={() => load()} disabled={busy}>
            <RefreshCw size={17} />
            Refresh Trace
          </button>
        </div>
      </section>
      <section className="mt-6 grid gap-4">
        {!runs.length ? (
          <EmptyState title="No agent runs" body="Run an objective to record tool calls and inspect the trace." />
        ) : (
          runs.map((run) => (
            <article key={run.id} className="panel p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-display text-2xl font-bold">{run.objective}</div>
                  <div className="mt-1 text-xs font-bold uppercase text-muted">
                    Run #{run.id} · {run.status} · {run.latency_ms} ms
                    {run.created_at ? ` · ${new Date(run.created_at).toLocaleString()}` : ""}
                  </div>
                </div>
              </div>
              {getAnswerText(run.answer) ? (
                <div className="mt-4 rounded-lg border border-line bg-surface p-3">
                  <div className="text-xs font-semibold uppercase text-muted">Final answer</div>
                  <p className="mt-1 text-sm font-semibold leading-6">{getAnswerText(run.answer)}</p>
                </div>
              ) : null}
              <div className="mt-4 grid gap-3">
                {run.tool_calls.map((call, index) => (
                  <details key={call.id} className="rounded-lg border border-line bg-surface/80 p-3 open:shadow-soft">
                    <summary className="cursor-pointer font-semibold marker:text-accent">
                      {index + 1}. {call.tool_name} · {call.status ?? "success"} · {call.latency_ms} ms ·{" "}
                      {call.evidence_count ?? 0} evidence
                    </summary>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold uppercase text-muted">
                      {call.created_at ? <TraceBadge>{new Date(call.created_at).toLocaleString()}</TraceBadge> : null}
                      {getRetrievalMethods(call.output_payload).map((method) => (
                        <TraceBadge key={method}>{method.replaceAll("_", " ")}</TraceBadge>
                      ))}
                    </div>
                    <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                      <TraceSummary label="Input" value={summarizePayload(call.input_payload)} />
                      <TraceSummary label="Output" value={summarizePayload(call.output_payload)} />
                    </div>
                    <pre className="mt-3 max-h-72 overflow-auto rounded-lg bg-[#1c1c1e] p-3 text-xs leading-5 text-white">
                      {JSON.stringify({ input: call.input_payload, output: call.output_payload }, null, 2)}
                    </pre>
                  </details>
                ))}
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}

function TraceSummary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-field p-3">
      <div className="text-xs font-semibold uppercase text-muted">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}

function TraceBadge({ children }: { children: ReactNode }) {
  return <span className="rounded-full border border-line bg-field px-2 py-1">{children}</span>;
}

function getAnswerText(answer: AgentRun["answer"]): string {
  if (!answer || typeof answer !== "object") {
    return "";
  }
  const record = answer as Record<string, unknown>;
  return typeof record.answer === "string" ? record.answer : "";
}

function getRetrievalMethods(payload: unknown): string[] {
  const evidence = extractEvidence(payload);
  return Array.from(
    new Set(
      evidence
        .map((item) => item.retrieval_method)
        .filter((method): method is string => typeof method === "string" && method.length > 0)
    )
  );
}

function extractEvidence(payload: unknown): Record<string, unknown>[] {
  if (Array.isArray(payload)) {
    return payload.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
  }
  if (!payload || typeof payload !== "object") {
    return [];
  }
  const evidence = (payload as Record<string, unknown>).evidence;
  if (!Array.isArray(evidence)) {
    return [];
  }
  return evidence.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
}

function summarizePayload(payload: unknown): string {
  if (Array.isArray(payload)) {
    const methods = getRetrievalMethods(payload);
    return `${payload.length} item${payload.length === 1 ? "" : "s"}${
      methods.length ? ` · ${methods.map((method) => method.replaceAll("_", " ")).join(", ")}` : ""
    }`;
  }
  if (!payload || typeof payload !== "object") {
    return String(payload ?? "empty");
  }
  const record = payload as Record<string, unknown>;
  if (typeof record.answer === "string") {
    return record.answer.slice(0, 140);
  }
  if (typeof record.question === "string") {
    return record.question;
  }
  if (typeof record.objective === "string") {
    return record.objective;
  }
  if (typeof record.document_id === "number") {
    return `Document ${record.document_id}`;
  }
  if (typeof record.evidence_count === "number") {
    return `${record.evidence_count} evidence chunk${record.evidence_count === 1 ? "" : "s"}`;
  }
  const evidence = extractEvidence(payload);
  if (evidence.length) {
    return `${evidence.length} evidence chunk${evidence.length === 1 ? "" : "s"}`;
  }
  return Object.keys(record).slice(0, 4).join(", ") || "object";
}
