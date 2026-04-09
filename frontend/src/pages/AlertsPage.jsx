import { useDeferredValue, useMemo, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { AlertTable, sortAlerts } from "../components/AlertTable";
import { DetailDrawer } from "../components/DetailDrawer";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatTimestamp } from "../lib/utils";

export function AlertsPage({ alerts, loadAlertDetail, runResponseAction }) {
  const [query, setQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("active");
  const [sortKey, setSortKey] = useState("first_seen_time");
  const [sortDirection, setSortDirection] = useState("desc");
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [runningAction, setRunningAction] = useState("");
  const [showRawEvent, setShowRawEvent] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const deferredQuery = useDeferredValue(query);

  const filteredAlerts = useMemo(() => {
    const value = deferredQuery.trim().toLowerCase();
    const nextAlerts = alerts.filter((alert) => {
      const matchesSeverity = severityFilter === "all" || alert.severity === severityFilter;
      const matchesStatus = statusFilter === "all"
        || (statusFilter === "active" && !["Resolved", "Archived", "Deleted"].includes(String(alert.status || "")))
        || alert.status === statusFilter;
      const matchesQuery = !value || [alert.title, alert.rule_id, alert.rule_name, alert.target, alert.sender, alert.summary, alert.rowid]
        .join(" ")
        .toLowerCase()
        .includes(value);
      return matchesSeverity && matchesStatus && matchesQuery;
    });
    return sortAlerts(nextAlerts, sortKey, sortDirection);
  }, [alerts, deferredQuery, severityFilter, sortDirection, sortKey, statusFilter]);

  async function openAlertDetail(rowid, alertPreview) {
    setActionMessage("");
    setLoadingDetail(true);
    try {
      const detail = await loadAlertDetail(rowid, alertPreview);
      setSelectedAlert(detail);
      setShowRawEvent(false);
    } finally {
      setLoadingDetail(false);
    }
  }

  async function handleAction(action) {
    if (!selectedAlert) return;
    setRunningAction(action);
    setActionMessage("");
    try {
      const result = await runResponseAction({
        action,
        target_type: "alert",
        target_rowid: selectedAlert.rowid,
      });
      const detail = await loadAlertDetail(selectedAlert.rowid, selectedAlert);
      setSelectedAlert(detail);
      setActionMessage(result?.audit_entry?.content || "Action completed in local-dev mode.");
    } finally {
      setRunningAction("");
    }
  }

  function handleSort(nextKey) {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection(nextKey === "severity" ? "desc" : "asc");
  }

  return (
    <>
      <SectionCard
        title="Alert Queue"
        subtitle="Primary SOC workspace with live search, severity filtering, status filtering, and analyst detail drawers."
        actions={
          <div className="flex flex-col gap-3 xl:flex-row">
            <label className="relative block min-w-80">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search alerts, targets, rules, senders..."
                className="h-11 w-full rounded-2xl border border-white/10 bg-ink-900/80 pl-10 pr-4 text-sm text-white outline-none focus:border-cyan-400/40"
              />
            </label>
            <select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value)}
              className="h-11 rounded-2xl border border-white/10 bg-ink-900/80 px-4 text-sm text-white outline-none focus:border-cyan-400/40"
            >
              <option value="all">All severities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
              <option value="Informational">Informational</option>
            </select>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="h-11 rounded-2xl border border-white/10 bg-ink-900/80 px-4 text-sm text-white outline-none focus:border-cyan-400/40"
            >
              <option value="active">Active queue</option>
              <option value="all">All statuses</option>
              <option value="New">New</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
              <option value="Archived">Archived</option>
            </select>
          </div>
        }
      >
        <AlertTable
          alerts={filteredAlerts}
          sortKey={sortKey}
          sortDirection={sortDirection}
          onSort={handleSort}
          onOpenAlert={openAlertDetail}
        />
      </SectionCard>

      <DetailDrawer
        open={Boolean(selectedAlert)}
        title={selectedAlert?.title || "Alert detail"}
        subtitle={selectedAlert?.rowid}
        onClose={() => setSelectedAlert(null)}
      >
        {loadingDetail && !selectedAlert ? <div className="text-sm text-slate-400">Loading alert detail...</div> : null}
        {selectedAlert ? (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={selectedAlert.severity} />
              <StatusBadge value={selectedAlert.status} />
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              {[
                ["Rule", selectedAlert.rule_name || selectedAlert.rule_id || "--"],
                ["Source", selectedAlert.product_name || selectedAlert.product_category || "--"],
                ["Target", selectedAlert.target || "--"],
                ["First Seen", formatTimestamp(selectedAlert.first_seen_time)],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
                  <div className="mt-2 text-sm text-white">{value}</div>
                </div>
              ))}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Summary</div>
                <div className="mt-2 text-sm leading-6 text-slate-200">{selectedAlert.summary || "No summary available."}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Linked Case</div>
                <div className="mt-2 text-sm text-white">{selectedAlert.linked_case?.title || "No linked case"}</div>
                <div className="mt-1 text-xs text-slate-500">{selectedAlert.linked_case?.rowid || "--"}</div>
                <div className="mt-3 text-xs text-slate-500">Alert status: {selectedAlert.status || "Unknown"}</div>
              </div>
            </div>

            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-cyan-100/70">Suggested Resolution</div>
                  <div className="mt-2 text-lg font-medium text-white">
                    {selectedAlert.resolution_guidance?.headline || "No resolution guidance available."}
                  </div>
                  <div className="mt-2 text-sm leading-6 text-cyan-50/85">
                    {selectedAlert.resolution_guidance?.recommendation || "Review the investigation outcome before resolving this alert."}
                  </div>
                  {selectedAlert.resolution_guidance?.playbook ? (
                    <div className="mt-2 text-xs text-cyan-100/70">
                      Latest playbook: {selectedAlert.resolution_guidance.playbook.name} | {selectedAlert.resolution_guidance.playbook.status}
                    </div>
                  ) : null}
                </div>
                {selectedAlert.resolution_guidance?.next_action ? (
                  <button
                    type="button"
                    onClick={() => handleAction(selectedAlert.resolution_guidance.next_action)}
                    className="rounded-2xl border border-cyan-300/30 bg-white/10 px-4 py-3 text-sm text-cyan-50 transition hover:bg-white/15"
                  >
                    {runningAction === selectedAlert.resolution_guidance.next_action ? "Running..." : "Apply Suggested Action"}
                  </button>
                ) : null}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Threat Analysis</div>
              <div className="mt-4 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-1">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Risk Score</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{selectedAlert.threat_analysis?.risk_score ?? "--"}</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Confidence</div>
                    <div className="mt-2 text-2xl font-semibold text-white">
                      {selectedAlert.threat_analysis?.confidence_score != null
                        ? Number(selectedAlert.threat_analysis.confidence_score).toFixed(2)
                        : "--"}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Campaign Links</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{(selectedAlert.linked_campaigns || []).length}</div>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Explanation</div>
                    <div className="mt-2 text-sm leading-6 text-slate-200">
                      {selectedAlert.threat_analysis?.explanation || "No threat explanation available."}
                    </div>
                  </div>
                  {(selectedAlert.threat_analysis?.action_plan || []).length ? (
                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Recommended Action Path</div>
                      <div className="mt-2 space-y-2 text-sm text-slate-200">
                        {(selectedAlert.threat_analysis?.action_plan || []).map((step, index) => (
                          <div key={`${index + 1}-${step}`} className="flex items-start gap-3">
                            <div className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-[10px] text-cyan-100">
                              {index + 1}
                            </div>
                            <div className="leading-6">{step}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">MITRE ATT&CK</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(selectedAlert.threat_analysis?.mitre_attack || []).length
                        ? (selectedAlert.threat_analysis?.mitre_attack || []).map((item) => (
                          <StatusBadge key={`${item.id}-${item.technique}`} value={`${item.id} ${item.technique}`} />
                        ))
                        : <div className="text-sm text-slate-400">No ATT&CK mapping available.</div>}
                    </div>
                  </div>
                  {(selectedAlert.linked_campaigns || []).length ? (
                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Linked Campaigns</div>
                      <div className="mt-2 space-y-2">
                        {(selectedAlert.linked_campaigns || []).map((campaign) => (
                          <div key={campaign.rowid} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                            <div className="text-sm text-white">{campaign.name}</div>
                            <div className="mt-1 text-xs text-slate-500">
                              {campaign.alert_count} alerts | Risk {campaign.risk_score}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Artifacts</div>
              {(selectedAlert.artifacts || []).length ? (
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  {(selectedAlert.artifacts || []).map((item) => (
                    <div key={item.rowid || `${item.type}-${item.value}`} className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                      <div className="text-xs text-slate-500">{item.role || item.type}</div>
                      <div className="mt-2 break-all text-sm text-white">{item.value || item.name || "--"}</div>
                      <div className="mt-1 text-xs text-slate-500">{item.type || "artifact"}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-3 text-sm text-slate-400">No artifacts available for this alert.</div>
              )}
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Enrichment</div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {Object.entries(selectedAlert.enrichment_context || {}).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{key}</div>
                    <div className="mt-2 space-y-1 text-xs text-slate-300">
                      {Object.entries(value || {}).map(([innerKey, innerValue]) => (
                        <div key={innerKey} className="flex items-start justify-between gap-3">
                          <span className="uppercase tracking-[0.12em] text-slate-500">{innerKey}</span>
                          <span className="text-right text-slate-200">{String(innerValue)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Actions</div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {(selectedAlert.recommended_actions || []).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleAction(item.id)}
                    className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-left transition hover:bg-cyan-400/20"
                  >
                    <div className="text-sm font-medium text-cyan-100">{runningAction === item.id ? "Running..." : item.label}</div>
                    <div className="mt-2 text-xs leading-5 text-cyan-50/80">{item.description}</div>
                  </button>
                ))}
              </div>
              {actionMessage ? (
                <div className="mt-3 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">
                  {actionMessage}
                </div>
              ) : null}
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Response Jobs</div>
              <div className="mt-3 space-y-3">
                {(selectedAlert.response_jobs || []).length ? (selectedAlert.response_jobs || []).map((item) => (
                  <div key={item.rowid} className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="flex items-center justify-between gap-3">
                      <StatusBadge value={item.action} />
                      <StatusBadge value={item.status} />
                    </div>
                    <div className="mt-2 text-sm text-slate-200">{item.summary}</div>
                    <div className="mt-2 text-xs text-slate-500">
                      Started {formatTimestamp(item.started_at)} | Finished {formatTimestamp(item.finished_at)}
                    </div>
                  </div>
                )) : <div className="text-sm text-slate-400">No response jobs recorded for this alert yet.</div>}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <button
                type="button"
                onClick={() => setShowRawEvent((current) => !current)}
                className="flex w-full items-center justify-between text-left"
              >
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Raw Event</div>
                <ChevronDown className={`h-4 w-4 text-slate-500 transition ${showRawEvent ? "rotate-180" : ""}`} />
              </button>
              {showRawEvent ? (
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-slate-300">{JSON.stringify(selectedAlert.raw_event || {}, null, 2)}</pre>
              ) : (
                <div className="mt-3 text-sm text-slate-400">Expand to inspect the raw JSON event payload.</div>
              )}
            </div>
          </div>
        ) : null}
      </DetailDrawer>
    </>
  );
}
