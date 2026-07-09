"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, ArrowRight, Database, FileText, SearchCheck, ShieldAlert } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { PageHeader } from "@/components/PageHeader";
import { api, type AgentRun } from "@/lib/api";

type DashboardData = {
  document_count: number;
  risk_finding_count: number;
  recent_agent_runs: AgentRun[];
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div>
      <PageHeader
        eyebrow="Portfolio MVP"
        title="Document review that shows its work."
        body="Upload public tender or contract PDFs, retrieve page-level evidence, run deterministic risk checks, compare extracted clauses, and inspect the agent tool trace."
      />
      <ErrorBanner message={error} />
      <div className="grid gap-4 md:grid-cols-3">
        <Metric icon={FileText} label="Documents" value={data?.document_count ?? 0} />
        <Metric icon={ShieldAlert} label="Risk Findings" value={data?.risk_finding_count ?? 0} />
        <Metric icon={Activity} label="Agent Runs" value={data?.recent_agent_runs.length ?? 0} />
      </div>

      <section className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel-strong p-5">
          <div className="kicker">Recommended flow</div>
          <h2 className="mt-2 font-display text-3xl font-bold">Run a review in four moves.</h2>
          <div className="mt-5 grid gap-3">
            <FlowLink href="/documents" icon={FileText} title="Upload source material" body="Parse PDFs and create page-aware chunks." />
            <FlowLink href="/qa" icon={SearchCheck} title="Ask with citations" body="Inspect confidence, retrieval method, and evidence snippets." />
            <FlowLink href="/risk" icon={ShieldAlert} title="Run deterministic checks" body="Surface payment, acceptance, liability, scoring, and dispute risks." />
            <FlowLink href="/agent-trace" icon={Database} title="Audit the trace" body="See exactly which tool path the agent used." />
          </div>
        </div>

        <div className="panel p-5">
          <div className="kicker">System posture</div>
          <div className="mt-4 grid gap-3">
            <Posture label="Evidence gate" value="LLM skipped when support is weak" />
            <Posture label="Local mode" value="SQLite + deterministic providers" />
            <Posture label="Vector path" value="PostgreSQL pgvector smoke-ready" />
          </div>
        </div>
      </section>

      <section className="mt-6">
        <h2 className="mb-3 font-display text-2xl font-bold">Recent Agent Runs</h2>
        {!data?.recent_agent_runs.length ? (
          <EmptyState title="No trace yet" body={`Backend target: ${api.apiBase}. Run Q&A or a review to create a tool trace.`} />
        ) : (
          <div className="grid gap-3">
            {data.recent_agent_runs.map((run) => (
              <article key={run.id} className="panel p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="font-semibold">{run.objective}</div>
                  <div className="text-xs font-bold uppercase text-steel">{run.latency_ms} ms</div>
                </div>
                <div className="mt-2 text-sm text-steel">
                  {run.tool_calls.map((call) => call.tool_name).join(" -> ") || "No tool calls"}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value
}: {
  icon: React.ComponentType<{ size?: number }>;
  label: string;
  value: number;
}) {
  return (
    <div className="metric-card p-5">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold uppercase text-muted">{label}</div>
        <div className="grid h-10 w-10 place-items-center rounded-full border border-line bg-field">
          <Icon size={19} />
        </div>
      </div>
      <div className="mt-4 font-display text-5xl font-bold">{value}</div>
    </div>
  );
}

function FlowLink({
  href,
  icon: Icon,
  title,
  body
}: {
  href: string;
  icon: React.ComponentType<{ size?: number }>;
  title: string;
  body: string;
}) {
  return (
    <Link href={href} className="group flex items-center gap-4 rounded-lg border border-line bg-surface p-3 hover:border-accent hover:bg-field">
      <div className="grid h-11 w-11 flex-none place-items-center rounded-lg border border-line bg-field group-hover:bg-accent group-hover:text-white">
        <Icon size={19} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{title}</div>
        <div className="mt-1 text-sm leading-5 text-muted">{body}</div>
      </div>
      <ArrowRight className="text-muted group-hover:text-ink" size={18} />
    </Link>
  );
}

function Posture({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="text-xs font-semibold uppercase text-muted">{label}</div>
      <div className="mt-1 text-sm font-bold">{value}</div>
    </div>
  );
}
