"use client";

import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";

import { DocumentSelect } from "@/components/DocumentSelect";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type DocumentSummary, type RiskFinding } from "@/lib/api";

export default function RiskPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentId, setDocumentId] = useState<number | "">("");
  const [findings, setFindings] = useState<RiskFinding[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.documents().then((data) => setDocuments(data.items)).catch((err: Error) => setError(err.message));
  }, []);

  async function runReview() {
    if (!documentId) {
      setError("Select a document first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await api.riskCheck(documentId);
      setFindings(result.findings);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Risk Rules"
        title="Rule-based checks with inspectable evidence."
        body="The MVP uses a small built-in rule set for payment periods, vague acceptance, missing dispute resolution, unquantified scoring, and related procurement risks."
      />
      <ErrorBanner message={error} />
      <section className="panel grid gap-4 p-4 md:grid-cols-[1fr_auto] md:items-end">
        <DocumentSelect label="Document" documents={documents} value={documentId} onChange={setDocumentId} />
        <button className="btn flex items-center justify-center gap-2" onClick={runReview} disabled={busy}>
          <ShieldAlert size={17} />
          {busy ? "Checking" : "Run Risk Review"}
        </button>
      </section>
      <section className="mt-6 grid gap-3">
        {!findings.length ? (
          <EmptyState title="No findings loaded" body="Run the risk checker to see structured findings and page evidence." />
        ) : (
          findings.map((finding, index) => (
            <article key={`${finding.rule_name}-${index}`} className="panel p-4">
              <div className="flex flex-wrap items-center gap-3">
                <StatusBadge value={finding.severity} />
                <span className="rounded-full border border-line px-2 py-1 text-xs font-black uppercase tracking-[0.08em] text-steel">
                  {finding.category.replaceAll("_", " ")}
                </span>
                <div className="font-black">{finding.rule_name}</div>
                {finding.page_number ? <span className="text-sm font-bold text-steel">Page {finding.page_number}</span> : null}
              </div>
              <p className="mt-3 text-sm leading-6">{finding.explanation}</p>
              {finding.evidence_text ? <blockquote className="mt-3 border-l-4 border-signal pl-3 text-sm">{finding.evidence_text}</blockquote> : null}
            </article>
          ))
        )}
      </section>
    </div>
  );
}
