import { useState } from "react";
import { DetailDrawer } from "../components/DetailDrawer";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatTimestamp } from "../lib/utils";

export function PlaybooksPage({ playbooks, loadPlaybookDetail }) {
  const [selectedPlaybook, setSelectedPlaybook] = useState(null);

  async function openPlaybook(rowid) {
    const detail = await loadPlaybookDetail(rowid);
    setSelectedPlaybook(detail);
  }

  return (
    <>
      <SectionCard
        title="Playbooks"
        subtitle="Execution state for local agentic runs and queued automation."
      >
        <div className="space-y-4">
          {playbooks.map((playbook) => (
            <button key={playbook.rowid} type="button" onClick={() => openPlaybook(playbook.rowid)} className="w-full rounded-2xl border border-white/10 bg-black/20 p-4 text-left transition hover:border-cyan-400/20 hover:bg-white/[0.03]">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-lg font-medium text-white">{playbook.name}</h3>
                    <StatusBadge value={playbook.status} />
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{playbook.remark || "No execution remark available."}</p>
                </div>
                <div className="text-xs text-slate-500">Run ID: {playbook.rowid}</div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Started</div>
                  <div className="mt-2 text-sm text-white">{formatTimestamp(playbook.started_at)}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Finished</div>
                  <div className="mt-2 text-sm text-white">{formatTimestamp(playbook.finished_at)}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Target</div>
                  <div className="mt-2 break-all text-sm text-white">{playbook.target_id || playbook.source_rowid}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </SectionCard>

      <DetailDrawer
        open={Boolean(selectedPlaybook)}
        title={selectedPlaybook?.name || "Playbook detail"}
        subtitle={selectedPlaybook?.rowid}
        onClose={() => setSelectedPlaybook(null)}
      >
        {selectedPlaybook ? (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={selectedPlaybook.status} />
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Execution Remark</div>
              <div className="mt-2 text-sm text-white">{selectedPlaybook.remark || "No execution remark available."}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Step Trace</div>
              <div className="mt-3 space-y-3">
                {(selectedPlaybook.step_trace || []).map((step) => (
                  <div key={`${step.step}-${step.node}`} className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm text-white">{step.node}</div>
                      <div className="text-xs text-slate-500">{formatTimestamp(step.ts)}</div>
                    </div>
                    <div className="mt-2 text-xs text-slate-400">{step.role}</div>
                    <div className="mt-2 text-sm text-slate-200">{step.content || "No content."}</div>
                    {step.output ? <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-slate-300">{JSON.stringify(step.output, null, 2)}</pre> : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </DetailDrawer>
    </>
  );
}
