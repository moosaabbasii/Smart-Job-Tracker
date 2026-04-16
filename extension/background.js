const API_BASE    = "https://k9gpcxpt4j.execute-api.us-east-1.amazonaws.com/prod";
const CLIENT_ID   = "2k1gkrhmlg5hn90kk2apfeen2a";
const COGNITO_URL = "https://cognito-idp.us-east-1.amazonaws.com/";

// ── ALARM SETUP ───────────────────────────────────────────────────────────────
// Create alarm on first install or extension update
chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("syncJobs", { periodInMinutes: 1 });
});

// Recreate alarm when Chrome itself restarts (clears alarms on browser restart)
chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.get("syncJobs", (alarm) => {
    if (!alarm) chrome.alarms.create("syncJobs", { periodInMinutes: 1 });
  });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "syncJobs") processQueue();
});

// ── LISTEN FOR MESSAGES ───────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "JOB_APPLIED") {
    enqueueJob(message.data).then(() => sendResponse({ success: true }));
    return true;
  }
  if (message.type === "GET_RECENT") {
    getRecentApplications(sendResponse);
    return true;
  }
});

// ── JOB QUEUE ─────────────────────────────────────────────────────────────────
async function enqueueJob(data) {
  const isDupe = await checkDuplicate(data.company, data.role);
  if (isDupe) {
    console.log("[SmartJobTracker] Duplicate — skipping");
    return;
  }

  const job = {
    id:             `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    company:        data.company || "Unknown Company",
    role:           data.role    || "Unknown Role",
    status:         "Applied",
    date_applied:   new Date().toISOString().split("T")[0],
    follow_up_date: "",
    notes:          `Auto-logged via ${data.source} extension`,
    queued_at:      new Date().toISOString(),
    attempts:       0,
  };

  const stored  = await chrome.storage.local.get("pendingJobs");
  const pending = stored.pendingJobs || [];
  pending.push(job);
  await chrome.storage.local.set({ pendingJobs: pending });

  console.log("[SmartJobTracker] Job queued:", job.role, "at", job.company);

  await saveLocally(job);
  showNotification(job.role, job.company, data.source);

  // Try to sync immediately, alarm is backup
  processQueue();
}

async function processQueue() {
  const stored  = await chrome.storage.local.get("pendingJobs");
  const pending = stored.pendingJobs || [];
  if (!pending.length) return;

  console.log(`[SmartJobTracker] Queue: ${pending.length} job(s) to sync`);

  const token = await getValidToken();
  if (!token) {
    console.warn("[SmartJobTracker] No valid token — will retry on next alarm");
    return;
  }

  const stillPending = [];

  for (const job of pending) {
    const sent = await sendToAPI(job, token);
    if (sent) {
      console.log("[SmartJobTracker] ✅ Synced:", job.role, "at", job.company);
    } else {
      job.attempts = (job.attempts || 0) + 1;
      if (job.attempts < 10) {
        stillPending.push(job);
        console.warn(`[SmartJobTracker] Retry ${job.attempts}/10:`, job.role);
      } else {
        console.error("[SmartJobTracker] ❌ Gave up after 10 attempts:", job.role);
      }
    }
  }

  await chrome.storage.local.set({ pendingJobs: stillPending });
}

// ── API CALL WITH 401 RETRY ───────────────────────────────────────────────────
async function sendToAPI(job, token) {
  const payload = {
    company:        job.company,
    role:           job.role,
    status:         job.status,
    date_applied:   job.date_applied,
    follow_up_date: job.follow_up_date,
    notes:          job.notes,
  };

  try {
    let res = await fetch(`${API_BASE}/applications`, {
      method:  "POST",
      headers: {
        "Content-Type":  "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (res.status === 401) {
      console.log("[SmartJobTracker] 401 — refreshing token and retrying");
      const freshToken = await forceRefreshToken();
      if (!freshToken) return false;
      res = await fetch(`${API_BASE}/applications`, {
        method:  "POST",
        headers: {
          "Content-Type":  "application/json",
          "Authorization": `Bearer ${freshToken}`,
        },
        body: JSON.stringify(payload),
      });
    }

    return res.ok;
  } catch (e) {
    console.error("[SmartJobTracker] Network error:", e.message);
    return false;
  }
}

// ── TOKEN MANAGEMENT ──────────────────────────────────────────────────────────
let _refreshPromise = null;

async function getValidToken() {
  const stored = await chrome.storage.local.get(["idToken", "refreshToken", "tokenExpiry"]);
  if (stored.idToken && stored.tokenExpiry && Date.now() < stored.tokenExpiry - 300_000) {
    return stored.idToken;
  }
  return forceRefreshToken();
}

async function forceRefreshToken() {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = _doRefresh().finally(() => { _refreshPromise = null; });
  return _refreshPromise;
}

async function _doRefresh() {
  const stored = await chrome.storage.local.get("refreshToken");
  if (!stored.refreshToken) {
    console.warn("[SmartJobTracker] No refresh token — user must log in");
    return null;
  }

  try {
    const res = await fetch(COGNITO_URL, {
      method:  "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
      },
      body: JSON.stringify({
        AuthFlow:       "REFRESH_TOKEN_AUTH",
        AuthParameters: { REFRESH_TOKEN: stored.refreshToken },
        ClientId:       CLIENT_ID,
      }),
    });

    if (res.ok) {
      const data      = await res.json();
      const newToken  = data.AuthenticationResult.IdToken;
      const expiresIn = data.AuthenticationResult.ExpiresIn || 3600;
      await chrome.storage.local.set({
        idToken:     newToken,
        tokenExpiry: Date.now() + expiresIn * 1000,
      });
      console.log("[SmartJobTracker] 🔄 Token refreshed");
      return newToken;
    }
  } catch (e) {
    console.error("[SmartJobTracker] Refresh error:", e.message);
  }

  await chrome.storage.local.remove(["idToken", "refreshToken", "tokenExpiry"]);
  console.warn("[SmartJobTracker] Session cleared — log in again");
  return null;
}

// ── LOCAL STORAGE ─────────────────────────────────────────────────────────────
async function saveLocally(job) {
  const stored = await chrome.storage.local.get("recentApps");
  const apps   = stored.recentApps || [];
  apps.unshift({ ...job, logged_at: job.queued_at || new Date().toISOString() });
  await chrome.storage.local.set({ recentApps: apps.slice(0, 20) });
}

async function getRecentApplications(sendResponse) {
  const stored = await chrome.storage.local.get("recentApps");
  sendResponse({ apps: stored.recentApps || [] });
}

// ── DEDUPLICATION ─────────────────────────────────────────────────────────────
async function checkDuplicate(company, role) {
  const stored = await chrome.storage.local.get("recentApps");
  const apps   = stored.recentApps || [];
  const cutoff = Date.now() - 10 * 60 * 1000;
  return apps.some(a =>
    a.company?.toLowerCase() === company?.toLowerCase() &&
    a.role?.toLowerCase()    === role?.toLowerCase() &&
    new Date(a.logged_at).getTime() > cutoff
  );
}

// ── NOTIFICATION ──────────────────────────────────────────────────────────────
function showNotification(role, company, source) {
  chrome.notifications.create({
    type:    "basic",
    iconUrl: "icons/icon48.png",
    title:   "Application Logged!",
    message: company ? `${role} @ ${company}` : role,
  });
}
