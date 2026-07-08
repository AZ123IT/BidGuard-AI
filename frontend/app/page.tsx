"use client";

import { useEffect, useState } from "react";
import { Activity, FileText, ShieldAlert } from "lucide-react";

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
      <section className="mt-6">
        <h2 className="mb-3 text-lg font-black">Recent Agent Runs</h2>
        {!data?.recent_agent_runs.length ? (
          <EmptyState title="No trace yet" body={`Backend target: ${api.apiBase}. Run Q&A or a review to create a tool trace.`} />
        ) : (
          <div className="grid gap-3">
            {data.recent_agent_runs.map((run) => (
              <article key={run.id} className="panel p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="font-black">{run.objective}</div>
                  <div className="text-xs font-bold uppercase tracking-[0.16em] text-steel">{run.latency_ms} ms</div>
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
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <div className="text-xs font-black uppercase tracking-[0.22em] text-steel">{label}</div>
        <Icon size={20} />
      </div>
      <div className="mt-4 text-5xl font-black">{value}</div>
    </div>
  );
}
