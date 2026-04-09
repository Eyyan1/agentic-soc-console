import { ArrowDownWideNarrow, ArrowUpWideNarrow } from "lucide-react";
import { classNames, formatTimestamp, getSeverityRank } from "../lib/utils";
import { StatusBadge } from "./StatusBadge";

export function AlertTable({
  alerts,
  sortKey,
  sortDirection,
  onSort,
  onOpenAlert,
  compact = false,
}) {
  function renderSortIcon(key) {
    if (sortKey !== key) return <ArrowDownWideNarrow className="h-3.5 w-3.5 text-slate-600" />;
    return sortDirection === "asc"
      ? <ArrowUpWideNarrow className="h-3.5 w-3.5 text-cyan-300" />
      : <ArrowDownWideNarrow className="h-3.5 w-3.5 text-cyan-300" />;
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/[0.03]">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left">
          <thead className="bg-black/30 text-xs uppercase tracking-[0.18em] text-slate-500">
            <tr>
              {[
                ["severity", "Severity"],
                ["title", "Alert"],
                ["rule_id", "Rule"],
                ["target", "Target"],
                ["status", "Status"],
                ["first_seen_time", "First Seen"],
              ].map(([key, label]) => (
                <th key={key} className="px-4 py-3 font-medium">
                  <button type="button" onClick={() => onSort(key)} className="inline-flex items-center gap-2">
                    <span>{label}</span>
                    {renderSortIcon(key)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {alerts.map((alert) => (
              <tr
                key={alert.rowid}
                className={classNames(
                  "cursor-pointer transition hover:bg-white/[0.04]",
                  alert.severity === "Critical" ? "bg-red-500/[0.06]" : "",
                  alert.status === "New" ? "animate-pulse" : ""
                )}
                onClick={() => onOpenAlert(alert.rowid, alert)}
              >
                <td className="px-4 py-3 align-top">
                  <StatusBadge value={alert.severity} />
                </td>
                <td className="max-w-[28rem] px-4 py-3 align-top">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 font-medium text-white">
                      <span>{alert.title}</span>
                      <span className="text-xs text-slate-600">Open</span>
                    </div>
                    {!compact ? <div className="mt-1 line-clamp-2 text-sm text-slate-400">{alert.summary || "No summary available."}</div> : null}
                  </div>
                </td>
                <td className="px-4 py-3 align-top text-sm text-slate-300">{alert.rule_id}</td>
                <td className="px-4 py-3 align-top text-sm text-slate-300">{alert.target || "unknown"}</td>
                <td className="px-4 py-3 align-top"><StatusBadge value={alert.status} /></td>
                <td className="px-4 py-3 align-top text-sm text-slate-400">{formatTimestamp(alert.first_seen_time)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function sortAlerts(alerts, sortKey, sortDirection) {
  const sorted = [...alerts].sort((left, right) => {
    if (sortKey === "severity") {
      return getSeverityRank(left.severity) - getSeverityRank(right.severity);
    }
    const a = String(left[sortKey] || "");
    const b = String(right[sortKey] || "");
    return a.localeCompare(b);
  });
  return sortDirection === "asc" ? sorted : sorted.reverse();
}
