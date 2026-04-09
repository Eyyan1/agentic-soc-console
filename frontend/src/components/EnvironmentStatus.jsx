import { Activity, BadgeCheck, Clock3, DatabaseZap, Server, ShieldCheck } from "lucide-react";
import { formatTimestamp } from "../lib/utils";
import { StatusBadge } from "./StatusBadge";

function StatusPill({ icon: Icon, label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
      <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-500">
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </div>
      <div className="mt-2 text-sm text-white">{value}</div>
    </div>
  );
}

export function EnvironmentStatus({ backendReachable, tokenValid, mode, lastRefreshAt, counts }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[repeat(4,minmax(0,1fr))_1.2fr]">
      <StatusPill icon={Server} label="Backend" value={backendReachable ? "Reachable" : "Unavailable"} />
      <StatusPill icon={ShieldCheck} label="Token" value={tokenValid ? "Valid" : "Not validated"} />
      <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-500">
          <DatabaseZap className="h-4 w-4" />
          <span>Data Mode</span>
        </div>
        <div className="mt-2">
          <StatusBadge value={mode === "live" ? "Success" : mode === "fallback" ? "Running" : "New"} />
          <div className="mt-2 text-sm text-white">{mode}</div>
        </div>
      </div>
      <StatusPill icon={Clock3} label="Last Refresh" value={formatTimestamp(lastRefreshAt)} />
      <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-500">
          <Activity className="h-4 w-4" />
          <span>Totals</span>
        </div>
        <div className="mt-3 grid grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-slate-500">Alerts</div>
            <div className="mt-1 text-white">{counts.alerts}</div>
          </div>
          <div>
            <div className="text-slate-500">Cases</div>
            <div className="mt-1 text-white">{counts.cases}</div>
          </div>
          <div>
            <div className="text-slate-500">Playbooks</div>
            <div className="mt-1 text-white">{counts.playbooks}</div>
          </div>
          <div>
            <div className="text-slate-500">Messages</div>
            <div className="mt-1 text-white">{counts.messages}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
