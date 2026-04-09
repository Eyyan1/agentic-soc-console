import { startTransition, useCallback, useEffect, useState } from "react";
import {
  DEFAULT_BACKEND_URL,
  fetchAlertDetail,
  fetchAssetDetail,
  fetchCaseDetail,
  fetchPlaybookDetail,
  fetchSocSnapshot,
  generateDemoAlerts,
  generateFIMScan,
  generateVulnerabilityScan,
  loginWithPassword,
  probeBackend,
  triggerResponseAction,
  updateCaseWorkflow,
  validateToken
} from "../lib/api";
import { mockSocData } from "../lib/mock-data";

const STORAGE_KEYS = {
  backendUrl: "agentic-soc.backend-url",
  token: "agentic-soc.token",
  username: "agentic-soc.username"
};

export function useSocData() {
  const [backendUrl, setBackendUrl] = useState(() => localStorage.getItem(STORAGE_KEYS.backendUrl) || DEFAULT_BACKEND_URL);
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEYS.token) || "");
  const [username, setUsername] = useState(() => localStorage.getItem(STORAGE_KEYS.username) || "");
  const [password, setPassword] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loggingIn, setLoggingIn] = useState(false);
  const [generatingDemo, setGeneratingDemo] = useState(false);
  const [runningModuleAction, setRunningModuleAction] = useState("");
  const [error, setError] = useState("");
  const [mode, setMode] = useState("demo");
  const [snapshot, setSnapshot] = useState(mockSocData);
  const [backendReachable, setBackendReachable] = useState(false);
  const [tokenValid, setTokenValid] = useState(false);
  const [lastRefreshAt, setLastRefreshAt] = useState(null);
  const [demoResult, setDemoResult] = useState(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.backendUrl, backendUrl);
  }, [backendUrl]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.token, token);
  }, [token]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.username, username);
  }, [username]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      if (!token.trim()) {
        const reachable = await probeBackend(backendUrl);
        startTransition(() => {
          setCurrentUser(null);
          setSnapshot(mockSocData);
          setMode("demo");
          setBackendReachable(reachable);
          setTokenValid(false);
          setLastRefreshAt(new Date().toISOString());
        });
        return;
      }

      const me = await validateToken(backendUrl, token.trim());
      const user = me?.data ?? me;
      setBackendReachable(true);
      setTokenValid(true);

      try {
        const nextSnapshot = await fetchSocSnapshot(backendUrl, token.trim());
        startTransition(() => {
          setCurrentUser(user);
          setSnapshot(nextSnapshot);
          setMode("live");
          setLastRefreshAt(new Date().toISOString());
        });
      } catch (endpointError) {
        startTransition(() => {
          setCurrentUser(user);
          setSnapshot(mockSocData);
          setMode("fallback");
          setError(endpointError.message || "Local-dev SOC endpoints unavailable. Showing fallback data.");
          setLastRefreshAt(new Date().toISOString());
        });
      }
    } catch (authError) {
      startTransition(() => {
        setCurrentUser(null);
        setSnapshot(mockSocData);
        setMode("demo");
        setError(authError.message || "Failed to validate token.");
        setBackendReachable(authError.code !== "NETWORK");
        setTokenValid(false);
      });
    } finally {
      setLoading(false);
    }
  }, [backendUrl, token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async () => {
    setLoggingIn(true);
    setError("");

    try {
      const payload = await loginWithPassword(backendUrl, username.trim(), password);
      const nextToken = payload?.data?.token || "";

      startTransition(() => {
        setToken(nextToken);
        setPassword("");
        setBackendReachable(true);
      });
    } catch (loginError) {
      startTransition(() => {
        setError(loginError.message || "Login failed.");
      });
    } finally {
      setLoggingIn(false);
    }
  }, [backendUrl, username, password]);

  const loadAlertDetail = useCallback(async (rowid, fallbackAlert = null) => {
    const deriveAlertDetail = (alert) => {
      if (!alert) {
        return null;
      }
      const linkedCase = (snapshot.cases || []).find((item) =>
        (item.alert_rowids || []).includes(alert.rowid) || (item.alert_rowids || []).includes(alert.id)
      ) || (snapshot.cases || [])[0] || null;

      return {
        ...alert,
        linked_case: linkedCase,
        response_jobs: (snapshot.responseJobs || []).filter((item) =>
          item.target_type === "alert" && item.target_rowid === alert.rowid
        ),
        resolution_guidance: alert.resolution_guidance || {
          state: linkedCase ? "needs_playbook" : "untriaged",
          headline: linkedCase ? "Automation has not completed yet" : "No linked case yet",
          recommendation: linkedCase
            ? "Run the playbook and review the result before resolving the alert."
            : "Escalate this alert to a case or assign it for analyst review.",
          next_action: linkedCase ? "run_playbook" : "escalate_to_case"
        },
        linked_campaigns: alert.linked_campaigns || (snapshot.campaigns || []).filter((item) =>
          (item.alerts || []).some((campaignAlert) => campaignAlert.rowid === alert.rowid)
        ),
        artifacts: alert.artifacts || [],
        artifact_summary: alert.artifact_summary || { total: alert.artifacts?.length || 0, actors: [], targets: [], related: [] },
        raw_headers: alert.raw_headers || {},
        raw_event: alert.raw_event || {},
        threat_analysis: alert.threat_analysis || {
          mitre_attack: [{ tactic: "Initial Access", technique: "Phishing", id: "T1566" }],
          risk_score: 72,
          confidence_score: 0.81,
          explanation: "Local-dev analysis identified a suspicious alert pattern that warrants triage.",
          action_plan: [
            "Validate the triggering evidence and affected asset or user.",
            "Contain the blast radius with compensating controls if needed.",
            "Track remediation through a case or ticket until closure."
          ],
          entities: {
            user: alert.target || "",
            asset: alert.target?.includes("@") ? "" : alert.target || "",
            domain: alert.sender_domain || "",
            ip: ""
          }
        },
        enrichment_context: alert.enrichment_context || {
          user: { email: alert.target || "unknown", risk: "Elevated" },
          domain: { value: alert.sender_domain || "unknown", reputation: "Suspicious" },
          ip: { value: "Not observed", reputation: "Unavailable" },
          host: { value: alert.target || "Not observed", state: "Monitor" }
        },
        recommended_actions: alert.recommended_actions || [
          { id: "isolate_host", label: "Isolate host", description: "Contain the affected endpoint if a host artifact exists." },
          { id: "disable_user", label: "Disable user", description: "Temporarily disable the affected user pending validation." },
          { id: "block_domain_ip", label: "Block IP/domain/hash", description: "Block suspicious indicators at the edge or on the endpoint." },
          { id: "create_ticket", label: "Create ticket", description: "Open a tracked incident task for analyst follow-up." },
          { id: "run_playbook", label: "Run Playbook", description: "Queue the default local-dev investigation playbook." },
          { id: "assign", label: "Assign", description: "Simulate analyst assignment in local-dev mode." }
        ]
      };
    };

    const alertFromSnapshot = (snapshot.alerts || []).find((item) => item.rowid === rowid || item.id === rowid) || fallbackAlert || null;

    if (mode !== "live" || !token.trim()) {
      return deriveAlertDetail(alertFromSnapshot);
    }

    try {
      return await fetchAlertDetail(backendUrl, token.trim(), rowid);
    } catch {
      return deriveAlertDetail(alertFromSnapshot);
    }
  }, [backendUrl, mode, snapshot.alerts, snapshot.campaigns, snapshot.cases, token]);

  const loadCaseDetail = useCallback(async (rowid) => {
    if (mode !== "live" || !token.trim()) {
      const caseItem = (snapshot.cases || []).find((item) => item.rowid === rowid) || null;
      if (!caseItem) {
        return null;
      }
      return {
        ...caseItem,
        alerts: snapshot.alerts || [],
        related_alerts: snapshot.alerts || [],
        linked_assets: snapshot.assets || [],
        linked_playbooks: snapshot.playbooks || [],
        recent_messages: snapshot.messages || [],
        activity_timeline: [...(snapshot.audit || []), ...(snapshot.messages || [])],
        response_jobs: (snapshot.responseJobs || []).filter((item) =>
          item.target_type === "case" && item.target_rowid === caseItem.rowid
        ),
        attack_timeline: [
          ...(snapshot.alerts || []).map((item) => ({
            rowid: `timeline-${item.rowid}`,
            type: "alert",
            title: item.title,
            summary: item.summary,
            ts: item.first_seen_time,
            severity: item.severity
          })),
          ...(snapshot.playbooks || []).map((item) => ({
            rowid: `timeline-playbook-${item.rowid}`,
            type: "playbook",
            title: item.name,
            summary: item.remark || item.status,
            ts: item.started_at
          }))
        ].sort((left, right) => String(left.ts || "").localeCompare(String(right.ts || ""))),
        response_history: snapshot.audit || [],
        notes: [{ author: "Analyst", content: "Demo case note for local development.", ts: new Date().toISOString() }],
        disposition: "Undispositioned",
        sla: { target_minutes: 60, elapsed_minutes: 18, remaining_minutes: 42, breached: false },
        assignment: { owner: caseItem.owner || "Local SOC Pipeline", assigned: Boolean(caseItem.owner) },
        artifact_summary: { total: 0, actors: [], targets: [], related: [] },
        recommended_actions: [
          { id: "isolate_host", label: "Isolate host", description: "Contain the affected endpoint if a host artifact exists." },
          { id: "disable_user", label: "Disable user", description: "Temporarily disable the affected user pending validation." },
          { id: "block_domain_ip", label: "Block IP/domain/hash", description: "Block suspicious indicators and related hashes." },
          { id: "create_ticket", label: "Create ticket", description: "Open a tracked incident task for analyst follow-up." },
          { id: "close_false_positive", label: "Close as false positive", description: "Mark the alert benign and close associated case work." }
        ]
      };
    }
    return fetchCaseDetail(backendUrl, token.trim(), rowid);
  }, [backendUrl, mode, snapshot.alerts, snapshot.assets, snapshot.audit, snapshot.cases, snapshot.messages, snapshot.playbooks, token]);

  const loadAssetDetail = useCallback(async (rowid) => {
    if (mode !== "live" || !token.trim()) {
      return (snapshot.assets || []).find((item) => item.rowid === rowid) || null;
    }
    try {
      return await fetchAssetDetail(backendUrl, token.trim(), rowid);
    } catch {
      return (snapshot.assets || []).find((item) => item.rowid === rowid) || null;
    }
  }, [backendUrl, mode, snapshot.assets, token]);

  const loadPlaybookDetail = useCallback(async (rowid) => {
    if (mode !== "live" || !token.trim()) {
      const playbook = (snapshot.playbooks || []).find((item) => item.rowid === rowid) || null;
      if (!playbook) {
        return null;
      }
      return {
        ...playbook,
        step_trace: (snapshot.messages || []).map((item, index) => ({
          step: index + 1,
          node: item.node || `step-${index + 1}`,
          role: item.role,
          content: item.content,
          output: item.data || null,
          ts: item.ts
        }))
      };
    }
    return fetchPlaybookDetail(backendUrl, token.trim(), rowid);
  }, [backendUrl, mode, snapshot.playbooks, token]);

  const runResponseAction = useCallback(async (body) => {
    if (mode !== "live" || !token.trim()) {
      setError("Response actions are only available against the local-dev API.");
      return null;
    }
    setError("");
    const result = await triggerResponseAction(backendUrl, token.trim(), body);
    await refresh();
    return result;
  }, [backendUrl, mode, refresh, token]);

  const runCaseWorkflow = useCallback(async (body) => {
    if (mode !== "live" || !token.trim()) {
      setError("Case workflow updates are only available against the local-dev API.");
      return null;
    }
    setError("");
    const result = await updateCaseWorkflow(backendUrl, token.trim(), body);
    await refresh();
    return result;
  }, [backendUrl, mode, refresh, token]);

  const runDemoAlerts = useCallback(async () => {
    if (!token.trim()) {
      setError("Sign in or paste a token before generating demo alerts.");
      return;
    }

    setGeneratingDemo(true);
    setError("");
    try {
      const result = await generateDemoAlerts(backendUrl, token.trim());
      setDemoResult(result);
      const delay = (result?.processing_hint_seconds || 4) * 1000;
      await new Promise((resolve) => setTimeout(resolve, delay));
      await refresh();
    } catch (demoError) {
      setDemoResult(null);
      setError(demoError.message || "Failed to generate demo alerts.");
    } finally {
      setGeneratingDemo(false);
    }
  }, [backendUrl, refresh, token]);

  const runFIMScan = useCallback(async () => {
    if (!token.trim()) {
      setError("Sign in or paste a token before running the FIM scan.");
      return;
    }
    setRunningModuleAction("fim");
    setError("");
    try {
      const result = await generateFIMScan(backendUrl, token.trim());
      setDemoResult({ ...result, stream: "local-fim" });
      await refresh();
    } catch (scanError) {
      setError(scanError.message || "Failed to run the FIM scan.");
    } finally {
      setRunningModuleAction("");
    }
  }, [backendUrl, refresh, token]);

  const runVulnerabilityScan = useCallback(async () => {
    if (!token.trim()) {
      setError("Sign in or paste a token before running the vulnerability scan.");
      return;
    }
    setRunningModuleAction("vulnerability");
    setError("");
    try {
      const result = await generateVulnerabilityScan(backendUrl, token.trim());
      setDemoResult({ ...result, stream: "local-vulnerability" });
      await refresh();
    } catch (scanError) {
      setError(scanError.message || "Failed to run the vulnerability scan.");
    } finally {
      setRunningModuleAction("");
    }
  }, [backendUrl, refresh, token]);

  return {
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
    login,
    loadAlertDetail,
    loadCaseDetail,
    loadAssetDetail,
    loadPlaybookDetail,
    runResponseAction,
    runCaseWorkflow,
    runDemoAlerts,
    runFIMScan,
    runVulnerabilityScan
  };
}
