"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, FileText, FolderOpen, Upload } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type DocumentSummary } from "@/lib/api";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocuments = () => api.documents().then((data) => setDocuments(data.items));

  useEffect(() => {
    loadDocuments().catch((err: Error) => setError(err.message));
  }, []);

  async function upload() {
    if (!file) {
      setError("Choose a PDF, DOCX, or TXT file first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.uploadDocument(file);
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      await loadDocuments();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Documents"
        title="Upload and parse public procurement files."
        body="The MVP parses text with PyMuPDF, stores page-aware chunks, extracts fields with simple rules, and keeps parse status visible."
      />
      <ErrorBanner message={error} />
      <section className="panel-strong p-5">
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <div className="field-label">
            <span>PDF, DOCX, or TXT file</span>
            <div className="flex min-h-[46px] min-w-0 items-stretch overflow-hidden rounded-lg border border-line bg-white shadow-[inset_0_1px_0_rgba(255,255,255,0.75)] focus-within:border-accent focus-within:ring-4 focus-within:ring-blue-500/10">
              <button
                type="button"
                className="inline-flex shrink-0 items-center gap-2 border-r border-line bg-field px-4 text-sm font-semibold text-ink hover:bg-blue-50 hover:text-accent disabled:cursor-not-allowed disabled:opacity-60"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy}
              >
                <FolderOpen size={16} />
                Choose file
              </button>
              <span className="min-w-0 flex-1 truncate px-4 py-3 text-sm font-medium text-muted">
                {file?.name ?? "No file selected"}
              </span>
            </div>
            <input
              ref={fileInputRef}
              className="sr-only"
              type="file"
              accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </div>
          <button
            type="button"
            className="btn flex h-[46px] items-center justify-center gap-2 whitespace-nowrap md:min-w-[196px]"
            onClick={upload}
            disabled={busy}
          >
            <Upload size={17} />
            {busy ? "Uploading" : "Upload document"}
          </button>
        </div>
        <p className="mt-2 text-xs font-semibold text-muted">
          Public tender or contract PDF/DOCX/TXT files work best for this demo.
        </p>
      </section>
      <section className="mt-6">
        <h2 className="mb-3 font-display text-2xl font-bold">Uploaded Documents</h2>
        {!documents.length ? (
          <EmptyState title="No documents" body="Upload a PDF to create searchable chunks and extracted fields." />
        ) : (
          <div className="grid gap-3">
            {documents.map((document) => (
              <article key={document.id} className="panel grid gap-4 p-4 md:grid-cols-[auto_1fr_auto] md:items-center">
                <div className="grid h-12 w-12 place-items-center rounded-lg border border-line bg-field">
                  <FileText size={20} />
                </div>
                <div className="min-w-0">
                  <Link href={`/documents/${document.id}`} className="font-semibold underline-offset-4 hover:underline">
                    {document.title}
                  </Link>
                  <div className="mt-1 text-sm text-muted">
                    {document.filename} · {document.page_count} pages
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 md:justify-end">
                  <StatusBadge value={document.status} />
                  <Link className="btn btn-secondary flex items-center gap-2 py-2 text-sm" href={`/documents/${document.id}`}>
                    Open
                    <ArrowRight size={15} />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
