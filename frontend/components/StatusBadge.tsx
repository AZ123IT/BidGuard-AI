export function StatusBadge({ value }: { value: string }) {
  const className =
    value === "high"
      ? "border-oxide bg-[#fff4f0] text-oxide"
      : value === "medium"
        ? "border-[#8b6b00] bg-[#fff9dc] text-[#6a5100]"
        : value === "low"
          ? "border-moss bg-[#eef8ed] text-moss"
          : "border-line bg-white text-steel";

  return (
    <span className={`inline-flex items-center border px-2 py-1 text-xs font-black uppercase tracking-[0.14em] ${className}`}>
      {value}
    </span>
  );
}
