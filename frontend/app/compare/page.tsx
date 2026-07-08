"use client";

import { useEffect, useState } from "react";
import { GitCompareArrows } from "lucide-react";

import { DocumentSelect } from "@/components/DocumentSelect";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type DiffRow, type DocumentSummary } from "@/lib/api";

export default function ComparePage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentAId, setDocumentAId] = useState<number | "">("");
  const [documentBId, setDocumentBId] = useState<number | "">("");
  const [rows, setRows] = useState<DiffRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.documents().then((data) => setDocuments(data.items)).catch((err: Error) => setError(err.message));
  }, []);

  async function compare() {
    if (!documentAId || !documentBId) {
      setError("Select two documents first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await api.diff(documentAId, documentBId);
      setRows(result.differences);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Cross-document Compare"
        title="Compare extracted fields and important clauses."
        body="Field extraction is intentionally simple and marks missing or low-confidence values as uncertain instead of pretending the comparison is complete."
      />
      <ErrorBanner message={error} />
      <section className="panel grid gap-4 p-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
        <DocumentSelect label="Document A" documents={documents} value={documentAId} onChange={setDocumentAId} />
        <DocumentSelect label="Document B" documents={documents} value={documentBId} onChange={setDocumentBId} />
        <button className="btn flex items-center justify-center gap-2" onClick={compare} disabled={busy}>
          <GitCompareArrows size={17} />
          {busy ? "Comparing" : "Compare"}
        </button>
      </section>
      <section className="mt-6">
        {!rows.length ? (
          <EmptyState title="No comparison" body="Run a comparison to see key fields, values, page references, and uncertainty markers." />
        ) : (
          <div className="overflow-hidden border border-line bg-white/80">
            <div className="table-grid bg-ink text-xs font-black uppercase tracking-[0.18em] text-white">
              <div className="p-3">Field</div>
              <div className="p-3">Document A</div>
              <div className="p-3">Document B</div>
              <div className="p-3">Status</div>
            </div>
            {rows.map((row) => (
              <div key={row.field} className="table-grid border-t border-line text-sm">
                <div className="p-3 font-black">{row.field.replaceAll("_", " ")}</div>
                <div className="p-3">
                  {row.document_a_value ?? "Not found"}
                  {row.document_a_page ? <span className="ml-2 text-xs font-bold text-steel">p.{row.document_a_page}</span> : null}
                </div>
                <div className="p-3">
                  {row.document_b_value ?? "Not found"}
                  {row.document_b_page ? <span className="ml-2 text-xs font-bold text-steel">p.{row.document_b_page}</span> : null}
                </div>
                <div className="p-3">
                  <StatusBadge value={row.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
