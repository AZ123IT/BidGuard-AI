export function StatusBadge({ value }: { value: string }) {
  const className =
    value === "high"
      ? "border-oxide bg-[#fff4f0] text-oxide"
      : value === "medium"
        ? "border-[var(--amber)] bg-[#fff9dc] text-[#6a5100]"
        : value === "low"
          ? "border-success bg-[#eefaf1] text-[#248a3d]"
          : value === "changed"
            ? "border-oxide bg-[#fff4f0] text-oxide"
            : value === "uncertain"
              ? "border-[var(--amber)] bg-[#fff9dc] text-[#6a5100]"
              : value === "same" || value === "complete"
                ? "border-success bg-[#eefaf1] text-[#248a3d]"
                : "border-line bg-white text-muted";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase ${className}`}
    >
      {value}
    </span>
  );
}
