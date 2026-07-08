"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Upload } from "lucide-react";

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
      setError("Choose a PDF first.");
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
      <section className="panel grid gap-3 p-4 md:grid-cols-[1fr_auto] md:items-end">
        <label className="grid gap-2 text-sm font-bold">
          PDF file
          <input className="control" type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </label>
        <button className="btn flex items-center justify-center gap-2" onClick={upload} disabled={busy}>
          <Upload size={17} />
          {busy ? "Uploading" : "Upload PDF"}
        </button>
      </section>
      <section className="mt-6">
        <h2 className="mb-3 text-lg font-black">Uploaded Documents</h2>
        {!documents.length ? (
          <EmptyState title="No documents" body="Upload a PDF to create searchable chunks and extracted fields." />
        ) : (
          <div className="grid gap-3">
            {documents.map((document) => (
              <article key={document.id} className="panel grid gap-3 p-4 md:grid-cols-[1fr_auto] md:items-center">
                <div>
                  <Link href={`/documents/${document.id}`} className="font-black underline-offset-4 hover:underline">
                    {document.title}
                  </Link>
                  <div className="mt-1 text-sm text-steel">
                    {document.filename} · {document.page_count} pages
                  </div>
                </div>
                <StatusBadge value={document.status} />
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
