"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FileSearch,
  GitCompareArrows,
  LayoutDashboard,
  MessageSquareQuote,
  ScanSearch,
  ShieldAlert
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileSearch },
  { href: "/qa", label: "Q&A", icon: MessageSquareQuote },
  { href: "/risk", label: "Risk Review", icon: ShieldAlert },
  { href: "/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/agent-trace", label: "Agent Trace", icon: ScanSearch }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/80 shadow-rule backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <Link href="/" className="group flex items-center gap-3" aria-label="BidGuard AI dashboard">
            <div className="brand-mark">BG</div>
            <div>
              <div className="font-display text-2xl font-bold">BidGuard AI</div>
              <div className="text-[0.68rem] font-semibold uppercase text-muted">
                Evidence-first review console
              </div>
            </div>
          </Link>

          <nav className="flex gap-2 overflow-x-auto pb-1 lg:flex-wrap lg:justify-end lg:overflow-visible lg:pb-0">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={`nav-link ${isActive ? "nav-link-active" : ""}`}
                >
                  <Icon size={16} aria-hidden />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="border-t border-line bg-field/70 text-muted">
          <div className="mx-auto flex max-w-7xl flex-wrap gap-x-6 gap-y-2 px-4 py-2 text-[0.68rem] font-semibold uppercase">
            <span>Grounded answers only</span>
            <span className="text-accent">Cited chunks visible</span>
            <span>SQLite local / pgvector ready</span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-7 md:py-10">{children}</main>
    </div>
  );
}
