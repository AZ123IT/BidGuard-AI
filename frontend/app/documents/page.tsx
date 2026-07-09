"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FileText, Upload } from "lucide-react";

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
      <section className="panel-strong grid gap-4 p-5 md:grid-cols-[1fr_auto] md:items-end">
        <label className="field-label">
          PDF, DOCX, or TXT file
          <input
            className="control"
            type="file"
            accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <span className="text-xs font-semibold text-muted">
            {file ? `${file.name} selected` : "Public tender or contract PDF/DOCX/TXT files work best for this demo."}
          </span>
        </label>
        <button className="btn flex items-center justify-center gap-2" onClick={upload} disabled={busy}>
          <Upload size={17} />
          {busy ? "Uploading" : "Upload document"}
        </button>
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
