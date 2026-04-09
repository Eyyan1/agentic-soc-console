import { classNames } from "../lib/utils";

const tones = {
  Critical: "border-red-400/30 bg-red-400/15 text-red-200",
  High: "border-orange-400/30 bg-orange-400/15 text-orange-200",
  Medium: "border-amber-400/30 bg-amber-400/15 text-amber-200",
  Low: "border-sky-400/30 bg-sky-400/15 text-sky-200",
  New: "border-sky-400/30 bg-sky-400/15 text-sky-200",
  Triage: "border-cyan-400/30 bg-cyan-400/15 text-cyan-200",
  Investigating: "border-violet-400/30 bg-violet-400/15 text-violet-200",
  "In Progress": "border-violet-400/30 bg-violet-400/15 text-violet-200",
  Contained: "border-amber-400/30 bg-amber-400/15 text-amber-200",
  Running: "border-sky-400/30 bg-sky-400/15 text-sky-200",
  Success: "border-emerald-400/30 bg-emerald-400/15 text-emerald-200",
  Failed: "border-red-400/30 bg-red-400/15 text-red-200",
  Resolved: "border-emerald-400/30 bg-emerald-400/15 text-emerald-200",
  Archived: "border-slate-400/30 bg-slate-400/15 text-slate-200",
  Closed: "border-slate-400/30 bg-slate-400/15 text-slate-200"
};

export function StatusBadge({ value }) {
  return (
    <span
      className={classNames(
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium",
        tones[value] || "border-white/15 bg-white/5 text-slate-200"
      )}
    >
      {value || "Unknown"}
    </span>
  );
}
