export function formatTimestamp(value) {
  if (!value) {
    return "--";
  }

  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

export function classNames(...values) {
  return values.filter(Boolean).join(" ");
}

export const severityColors = {
  Critical: "text-red-200 border-red-400/30 bg-red-500/12",
  High: "text-orange-200 border-orange-400/30 bg-orange-500/12",
  Medium: "text-yellow-200 border-yellow-300/30 bg-yellow-500/12",
  Low: "text-blue-200 border-blue-400/30 bg-blue-500/12",
  Informational: "text-slate-200 border-slate-400/20 bg-slate-500/10",
  Unknown: "text-slate-200 border-white/10 bg-white/5"
};

export const severityRank = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Low: 1,
  Informational: 0,
  Unknown: -1
};

export function getSeverityRank(value) {
  return severityRank[value] ?? -1;
}

export function summarizeActivity(item) {
  const role = item.role || item.action || "System";
  const prefixMap = {
    SystemMessage: "SYSTEM",
    AIMessage: "AI",
    HumanMessage: "HUMAN",
    ToolMessage: "PLAYBOOK",
    AuditLog: "SYSTEM",
    ResponseJob: "RESPONSE"
  };
  const prefix = prefixMap[role] || String(role).replace(/Message$/, "").toUpperCase();
  const body = item.content || item.details?.summary || item.action || item.node || "Updated record";
  return `[${prefix}] ${body}`;
}

export function groupByDay(items) {
  const groups = [];
  let lastDay = "";
  for (const item of items) {
    const day = String(item.ts || "").slice(0, 10) || "Unknown";
    if (day !== lastDay) {
      groups.push({ type: "header", label: day });
      lastDay = day;
    }
    groups.push({ type: "item", item });
  }
  return groups;
}
