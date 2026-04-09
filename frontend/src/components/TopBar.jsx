import { RefreshCw } from "lucide-react";

export function TopBar({
  backendUrl,
  setBackendUrl,
  token,
  setToken,
  username,
  setUsername,
  password,
  setPassword,
  currentUser,
  loading,
  loggingIn,
  generatingDemo,
  runningModuleAction,
  demoResult,
  refresh,
  mode,
  badges,
  login,
  runDemoAlerts,
  runFIMScan,
  runVulnerabilityScan
}) {
  function handleLoginSubmit(event) {
    event.preventDefault();
    login();
  }

  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5 shadow-panel">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Security Operations Center</p>
          <h1 className="mt-2 text-3xl font-semibold text-white md:text-4xl">Alert Workbench</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Alerts are the primary working queue. Use the local token or username/password flow, inspect correlated cases and playbooks, and replay demo traffic when local-dev APIs are enabled.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <div className="rounded-full border border-red-400/30 bg-red-400/10 px-3 py-1 text-xs font-medium text-red-100">
              Critical Alerts: {badges?.criticalAlerts ?? 0}
            </div>
            <div className="rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1 text-xs font-medium text-amber-100">
              Open Cases: {badges?.openCases ?? 0}
            </div>
            <div className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-100">
              Running Playbooks: {badges?.runningPlaybooks ?? 0}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={refresh}
            className="inline-flex h-11 items-center justify-center rounded-2xl bg-white px-5 text-sm font-medium text-slate-950 transition hover:bg-slate-200"
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={runDemoAlerts}
            className="inline-flex h-11 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/20"
          >
            {generatingDemo ? "Generating..." : "Generate Demo Alerts"}
          </button>
          <button
            type="button"
            onClick={runFIMScan}
            className="inline-flex h-11 items-center justify-center rounded-2xl border border-orange-400/20 bg-orange-400/10 px-5 text-sm font-medium text-orange-100 transition hover:bg-orange-400/20"
          >
            {runningModuleAction === "fim" ? "Running FIM..." : "Run FIM Scan"}
          </button>
          <button
            type="button"
            onClick={runVulnerabilityScan}
            className="inline-flex h-11 items-center justify-center rounded-2xl border border-red-400/20 bg-red-400/10 px-5 text-sm font-medium text-red-100 transition hover:bg-red-400/20"
          >
            {runningModuleAction === "vulnerability" ? "Running Vuln Scan..." : "Run Vulnerability Scan"}
          </button>
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr_auto]">
        <label className="block">
          <span className="mb-2 block text-sm text-slate-400">Backend URL</span>
          <input
            value={backendUrl}
            onChange={(event) => setBackendUrl(event.target.value)}
            className="h-11 w-full rounded-2xl border border-white/10 bg-ink-900/80 px-4 text-sm text-white outline-none ring-0 transition focus:border-cyan-400/40"
          />
        </label>

        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleLoginSubmit}>
          <label className="block">
            <span className="mb-2 block text-sm text-slate-400">Username</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="admin"
              className="h-11 w-full rounded-2xl border border-white/10 bg-ink-900/80 px-4 text-sm text-white outline-none ring-0 transition focus:border-cyan-400/40"
            />
          </label>

          <div className="flex gap-3">
            <label className="block flex-1">
              <span className="mb-2 block text-sm text-slate-400">Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                className="h-11 w-full rounded-2xl border border-white/10 bg-ink-900/80 px-4 text-sm text-white outline-none ring-0 transition focus:border-cyan-400/40"
              />
            </label>
            <button
              type="submit"
              className="mt-[1.75rem] inline-flex h-11 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/20"
            >
              {loggingIn ? "Signing in..." : "Sign in"}
            </button>
          </div>
        </form>

        <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Session</div>
          <div className="mt-2 text-sm text-white">{currentUser ? currentUser.name || currentUser.username || "Authenticated" : "Demo mode"}</div>
          <div className="mt-1 text-xs text-slate-400">Data mode: {mode}</div>
        </div>
      </div>

      <div className="mt-4">
        <label className="block">
          <span className="mb-2 block text-sm text-slate-400">Manual DRF Token Fallback</span>
          <input
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Paste Token ..."
            className="h-11 w-full rounded-2xl border border-white/10 bg-ink-900/80 px-4 text-sm text-white outline-none ring-0 transition focus:border-cyan-400/40"
          />
        </label>
      </div>

      {demoResult ? (
        <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-sm text-cyan-50">
          <div className="font-medium text-cyan-100">
            {demoResult.stream === "local-fim"
              ? "FIM scan completed"
              : demoResult.stream === "local-vulnerability"
                ? "Vulnerability scan completed"
                : "Demo batch injected"}
          </div>
          <div className="mt-2 text-cyan-50/90">
            {demoResult.stream === "local-fim" || demoResult.stream === "local-vulnerability"
              ? <>Generated {demoResult.generated_alerts} alerts from <span className="font-medium">{demoResult.stream}</span>.</>
              : <>Queued {demoResult.generated_alerts} records into <span className="font-medium">{demoResult.stream}</span>.</>}
            {" "}Processed delta: alerts {demoResult.processed_delta?.alerts ?? 0}, cases {demoResult.processed_delta?.cases ?? 0},
            {" "}playbooks {demoResult.processed_delta?.playbooks ?? 0}, messages {demoResult.processed_delta?.messages ?? 0}.
          </div>
          <div className="mt-2 text-xs text-cyan-50/70">
            Before {demoResult.counts_before?.alerts ?? 0}/{demoResult.counts_before?.cases ?? 0}/{demoResult.counts_before?.playbooks ?? 0}/{demoResult.counts_before?.messages ?? 0}
            {" "}to{" "}After {demoResult.counts_after?.alerts ?? 0}/{demoResult.counts_after?.cases ?? 0}/{demoResult.counts_after?.playbooks ?? 0}/{demoResult.counts_after?.messages ?? 0}
            {" "}for alerts/cases/playbooks/messages.
          </div>
          {(demoResult.counts_before?.alerts ?? 0) === 0 && (demoResult.counts_after?.alerts ?? 0) === 0 ? (
            <div className="mt-3 rounded-2xl border border-amber-300/20 bg-amber-300/10 px-3 py-2 text-xs text-amber-100">
              This response came from an older backend process that does not have the new local fallback loaded. Restart Django on port 7000, then try again.
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
