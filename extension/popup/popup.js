const API_BASE    = "https://k9gpcxpt4j.execute-api.us-east-1.amazonaws.com/prod";
const CLIENT_ID   = "2k1gkrhmlg5hn90kk2apfeen2a";
const COGNITO_URL = "https://cognito-idp.us-east-1.amazonaws.com/";

const SOURCE_COLORS = {
  LinkedIn:   "#0077B5",
  Indeed:     "#2164F3",
  Greenhouse: "#3AB549",
  Lever:      "#0a66c2",
  Workday:    "#F5622D",
};

// ── INIT ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  const { idToken } = await chrome.storage.local.get("idToken");

  if (idToken) {
    showDashboard(idToken);
  } else {
    showLogin();
  }

  document.getElementById("loginBtn").addEventListener("click", handleLogin);
  document.getElementById("logoutBtn").addEventListener("click", handleLogout);
  document.getElementById("clearBtn").addEventListener("click", clearHistory);

  // Allow Enter key on password field
  document.getElementById("loginPassword").addEventListener("keydown", e => {
    if (e.key === "Enter") handleLogin();
  });
});

// ── AUTH ──────────────────────────────────────────────────────────────────────
async function handleLogin() {
  const email    = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  const errEl    = document.getElementById("loginError");
  const btn      = document.getElementById("loginBtn");

  errEl.style.display = "none";
  btn.textContent = "Signing in…";
  btn.disabled = true;

  try {
    const res = await fetch(COGNITO_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
      },
      body: JSON.stringify({
        AuthFlow: "USER_PASSWORD_AUTH",
        AuthParameters: { USERNAME: email, PASSWORD: password },
        ClientId: CLIENT_ID,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || data.__type || "Login failed");
    }

    const auth      = data.AuthenticationResult;
    const token     = auth.IdToken;
    const expiresIn = auth.ExpiresIn || 3600;
    await chrome.storage.local.set({
      idToken:      token,
      refreshToken: auth.RefreshToken,
      tokenExpiry:  Date.now() + expiresIn * 1000,
    });
    showDashboard(token);

  } catch (e) {
    errEl.textContent = e.message;
    errEl.style.display = "block";
    btn.textContent = "Sign In";
    btn.disabled = false;
  }
}

async function handleLogout() {
  await chrome.storage.local.remove("idToken");
  showLogin();
}

// ── VIEW SWITCHING ─────────────────────────────────────────────────────────────
function showLogin() {
  document.getElementById("loginView").style.display = "block";
  document.getElementById("dashView").style.display  = "none";
  document.getElementById("loginEmail").value    = "";
  document.getElementById("loginPassword").value = "";
  document.getElementById("loginError").style.display = "none";
  document.getElementById("loginBtn").textContent = "Sign In";
  document.getElementById("loginBtn").disabled    = false;
}

function showDashboard(token) {
  document.getElementById("loginView").style.display = "none";
  document.getElementById("dashView").style.display  = "block";
  checkAPIStatus(token);
  loadRecentApps();
  detectCurrentJob(token);
}

// ── LOG THIS JOB ──────────────────────────────────────────────────────────────
async function detectCurrentJob(token) {
  const section = document.getElementById("logJobSection");

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url) return;

    const isJobSite = (
      tab.url.includes("linkedin.com/jobs") ||
      tab.url.includes("indeed.com") ||
      tab.url.includes("greenhouse.io") ||
      tab.url.includes("lever.co") ||
      tab.url.includes("myworkdayjobs.com")
    );
    if (!isJobSite) return;

    // Extract role + company from the page DOM
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const role = document.querySelector("h1")?.innerText?.trim() || "";
        const companySelectors = [
          ".job-details-jobs-unified-top-card__company-name",
          ".jobs-unified-top-card__company-name",
          ".job-details-jobs-unified-top-card__primary-description",
        ];
        let company = "";
        for (const sel of companySelectors) {
          const el = document.querySelector(sel);
          if (el?.innerText?.trim()) {
            company = el.innerText.trim().split("\n")[0];
            break;
          }
        }
        // Title fallback
        if (!company) {
          const t = document.title.replace(/\s*[|\-]\s*LinkedIn\s*$/i, "").trim();
          if (t.includes(" at ")) {
            company = t.substring(t.lastIndexOf(" at ") + 4).split("|")[0].split(",")[0].trim();
          }
        }
        return { role, company };
      },
    });

    const { role, company } = results[0]?.result || {};
    if (!role || !company) return;

    document.getElementById("detectedRole").textContent    = role;
    document.getElementById("detectedCompany").textContent = company;
    section.style.display = "block";

    document.getElementById("logJobBtn").onclick = () => logDetectedJob(token, role, company);

  } catch (e) {
    // Not on a injectable page — silently skip
  }
}

async function logDetectedJob(token, role, company) {
  const btn    = document.getElementById("logJobBtn");
  const msgEl  = document.getElementById("logJobMsg");

  btn.textContent = "Logging…";
  btn.disabled    = true;

  try {
    const res = await fetch(`${API_BASE}/applications`, {
      method: "POST",
      headers: {
        "Content-Type":  "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({
        company,
        role,
        status:         "Applied",
        date_applied:   new Date().toISOString().split("T")[0],
        follow_up_date: "",
        notes:          "Logged via extension popup",
      }),
    });

    if (res.ok) {
      msgEl.style.color   = "#2ECC71";
      msgEl.textContent   = "✓ Logged successfully!";
      msgEl.style.display = "block";
      btn.textContent     = "Logged ✓";
      loadRecentApps();
    } else {
      throw new Error(`API error ${res.status}`);
    }
  } catch (e) {
    msgEl.style.color   = "#E74C3C";
    msgEl.textContent   = `Failed: ${e.message}`;
    msgEl.style.display = "block";
    btn.textContent     = "Log Job ✓";
    btn.disabled        = false;
  }
}

// ── API STATUS ────────────────────────────────────────────────────────────────
async function checkAPIStatus(token) {
  const dot = document.getElementById("statusDot");
  try {
    const res = await fetch(`${API_BASE}/applications`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    dot.className = res.ok ? "status-dot online" : "status-dot offline";
    dot.title     = res.ok ? "API online" : `API error: ${res.status}`;
  } catch {
    dot.className = "status-dot offline";
    dot.title     = "Cannot reach API";
  }
}

// ── RECENT APPS ───────────────────────────────────────────────────────────────
function loadRecentApps() {
  chrome.runtime.sendMessage({ type: "GET_RECENT" }, ({ apps }) => {
    updateStats(apps);
    renderList(apps);
  });
}

function updateStats(apps) {
  const now      = new Date();
  const todayStr = now.toISOString().split("T")[0];
  const weekAgo  = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  document.getElementById("totalToday").textContent = apps.filter(a => a.date_applied === todayStr).length;
  document.getElementById("totalWeek").textContent  = apps.filter(a => new Date(a.logged_at) >= weekAgo).length;
  document.getElementById("totalAll").textContent   = apps.length;
}

function renderList(apps) {
  const list = document.getElementById("appList");
  if (!apps.length) return;

  list.innerHTML = apps.map(app => {
    const source = extractSource(app.notes || "");
    const color  = SOURCE_COLORS[source] || "#4A90D9";
    const time   = timeAgo(new Date(app.logged_at));
    return `
      <div class="app-item" style="border-left-color:${color}">
        <div class="app-info">
          <div class="role">${esc(app.role)}</div>
          <div class="company">${esc(app.company)}</div>
        </div>
        <div class="app-right">
          <span class="app-source" style="color:${color};border-color:${color}44;background:${color}18">${source}</span>
          <div class="app-time">${time}</div>
        </div>
      </div>`;
  }).join("");
}

function extractSource(notes) {
  for (const src of ["LinkedIn", "Indeed", "Greenhouse", "Lever", "Workday"]) {
    if (notes.toLowerCase().includes(src.toLowerCase())) return src;
  }
  return "Manual";
}

function timeAgo(date) {
  const secs = Math.floor((Date.now() - date.getTime()) / 1000);
  if (secs < 60)    return "just now";
  if (secs < 3600)  return `${Math.floor(secs/60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs/3600)}h ago`;
  return `${Math.floor(secs/86400)}d ago`;
}

function esc(str) {
  return (str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

async function clearHistory() {
  await chrome.storage.local.set({ recentApps: [] });
  loadRecentApps();
  document.getElementById("appList").innerHTML = '<div class="empty">History cleared.</div>';
}
