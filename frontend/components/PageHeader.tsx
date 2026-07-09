export function PageHeader({
  eyebrow,
  title,
  body
}: {
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <section className="mb-7 overflow-hidden rounded-lg border border-line bg-surface/75 p-5 shadow-soft md:p-7">
      <div className="flex flex-wrap items-center gap-3">
        <div className="kicker">{eyebrow}</div>
        <div className="h-px min-w-16 flex-1 bg-line" />
        <div className="rounded-full border border-line bg-field px-3 py-1 text-[0.68rem] font-semibold uppercase text-muted">
          Evidence traceable
        </div>
      </div>
      <h1 className="mt-4 max-w-4xl font-display text-3xl font-bold leading-tight md:text-5xl">{title}</h1>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-muted md:text-base">{body}</p>
    </section>
  );
}
