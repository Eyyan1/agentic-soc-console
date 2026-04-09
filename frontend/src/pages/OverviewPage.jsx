import { useDeferredValue, useMemo, useState } from "react";
import { AlertTriangle, Bot, FileText, Search, Siren } from "lucide-react";
import { SectionCard } from "../components/SectionCard";
import { ActivityFeed } from "../components/ActivityFeed";
import { AlertTable, sortAlerts } from "../components/AlertTable";
import { BarChart, LineChart, SeverityPieChart } from "../components/Charts";
import { StatCard } from "../components/StatCard";

function buildTrendData(alerts) {
  const counts = new Map();
  alerts.forEach((alert) => {
    const bucket = String(alert.first_seen_time || "").slice(0, 10) || "unknown";
    counts.set(bucket, (counts.get(bucket) || 0) + 1);
  });
  return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b)).slice(-6).map(([day, count]) => ({
    day: day.slice(5),
    count
  }));
}

function buildTopRules(alerts) {
  const counts = new Map();
  alerts.forEach((alert) => {
    const key = alert.rule_id || "unknown";
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return [...counts.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count).slice(0, 5);
}

export function OverviewPage({ snapshot, loadAlertDetail }) {
  const stats = snapshot.overview?.stats || {};
  const metrics = snapshot.overview?.metrics || {};
  const activity = snapshot.overview?.recent_activity || snapshot.messages || [];
  const [query, setQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [sortKey, setSortKey] = useState("first_seen_time");
  const [sortDirection, setSortDirection] = useState("desc");
  const deferredQuery = useDeferredValue(query);

  const filteredAlerts = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    const base = (snapshot.alerts || []).filter((alert) => {
      const matchesSeverity = severityFilter === "all" || alert.severity === severityFilter;
      const matchesQuery = !q || [alert.title, alert.rule_id, alert.target, alert.summary, alert.sender].join(" ").toLowerCase().includes(q);
      return matchesSeverity && matchesQuery;
    });
    return sortAlerts(base, sortKey, sortDirection);
  }, [deferredQuery, severityFilter, snapshot.alerts, sortDirection, sortKey]);

  const trendData = useMemo(() => buildTrendData(snapshot.alerts || []), [snapshot.alerts]);
  const topRules = useMemo(() => buildTopRules(snapshot.alerts || []), [snapshot.alerts]);

  function handleSort(nextKey) {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection(nextKey === "severity" ? "desc" : "asc");
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Critical Alerts" value={stats.critical_alerts || 0} hint="Immediate analyst attention" icon={AlertTriangle} tone="critical" />
        <StatCard label="Open Cases" value={stats.open_cases || 0} hint="Active investigations" icon={FileText} tone="neutral" />
        <StatCard label="Running Playbooks" value={stats.running_playbooks || 0} hint="Automation currently in flight" icon={Bot} tone="info" />
        <StatCard label="Total Alerts" value={stats.alerts || 0} hint="Live alert queue volume" icon={Siren} tone="warning" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.7fr_0.9fr]">
        <SectionCard
          title="Alert Workbench"
          subtitle="Primary analyst surface with sorting, filtering, search, and urgency cues."
          actions={
            <div className="flex flex-col gap-3 xl:flex-row">
              <label className="relative block min-w-72">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search alerts, targets, rules, summaries..."
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
            </div>
          }
        >
          <AlertTable
            alerts={filteredAlerts}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onSort={handleSort}
            onOpenAlert={loadAlertDetail ? async (rowid) => { await loadAlertDetail(rowid); } : () => {}}
          />
        </SectionCard>

        <div className="space-y-6">
          <SectionCard title="Severity Distribution" subtitle="Visual breakdown by urgency.">
            <SeverityPieChart data={metrics.severity_distribution || []} />
          </SectionCard>
          <SectionCard title="Alerts Over Time" subtitle="Recent alert intake trend.">
            <LineChart data={trendData} titleKey="day" valueKey="count" />
          </SectionCard>
          <SectionCard title="Top Rules" subtitle="Most active detections in the queue.">
            <BarChart data={topRules} />
          </SectionCard>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard title="Top Affected Assets" subtitle="Most frequently impacted targets.">
          <BarChart data={metrics.top_assets || []} />
        </SectionCard>
        <SectionCard title="Activity Feed" subtitle="Grouped, readable operational updates.">
          <ActivityFeed items={activity.slice(0, 10)} compact />
        </SectionCard>
      </div>
    </div>
  );
}
