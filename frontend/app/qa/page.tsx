"use client";

import { useEffect, useState } from "react";
import { Search, ShieldCheck } from "lucide-react";

import { DocumentSelect } from "@/components/DocumentSelect";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { EvidenceList } from "@/components/EvidenceList";
import { PageHeader } from "@/components/PageHeader";
import { api, type DocumentSummary, type QAResponse } from "@/lib/api";

const suggestedQuestions = [
  "What is the bid deadline for the solar microgrid project?",
  "What are the payment terms in the contract draft?",
  "Are the acceptance criteria clearly defined?",
  "What is the vendor tax ID?"
];

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
      <section className="panel-strong grid gap-4 p-5">
        <DocumentSelect label="Document" documents={documents} value={documentId} onChange={setDocumentId} />
        <label className="field-label">
          Question
          <textarea className="control min-h-28" value={question} onChange={(event) => setQuestion(event.target.value)} />
        </label>
        <div className="flex flex-wrap gap-2">
          {suggestedQuestions.map((item) => (
            <button
              key={item}
              type="button"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-left text-xs font-medium leading-5 text-muted hover:border-accent hover:bg-accent hover:text-white sm:w-auto sm:rounded-full sm:py-1.5 sm:text-center"
              onClick={() => setQuestion(item)}
            >
              {item}
            </button>
          ))}
        </div>
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
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="kicker">Final Answer</div>
                <div className="flex items-center gap-2 rounded-full border border-line bg-field px-3 py-1 text-xs font-semibold uppercase text-muted">
                  <ShieldCheck size={14} />
                  Evidence gate
                </div>
              </div>
              <p className="mt-4 text-lg font-bold leading-8 md:text-xl">{answer.answer}</p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold uppercase text-muted">
                <span className="rounded-full border border-line bg-surface px-2 py-1">Confidence {answer.confidence.toFixed(2)}</span>
                <span className="rounded-full border border-line bg-surface px-2 py-1">
                  LLM synthesis {answer.llm_synthesis_used ? "used" : "skipped"}
                </span>
                {answer.synthesis_provider ? (
                  <span className="rounded-full border border-line bg-surface px-2 py-1">{answer.synthesis_provider}</span>
                ) : null}
                {!answer.evidence.length ? (
                  <span className="rounded-full border border-oxide bg-[#fff4f0] px-2 py-1 text-oxide">Insufficient evidence</span>
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
