import { NavLink } from "react-router-dom";
import { Activity, Bot, FileText, ListChecks, MonitorSmartphone, Radar, Shield, Siren, Workflow } from "lucide-react";
import { classNames } from "../lib/utils";

const items = [
  { to: "/", label: "Alerts", icon: Siren },
  { to: "/overview", label: "Overview", icon: Activity },
  { to: "/assets", label: "Assets", icon: MonitorSmartphone },
  { to: "/campaigns", label: "Campaigns", icon: Radar },
  { to: "/cases", label: "Cases", icon: FileText },
  { to: "/playbooks", label: "Playbooks", icon: Bot },
  { to: "/response-jobs", label: "Response Jobs", icon: ListChecks },
  { to: "/activity", label: "Activity", icon: Workflow }
];

export function Sidebar({ mode }) {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-white/10 bg-black/20 p-6 lg:flex lg:flex-col">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
          <Shield className="h-6 w-6 text-signal-cyan" />
        </div>
        <div>
          <div className="text-lg font-semibold text-white">Agentic SOC</div>
          <div className="text-sm text-slate-400">Local Operations Console</div>
        </div>
      </div>

      <nav className="mt-8 space-y-2">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              classNames(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition-colors",
                isActive
                  ? "border border-cyan-400/20 bg-cyan-400/10 text-cyan-100"
                  : "border border-white/5 bg-white/[0.03] text-slate-300 hover:bg-white/[0.05]"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-4">
        <div className="text-sm font-medium text-emerald-200">Mode: {mode}</div>
        <p className="mt-2 text-sm text-emerald-100/80">
          `live` uses the local-dev SOC read APIs. `fallback` keeps the UI operational with seeded data when those endpoints are unavailable.
        </p>
      </div>
    </aside>
  );
}
