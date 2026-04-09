import { Bot, Cpu, PlaySquare, User, Wrench } from "lucide-react";
import { formatTimestamp, groupByDay, summarizeActivity } from "../lib/utils";
import { StatusBadge } from "./StatusBadge";

function roleIcon(role) {
  if (role === "SystemMessage") return Cpu;
  if (role === "AIMessage") return Bot;
  if (role === "HumanMessage") return User;
  if (role === "ToolMessage") return PlaySquare;
  if (role === "AuditLog") return Cpu;
  if (role === "ResponseJob") return Wrench;
  return Wrench;
}

export function ActivityFeed({ items, compact = false }) {
  const grouped = groupByDay(items);

  return (
    <div className="space-y-4">
      {grouped.map((entry, index) => {
        if (entry.type === "header") {
          return (
            <div key={`${entry.label}-${index}`} className="sticky top-0 z-[1] bg-transparent text-xs uppercase tracking-[0.24em] text-slate-500">
              {entry.label}
            </div>
          );
        }

        const item = entry.item;
        const Icon = roleIcon(item.role || item.action);
        return (
          <div key={item.rowid} className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-2xl border border-white/10 bg-white/[0.04] p-2">
                <Icon className="h-4 w-4 text-slate-200" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge value={item.role || item.action} />
                  <span className="text-xs text-slate-500">{formatTimestamp(item.ts)}</span>
                </div>
                <div className="mt-2 text-sm leading-6 text-slate-200">{summarizeActivity(item)}</div>
                {!compact && item.node ? <div className="mt-2 text-xs text-slate-500">Node: {item.node}</div> : null}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
