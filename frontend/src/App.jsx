import { Route, Routes } from "react-router-dom";
import { motion } from "framer-motion";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { EnvironmentStatus } from "./components/EnvironmentStatus";
import { OverviewPage } from "./pages/OverviewPage";
import { AlertsPage } from "./pages/AlertsPage";
import { AssetsPage } from "./pages/AssetsPage";
import { CampaignsPage } from "./pages/CampaignsPage";
import { CasesPage } from "./pages/CasesPage";
import { PlaybooksPage } from "./pages/PlaybooksPage";
import { ActivityPage } from "./pages/ActivityPage";
import { ResponseJobsPage } from "./pages/ResponseJobsPage";
import { useSocData } from "./hooks/useSocData";

export default function App() {
  const {
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
    error,
    mode,
    snapshot,
    backendReachable,
    tokenValid,
    lastRefreshAt,
    demoResult,
    refresh,
    login
    ,
    runDemoAlerts,
    runFIMScan,
    runVulnerabilityScan,
    loadAlertDetail,
    loadAssetDetail,
    loadCaseDetail,
    loadPlaybookDetail,
    runResponseAction,
    runCaseWorkflow
  } = useSocData();

  const counts = {
    alerts: snapshot.alerts?.length || 0,
    cases: snapshot.cases?.length || 0,
    playbooks: snapshot.playbooks?.length || 0,
    messages: snapshot.messages?.length || 0
  };

  const badges = {
    criticalAlerts: (snapshot.alerts || []).filter((alert) => String(alert.severity || "").toLowerCase() === "critical").length,
    openCases: (snapshot.cases || []).filter((item) => !["resolved", "closed"].includes(String(item.status || "").toLowerCase())).length,
    runningPlaybooks: (snapshot.playbooks || []).filter((item) => String(item.status || "").toLowerCase() === "running").length
  };

  return (
    <div className="min-h-screen bg-soc-grid bg-[size:44px_44px]">
      <div className="flex min-h-screen">
        <Sidebar mode={mode} />

        <main className="flex-1 p-4 md:p-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="mx-auto max-w-7xl space-y-6"
          >
            <TopBar
              backendUrl={backendUrl}
              setBackendUrl={setBackendUrl}
              token={token}
              setToken={setToken}
              username={username}
              setUsername={setUsername}
              password={password}
              setPassword={setPassword}
              currentUser={currentUser}
              loading={loading}
              loggingIn={loggingIn}
              generatingDemo={generatingDemo}
              runningModuleAction={runningModuleAction}
              demoResult={demoResult}
              refresh={refresh}
              mode={mode}
              badges={badges}
              login={login}
              runDemoAlerts={runDemoAlerts}
              runFIMScan={runFIMScan}
              runVulnerabilityScan={runVulnerabilityScan}
            />

            {error ? (
              <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
                {error}
              </div>
            ) : null}

            <EnvironmentStatus
              backendReachable={backendReachable}
              tokenValid={tokenValid}
              mode={mode}
              lastRefreshAt={lastRefreshAt}
              counts={counts}
            />

            <Routes>
              <Route
                path="/"
                element={<AlertsPage alerts={snapshot.alerts || []} loadAlertDetail={loadAlertDetail} runResponseAction={runResponseAction} />}
              />
              <Route path="/overview" element={<OverviewPage snapshot={snapshot} />} />
              <Route
                path="/alerts"
                element={<AlertsPage alerts={snapshot.alerts || []} loadAlertDetail={loadAlertDetail} runResponseAction={runResponseAction} />}
              />
              <Route path="/assets" element={<AssetsPage assets={snapshot.assets || []} loadAssetDetail={loadAssetDetail} />} />
              <Route path="/campaigns" element={<CampaignsPage campaigns={snapshot.campaigns || []} />} />
              <Route
                path="/cases"
                element={<CasesPage cases={snapshot.cases || []} loadCaseDetail={loadCaseDetail} runResponseAction={runResponseAction} runCaseWorkflow={runCaseWorkflow} />}
              />
              <Route path="/playbooks" element={<PlaybooksPage playbooks={snapshot.playbooks || []} loadPlaybookDetail={loadPlaybookDetail} />} />
              <Route path="/response-jobs" element={<ResponseJobsPage responseJobs={snapshot.responseJobs || []} />} />
              <Route path="/activity" element={<ActivityPage messages={snapshot.messages || []} audit={snapshot.audit || []} responseJobs={snapshot.responseJobs || []} />} />
            </Routes>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
