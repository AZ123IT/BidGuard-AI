export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="panel border-dashed p-6">
      <div className="text-sm font-black uppercase tracking-[0.18em] text-steel">{title}</div>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">{body}</p>
    </div>
  );
}
