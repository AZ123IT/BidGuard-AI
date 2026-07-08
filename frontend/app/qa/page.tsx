"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { DocumentSelect } from "@/components/DocumentSelect";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { EvidenceList } from "@/components/EvidenceList";
import { PageHeader } from "@/components/PageHeader";
import { api, type DocumentSummary, type QAResponse } from "@/lib/api";

export default function QAPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentId, setDocumentId] = useState<number | "">("");
  const [question, setQuestion] = useState("What is the bid deadline?");
  const [answer, setAnswer] = useState<QAResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.documents().then((data) => setDocuments(data.items)).catch((err: Error) => setError(err.message));
  }, []);

  async function ask() {
    if (!documentId) {
      setError("Select a document first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setAnswer(await api.ask(question, [documentId]));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Document Q&A"
        title="Answers must cite the uploaded document."
        body="The backend ranks stored chunks and returns the final answer with document title, page number, snippet, and retrieval confidence."
      />
      <ErrorBanner message={error} />
      <section className="panel grid gap-4 p-4">
        <DocumentSelect label="Document" documents={documents} value={documentId} onChange={setDocumentId} />
        <label className="grid gap-2 text-sm font-bold">
          Question
          <textarea className="control min-h-28" value={question} onChange={(event) => setQuestion(event.target.value)} />
        </label>
        <button className="btn flex w-fit items-center gap-2" onClick={ask} disabled={busy}>
          <Search size={17} />
          {busy ? "Searching" : "Ask with evidence"}
        </button>
      </section>
      <section className="mt-6 grid gap-4">
        {!answer ? (
          <EmptyState title="No answer yet" body="Ask a question to see the evidence-first response shape." />
        ) : (
          <>
            <div className="panel p-5">
              <div className="text-xs font-black uppercase tracking-[0.2em] text-steel">Final Answer</div>
              <p className="mt-3 text-lg font-bold leading-7">{answer.answer}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs font-black uppercase tracking-[0.14em] text-steel">
                <span className="border border-line bg-white px-2 py-1">Confidence {answer.confidence.toFixed(2)}</span>
                <span className="border border-line bg-white px-2 py-1">
                  LLM synthesis {answer.llm_synthesis_used ? "used" : "skipped"}
                </span>
                {answer.synthesis_provider ? (
                  <span className="border border-line bg-white px-2 py-1">{answer.synthesis_provider}</span>
                ) : null}
                {!answer.evidence.length ? (
                  <span className="border border-oxide bg-[#fff4f0] px-2 py-1 text-oxide">Insufficient evidence</span>
                ) : null}
              </div>
            </div>
            <EvidenceList evidence={answer.evidence} />
          </>
        )}
      </section>
    </div>
  );
}
