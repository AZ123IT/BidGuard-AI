"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type DocumentDetail } from "@/lib/api";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentId = useMemo(() => Number(params.id), [params.id]);
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(documentId)) {
      setError("Invalid document id.");
      return;
    }
    api
      .document(documentId)
      .then(setDocument)
      .catch((err: Error) => setError(err.message));
  }, [documentId]);

  return (
    <div>
      <PageHeader
        eyebrow="Document Detail"
        title={document?.title ?? "Document detail"}
        body="Inspect parse status, chunk count, and extracted fields from the backend document detail endpoint."
      />
      <ErrorBanner message={error} />
      {!document ? (
        <EmptyState title="Loading detail" body="Document metadata and extracted fields will appear here." />
      ) : (
        <div className="grid gap-5">
          <section className="panel grid gap-3 p-4 md:grid-cols-4">
            <Metric label="Status" value={<StatusBadge value={document.status} />} />
            <Metric label="Pages" value={document.page_count} />
            <Metric label="Chunks" value={document.chunk_count} />
            <Metric label="Risk Findings" value={document.risk_finding_count} />
          </section>

          <section className="panel p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-black">Extracted Fields</h2>
                <p className="mt-1 text-sm text-steel">{document.filename}</p>
              </div>
              <Link className="btn btn-secondary" href="/documents">
                Back to documents
              </Link>
            </div>
            <div className="mt-4 overflow-hidden border border-line bg-white/80">
              <div className="grid grid-cols-1 bg-ink text-xs font-black uppercase tracking-[0.18em] text-white md:grid-cols-[180px_1fr_100px]">
                <div className="p-3">Field</div>
                <div className="p-3">Value</div>
                <div className="p-3">Page</div>
              </div>
              {Object.entries(document.extracted_fields).map(([name, field]) => (
                <div key={name} className="grid grid-cols-1 border-t border-line text-sm md:grid-cols-[180px_1fr_100px]">
                  <div className="p-3 font-black">{name.replaceAll("_", " ")}</div>
                  <div className="p-3">{field.value ?? "Not found"}</div>
                  <div className="p-3">{field.page_number ?? "-"}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-black uppercase tracking-[0.18em] text-steel">{label}</div>
      <div className="mt-2 text-2xl font-black">{value}</div>
    </div>
  );
}
