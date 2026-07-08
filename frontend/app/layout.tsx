import type { Metadata } from "next";
import Link from "next/link";
import { FileSearch, GitCompareArrows, LayoutDashboard, MessageSquareQuote, ScanSearch, ShieldAlert } from "lucide-react";

import "./globals.css";

export const metadata: Metadata = {
  title: "BidGuard AI",
  description: "Evidence-first tender and contract document review agent"
};

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileSearch },
  { href: "/qa", label: "Q&A", icon: MessageSquareQuote },
  { href: "/risk", label: "Risk Review", icon: ShieldAlert },
  { href: "/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/agent-trace", label: "Agent Trace", icon: ScanSearch }
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-line bg-field/95">
            <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
              <Link href="/" className="group flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center border border-ink bg-signal font-black text-ink">
                  BG
                </div>
                <div>
                  <div className="text-xl font-black tracking-tight">BidGuard AI</div>
                  <div className="text-xs font-semibold uppercase tracking-[0.22em] text-steel">
                    Evidence-first tender review
                  </div>
                </div>
              </Link>
              <nav className="flex flex-wrap gap-2">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="flex items-center gap-2 border border-line bg-white/70 px-3 py-2 text-sm font-bold hover:border-ink hover:bg-signal"
                    >
                      <Icon size={16} aria-hidden />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
