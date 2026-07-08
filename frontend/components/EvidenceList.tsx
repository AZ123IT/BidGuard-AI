import type { Evidence } from "@/lib/api";

export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) {
    return null;
  }
  return (
    <div className="grid gap-3">
      {evidence.map((item) => (
        <article key={`${item.document_id}-${item.chunk_id}-${item.page_number}`} className="panel p-4">
          <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-steel">
            <span>{item.document_title}</span>
            <span className="bg-signal px-2 py-1 text-ink">Page {item.page_number}</span>
            <span>Score {item.score.toFixed(2)}</span>
            {typeof item.similarity_score === "number" ? <span>Similarity {item.similarity_score.toFixed(2)}</span> : null}
            {item.retrieval_method ? <span>{item.retrieval_method.replaceAll("_", " ")}</span> : null}
          </div>
          <p className="mt-3 text-sm leading-6">{item.text}</p>
        </article>
      ))}
    </div>
  );
}
