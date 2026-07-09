export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="panel border-dashed p-6">
      <div className="flex items-start gap-4">
        <div className="mt-1 h-3 w-3 rounded-full bg-accent shadow-[0_0_0_6px_rgba(10,132,255,0.14)]" />
        <div>
          <div className="text-sm font-semibold uppercase text-muted">{title}</div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{body}</p>
        </div>
      </div>
    </div>
  );
}
