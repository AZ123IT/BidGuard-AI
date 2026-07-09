"use client";

import type { DocumentSummary } from "@/lib/api";

export function DocumentSelect({
  label,
  documents,
  value,
  onChange
}: {
  label: string;
  documents: DocumentSummary[];
  value: number | "";
  onChange: (value: number | "") => void;
}) {
  return (
    <label className="field-label">
      {label}
      <select
        className="control"
        value={value}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : "")}
      >
        <option value="">Select a document</option>
        {documents.map((document) => (
          <option key={document.id} value={document.id}>
            {document.title} ({document.page_count} pages)
          </option>
        ))}
      </select>
    </label>
  );
}
