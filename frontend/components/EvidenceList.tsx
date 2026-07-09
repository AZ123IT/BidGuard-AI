import Link from "next/link";
import type { ReactNode } from "react";

import type { Evidence } from "@/lib/api";

export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) {
    return null;
  }
  return (
    <div className="grid gap-3">
      {evidence.map((item) => (
        <article key={`${item.document_id}-${item.chunk_id}-${item.page_number}`} className="panel evidence-rail p-4">
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase text-muted">
            <span className="font-mono-ui text-ink">{item.document_title}</span>
            <EvidenceBadge>Page {item.page_number}</EvidenceBadge>
            <EvidenceBadge>Chunk {item.chunk_id ?? "n/a"}</EvidenceBadge>
            <EvidenceBadge>Score {item.score.toFixed(2)}</EvidenceBadge>
            {typeof item.similarity_score === "number" ? (
              <EvidenceBadge>Similarity {item.similarity_score.toFixed(2)}</EvidenceBadge>
            ) : null}
            {typeof item.keyword_score === "number" ? (
              <EvidenceBadge>Keyword {item.keyword_score.toFixed(2)}</EvidenceBadge>
            ) : null}
            {item.retrieval_method ? <EvidenceBadge>{item.retrieval_method.replaceAll("_", " ")}</EvidenceBadge> : null}
          </div>
          <p className="mt-3 text-sm leading-6 text-ink">{item.text}</p>
          <Link
            className="mt-3 inline-flex items-center rounded-full border border-line bg-surface px-3 py-1.5 text-sm font-semibold text-accent hover:border-accent hover:bg-accent hover:text-white"
            href={`/documents/${item.document_id}?page=${item.page_number}${
              item.chunk_id ? `&chunk=${item.chunk_id}` : ""
            }`}
          >
            Open source chunk
          </Link>
        </article>
      ))}
    </div>
  );
}

function EvidenceBadge({ children }: { children: ReactNode }) {
  return <span className="rounded-full border border-line bg-surface px-2 py-1 text-ink">{children}</span>;
}
