const DEFAULT_BACKEND_URL = "http://127.0.0.1:7000";

function useProxyUrl(baseUrl) {
  const normalized = (baseUrl || "").trim();
  return !normalized || normalized === DEFAULT_BACKEND_URL;
}

function buildUrl(baseUrl, path) {
  if (useProxyUrl(baseUrl)) {
    return path;
  }
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function requestJson(baseUrl, path, token) {
  let response;
  try {
    response = await fetch(buildUrl(baseUrl, path), {
      headers: token
        ? {
            Authorization: `Token ${token}`
          }
        : {}
    });
  } catch {
    const error = new Error("Backend unreachable.");
    error.code = "NETWORK";
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`${path} failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

export async function loginWithPassword(baseUrl, username, password) {
  let response;
  try {
    response = await fetch(buildUrl(baseUrl, "/api/login/account"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ username, password })
    });
  } catch {
    const error = new Error("Backend unreachable.");
    error.code = "NETWORK";
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`/api/login/account failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  const payload = await response.json();
  const token = payload?.data?.token;
  if (!token || payload?.data?.status !== "ok") {
    throw new Error(payload?.msg_en || "Login failed.");
  }

  return payload;
}

export async function validateToken(baseUrl, token) {
  return requestJson(baseUrl, "/api/currentUser", token);
}

export async function probeBackend(baseUrl) {
  try {
    await fetch(buildUrl(baseUrl, "/api/currentUser"));
    return true;
  } catch {
    return false;
  }
}

export async function fetchSocSnapshot(baseUrl, token) {
  const [overview, alerts, assets, campaigns, cases, playbooks, messages, audit, responseJobs] = await Promise.all([
    requestJson(baseUrl, "/api/local-dev/overview", token),
    requestJson(baseUrl, "/api/local-dev/alerts", token),
    requestJson(baseUrl, "/api/local-dev/assets", token),
    requestJson(baseUrl, "/api/local-dev/campaigns", token),
    requestJson(baseUrl, "/api/local-dev/cases", token),
    requestJson(baseUrl, "/api/local-dev/playbooks", token),
    requestJson(baseUrl, "/api/local-dev/messages", token),
    requestJson(baseUrl, "/api/local-dev/audit", token),
    requestJson(baseUrl, "/api/local-dev/response-jobs", token)
  ]);

  return {
    overview: overview.data,
    alerts: alerts.data,
    assets: assets.data,
    campaigns: campaigns.data,
    cases: cases.data,
    playbooks: playbooks.data,
    messages: messages.data,
    audit: audit.data,
    responseJobs: responseJobs.data
  };
}

export async function fetchAlertDetail(baseUrl, token, rowid) {
  const payload = await requestJson(baseUrl, `/api/local-dev/alerts/${rowid}`, token);
  return payload.data;
}

export async function fetchCaseDetail(baseUrl, token, rowid) {
  const payload = await requestJson(baseUrl, `/api/local-dev/cases/${rowid}`, token);
  return payload.data;
}

export async function fetchAssetDetail(baseUrl, token, rowid) {
  const payload = await requestJson(baseUrl, `/api/local-dev/assets/${rowid}`, token);
  return payload.data;
}

export async function fetchPlaybookDetail(baseUrl, token, rowid) {
  const payload = await requestJson(baseUrl, `/api/local-dev/playbooks/${rowid}`, token);
  return payload.data;
}

export async function triggerResponseAction(baseUrl, token, body) {
  let response;
  try {
    response = await fetch(buildUrl(baseUrl, "/api/local-dev/respond"), {
      method: "POST",
      headers: {
        Authorization: `Token ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
  } catch {
    const error = new Error("Backend unreachable.");
    error.code = "NETWORK";
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`/api/local-dev/respond failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  const payload = await response.json();
  return payload.data;
}

export async function updateCaseWorkflow(baseUrl, token, body) {
  let response;
  try {
    response = await fetch(buildUrl(baseUrl, "/api/local-dev/case-workflow"), {
      method: "POST",
      headers: {
        Authorization: `Token ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
  } catch {
    const error = new Error("Backend unreachable.");
    error.code = "NETWORK";
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`/api/local-dev/case-workflow failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  const payload = await response.json();
  return payload.data;
}

export async function generateDemoAlerts(baseUrl, token) {
  let response;
  try {
    response = await fetch(buildUrl(baseUrl, "/api/local-dev/demo-alerts"), {
      method: "POST",
      headers: {
        Authorization: `Token ${token}`
      }
    });
  } catch {
    const error = new Error("Backend unreachable.");
    error.code = "NETWORK";
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`/api/local-dev/demo-alerts failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  const payload = await response.json();
  return payload.data;
}

async function postLocalAction(baseUrl, token, path) {
  let response;
  try {
    response = await fetch(buildUrl(baseUrl, path), {
      method: "POST",
      headers: {
        Authorization: `Token ${token}`
      }
    });
  } catch {
    const error = new Error("Backend unreachable.");
    error.code = "NETWORK";
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`${path} failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  const payload = await response.json();
  return payload.data;
}

export async function generateFIMScan(baseUrl, token) {
  return postLocalAction(baseUrl, token, "/api/local-dev/fim-scan");
}

export async function generateVulnerabilityScan(baseUrl, token) {
  return postLocalAction(baseUrl, token, "/api/local-dev/vulnerability-scan");
}

export { DEFAULT_BACKEND_URL };
