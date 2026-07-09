export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }
  return (
    <div className="mb-4 rounded-lg border border-oxide bg-[#fff4f0] p-3 text-sm font-semibold text-oxide shadow-rule">
      {message}
    </div>
  );
}
