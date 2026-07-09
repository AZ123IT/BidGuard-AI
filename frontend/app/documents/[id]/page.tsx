"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type DocumentChunk, type DocumentDetail } from "@/lib/api";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const documentId = useMemo(() => Number(params.id), [params.id]);
  const selectedPage = Number(searchParams.get("page"));
  const selectedChunkId = Number(searchParams.get("chunk"));
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
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

  async function downloadReport() {
    if (!document) {
      return;
    }
    setReportBusy(true);
    setError(null);
    try {
      const report = await api.documentReport(document.id);
      const blob = new Blob([report.content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = `${slugify(report.document_title)}-bidguard-review.md`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setReportBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Document Detail"
        title={document?.title ?? "Document detail"}
        body="Inspect parse status, extracted fields, and page-aware chunks used as cited evidence."
      />
      <ErrorBanner message={error} />
      {!document ? (
        <EmptyState title="Loading detail" body="Document metadata and extracted fields will appear here." />
      ) : (
        <div className="grid gap-5">
          <section className="grid gap-3 md:grid-cols-4">
            <Metric label="Status" value={<StatusBadge value={document.status} />} />
            <Metric label="Pages" value={document.page_count} />
            <Metric label="Chunks" value={document.chunk_count} />
            <Metric label="Embeddings" value={document.embedding_status.replaceAll("_", " ")} />
          </section>

          <section className="panel-strong p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-3xl font-bold">Document Metadata</h2>
                <p className="mt-1 text-sm text-muted">{document.filename}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="btn flex items-center gap-2" onClick={downloadReport} disabled={reportBusy}>
                  <Download size={16} />
                  {reportBusy ? "Preparing" : "Download report"}
                </button>
                <Link className="btn btn-secondary" href="/documents">
                  Back to documents
                </Link>
              </div>
            </div>
            <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
              <MetadataItem label="Content type" value={document.content_type} />
              <MetadataItem label="Created" value={document.created_at ? new Date(document.created_at).toLocaleString() : "Unknown"} />
              <MetadataItem label="Risk findings" value={String(document.risk_finding_count)} />
            </div>
            {document.error_message ? <ErrorBanner message={document.error_message} /> : null}
          </section>

          <section className="panel p-4">
            <h2 className="font-display text-2xl font-bold">Extracted Fields</h2>
            <div className="mt-4 overflow-hidden rounded-lg border border-line bg-surface/90">
              <div className="grid grid-cols-1 border-b border-line bg-field text-xs font-semibold uppercase text-muted md:grid-cols-[170px_1fr_90px_110px]">
                <div className="p-3">Field</div>
                <div className="p-3">Value</div>
                <div className="p-3">Page</div>
                <div className="p-3">Confidence</div>
              </div>
              {Object.entries(document.extracted_fields).length ? (
                Object.entries(document.extracted_fields).map(([name, field]) => (
                  <div key={name} className="grid grid-cols-1 border-t border-line text-sm md:grid-cols-[170px_1fr_90px_110px]">
                    <div className="p-3 font-semibold capitalize">{name.replaceAll("_", " ")}</div>
                    <div className="p-3">
                      <div>{field.value ?? "Not found"}</div>
                      {field.evidence_text ? <div className="mt-1 text-xs leading-5 text-muted">{field.evidence_text}</div> : null}
                    </div>
                    <div className="p-3">{field.page_number ?? "-"}</div>
                    <div className="p-3">{field.confidence.toFixed(2)}</div>
                  </div>
                ))
              ) : (
                <div className="border-t border-line p-3 text-sm text-muted">No extracted fields were stored for this document.</div>
              )}
            </div>
          </section>

          <section className="panel p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-2xl font-bold">Evidence Chunks</h2>
                <p className="mt-1 text-sm text-muted">
                  Chunks are grouped by page and match the source links shown in Q&A evidence cards.
                </p>
              </div>
              {Number.isFinite(selectedPage) ? (
                <span className="rounded-full border border-line bg-accent px-3 py-1 text-xs font-semibold uppercase text-white">
                  Source target: page {selectedPage}
                  {Number.isFinite(selectedChunkId) ? ` / chunk ${selectedChunkId}` : ""}
                </span>
              ) : null}
            </div>
            <div className="mt-4 grid gap-4">
              {groupChunksByPage(document.chunks).map(([pageNumber, chunks]) => (
                <section key={pageNumber} className="overflow-hidden rounded-lg border border-line bg-surface/80">
                  <div className="border-b border-line bg-field px-3 py-2 text-sm font-semibold">Page {pageNumber}</div>
                  <div className="grid gap-3 p-3">
                    {chunks.map((chunk) => {
                      const isSelected =
                        (Number.isFinite(selectedChunkId) && selectedChunkId === chunk.id) ||
                        (!Number.isFinite(selectedChunkId) && Number.isFinite(selectedPage) && selectedPage === chunk.page_number);
                      return <ChunkPreview key={chunk.id} chunk={chunk} selected={isSelected} />;
                    })}
                  </div>
                </section>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 80) || "document";
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="metric-card p-4">
      <div className="text-xs font-semibold uppercase text-muted">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface/80 p-3">
      <div className="text-xs font-semibold uppercase text-muted">{label}</div>
      <div className="mt-1 font-bold">{value}</div>
    </div>
  );
}

function ChunkPreview({ chunk, selected }: { chunk: DocumentChunk; selected: boolean }) {
  return (
    <article
      id={`chunk-${chunk.id}`}
      className={`rounded-lg border p-3 ${selected ? "border-accent bg-[#eef6ff] shadow-soft" : "border-line bg-surface"}`}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase text-muted">
        <span>Chunk {chunk.id}</span>
        <span>Index {chunk.chunk_index}</span>
        <span>{chunk.token_count} tokens</span>
        {chunk.embedding_provider ? <span>{chunk.embedding_provider}</span> : null}
        {chunk.embedding_dimension ? <span>{chunk.embedding_dimension}d</span> : null}
      </div>
      <p className="mt-2 text-sm leading-6">{chunk.text}</p>
    </article>
  );
}

function groupChunksByPage(chunks: DocumentChunk[]): [number, DocumentChunk[]][] {
  const groups = new Map<number, DocumentChunk[]>();
  for (const chunk of chunks) {
    const pageChunks = groups.get(chunk.page_number) ?? [];
    pageChunks.push(chunk);
    groups.set(chunk.page_number, pageChunks);
  }
  return Array.from(groups.entries()).sort(([left], [right]) => left - right);
}
