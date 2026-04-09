import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatTimestamp } from "../lib/utils";

export function CampaignsPage({ campaigns }) {
  return (
    <SectionCard
      title="Campaigns"
      subtitle="Correlated alert clusters grouped by user, asset, network indicators, and time window."
    >
      <div className="space-y-4">
        {campaigns.length ? campaigns.map((campaign) => (
          <div key={campaign.rowid} className="rounded-3xl border border-white/10 bg-black/20 p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-lg font-medium text-white">{campaign.name}</h3>
                  <StatusBadge value={`Risk ${campaign.risk_score || 0}`} />
                  <StatusBadge value={`${campaign.alert_count || 0} Alerts`} />
                </div>
                <div className="mt-2 text-sm text-slate-400">{campaign.correlation_basis || "Correlation basis unavailable."}</div>
              </div>
              <div className="text-sm text-slate-500">Latest {formatTimestamp(campaign.latest_seen)}</div>
            </div>

            <div className="mt-4 grid gap-3 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Users</div>
                <div className="mt-2 space-y-1 text-sm text-white">
                  {(campaign.users || []).length ? campaign.users.map((item) => <div key={item}>{item}</div>) : <div className="text-slate-400">No user entity</div>}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Assets</div>
                <div className="mt-2 space-y-1 text-sm text-white">
                  {(campaign.assets || []).length ? campaign.assets.map((item) => <div key={item}>{item}</div>) : <div className="text-slate-400">No asset entity</div>}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Domains / IPs</div>
                <div className="mt-2 space-y-1 text-sm text-white">
                  {[...(campaign.domains || []), ...(campaign.ips || [])].length
                    ? [...(campaign.domains || []), ...(campaign.ips || [])].map((item) => <div key={item}>{item}</div>)
                    : <div className="text-slate-400">No network indicators</div>}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Attack Summary</div>
                <div className="mt-2 space-y-1 text-sm text-white">
                  {(campaign.attack_summary || []).length ? campaign.attack_summary.map((item) => <div key={item}>{item}</div>) : <div className="text-slate-400">No ATT&CK mapping</div>}
                </div>
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Grouped Alerts</div>
              <div className="mt-3 space-y-3">
                {(campaign.alerts || []).map((alert) => (
                  <div key={alert.rowid} className="flex flex-col gap-2 rounded-2xl border border-white/10 bg-black/20 p-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-sm text-white">{alert.title}</div>
                      <div className="mt-1 text-xs text-slate-500">{alert.rule_id}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge value={alert.severity || "Unknown"} />
                      <div className="text-xs text-slate-500">{formatTimestamp(alert.first_seen_time)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )) : (
          <div className="rounded-3xl border border-dashed border-white/10 bg-black/20 p-6 text-sm text-slate-400">
            No campaigns available yet. Generate demo alerts or run local modules to populate correlated attack clusters.
          </div>
        )}
      </div>
    </SectionCard>
  );
}
