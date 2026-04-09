import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatTimestamp } from "../lib/utils";

export function ResponseJobsPage({ responseJobs }) {
  return (
    <SectionCard
      title="Response Jobs"
      subtitle="Explicit execution history for local-dev response actions such as assignment, ticketing, containment, and playbook queueing."
    >
      <div className="space-y-3">
        {(responseJobs || []).length ? (responseJobs || []).map((item) => (
          <div key={item.rowid} className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge value={item.action} />
                  <StatusBadge value={item.status} />
                  <StatusBadge value={item.target_type} />
                </div>
                <div className="text-sm text-white">{item.summary}</div>
                <div className="text-xs text-slate-500">Target: {item.target_rowid}</div>
              </div>
              <div className="text-xs text-slate-500">
                <div>Started {formatTimestamp(item.started_at)}</div>
                <div className="mt-1">Finished {formatTimestamp(item.finished_at)}</div>
              </div>
            </div>
          </div>
        )) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-black/20 p-6 text-sm text-slate-400">
            No response jobs yet. Run an action from an alert or case to see execution history here.
          </div>
        )}
      </div>
    </SectionCard>
  );
}
