import { useState } from "react";
import { DetailDrawer } from "../components/DetailDrawer";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatTimestamp } from "../lib/utils";

const criticalityTone = {
  Critical: "border-red-400/30 bg-red-400/15 text-red-200",
  High: "border-orange-400/30 bg-orange-400/15 text-orange-200",
  Medium: "border-amber-400/30 bg-amber-400/15 text-amber-200",
  Low: "border-sky-400/30 bg-sky-400/15 text-sky-200",
};

function CriticalityBadge({ value }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${criticalityTone[value] || "border-white/15 bg-white/5 text-slate-200"}`}>
      {value || "Unknown"}
    </span>
  );
}

export function AssetsPage({ assets, loadAssetDetail }) {
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  async function openAsset(rowid) {
    setLoadingDetail(true);
    try {
      const detail = await loadAssetDetail(rowid);
      setSelectedAsset(detail);
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <>
      <SectionCard
        title="Asset Inventory"
        subtitle="Tracked hosts and agents with criticality, last-seen status, software inventory, and local exposure context."
      >
        <div className="grid gap-4 xl:grid-cols-2">
          {(assets || []).map((asset) => (
            <button
              key={asset.rowid}
              type="button"
              onClick={() => openAsset(asset.rowid)}
              className="rounded-2xl border border-white/10 bg-black/20 p-5 text-left transition hover:border-cyan-400/20 hover:bg-white/[0.03]"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-lg font-medium text-white">{asset.hostname}</div>
                  <div className="mt-2 text-sm text-slate-400">{asset.owner || "Unassigned"} · {asset.ip_address || "No IP"}</div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <CriticalityBadge value={asset.criticality} />
                  <StatusBadge value={asset.status} />
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Last Seen</div>
                  <div className="mt-2 text-sm text-white">{formatTimestamp(asset.last_seen)}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Software</div>
                  <div className="mt-2 text-sm text-white">{asset.software_count || 0}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Open Vulns</div>
                  <div className="mt-2 text-sm text-white">{asset.vulnerability_count || 0}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </SectionCard>

      <DetailDrawer
        open={Boolean(selectedAsset)}
        title={selectedAsset?.hostname || "Asset detail"}
        subtitle={selectedAsset?.rowid}
        onClose={() => setSelectedAsset(null)}
      >
        {loadingDetail && !selectedAsset ? <div className="text-sm text-slate-400">Loading asset detail...</div> : null}
        {selectedAsset ? (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-2">
              <CriticalityBadge value={selectedAsset.criticality} />
              <StatusBadge value={selectedAsset.status} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Owner</div>
                <div className="mt-2 text-sm text-white">{selectedAsset.owner || "Unassigned"}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Last Seen</div>
                <div className="mt-2 text-sm text-white">{formatTimestamp(selectedAsset.last_seen)}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Operating System</div>
                <div className="mt-2 text-sm text-white">{selectedAsset.operating_system || "Unknown"}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Isolation State</div>
                <div className="mt-2 text-sm text-white">{selectedAsset.isolation_state || "Connected"}</div>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Software Inventory</div>
              <div className="mt-3 space-y-2">
                {(selectedAsset.software_inventory || []).map((software) => (
                  <div key={`${software.name}-${software.version}`} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm">
                    <span className="text-white">{software.name}</span>
                    <span className="text-slate-400">{software.version}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Vulnerability Exposure</div>
              <div className="mt-3 space-y-3">
                {(selectedAsset.vulnerabilities || []).length ? (selectedAsset.vulnerabilities || []).map((item) => (
                  <div key={`${item.cve}-${item.package}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm text-white">{item.cve}</div>
                      <CriticalityBadge value={item.severity} />
                    </div>
                    <div className="mt-2 text-xs text-slate-400">{item.package} {item.installed_version} · fixed in {item.fixed_in}</div>
                  </div>
                )) : <div className="text-sm text-slate-400">No vulnerability findings recorded.</div>}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Integrity Findings</div>
              <div className="mt-3 space-y-3">
                {(selectedAsset.integrity_findings || []).length ? (selectedAsset.integrity_findings || []).map((item) => (
                  <div key={`${item.path}-${item.observed_at || item.severity}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                    <div className="text-sm text-white">{item.path}</div>
                    <div className="mt-2 text-xs text-slate-400">{item.severity} · {formatTimestamp(item.observed_at || selectedAsset.last_seen)}</div>
                  </div>
                )) : <div className="text-sm text-slate-400">No integrity findings recorded.</div>}
              </div>
            </div>
          </div>
        ) : null}
      </DetailDrawer>
    </>
  );
}
