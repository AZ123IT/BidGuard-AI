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
    <section className="mb-6 border-b border-line pb-5">
      <div className="text-xs font-black uppercase tracking-[0.28em] text-moss">{eyebrow}</div>
      <h1 className="mt-2 max-w-4xl text-3xl font-black tracking-tight md:text-5xl">{title}</h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-steel md:text-base">{body}</p>
    </section>
  );
}
