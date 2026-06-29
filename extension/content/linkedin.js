(function () {
  'use strict';

  let lastLogged    = '';
  let alreadyLogged = false; // dedup gate — only one source gets to log per application

  function extractJobInfo() {
    const role = document.querySelector('h1')?.innerText?.trim() || '';

    let company = '';
    const selectors = [
      '.job-details-jobs-unified-top-card__company-name',
      '.jobs-unified-top-card__company-name',
      '.job-details-jobs-unified-top-card__primary-description',
      '.jobs-unified-top-card__primary-description',
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el?.innerText?.trim()) {
        company = el.innerText.trim().split('\n')[0].trim();
        break;
      }
    }

    if (!company) {
      const t = document.title.replace(/\s*[|\-]\s*LinkedIn\s*$/i, '').trim();
      if (t.includes(' at ')) {
        company = t.substring(t.lastIndexOf(' at ') + 4).split('|')[0].split(',')[0].trim();
      }
    }

    return { role, company };
  }

  function logApplication(source) {
    // Dedup: whichever detector fires first wins. Network is checked first
    // each cycle, so it naturally takes priority when both fire close together.
    if (alreadyLogged) {
      console.log(`[SmartJobTracker] Ignored duplicate detection via ${source} (already logged)`);
      return;
    }

    const { role, company } = extractJobInfo();
    if (!role || !company) return;

    const key = `${role}||${company}`;
    if (key === lastLogged) return;
    lastLogged    = key;
    alreadyLogged = true;

    // Cooldown — allow re-logging the same job if you genuinely re-apply later
    setTimeout(() => { alreadyLogged = false; }, 30_000);

    console.log(`[SmartJobTracker] ✅ Detected via ${source}:`, { role, company });
    chrome.runtime.sendMessage({
      type: 'JOB_APPLIED',
      data: { company, role, source: 'LinkedIn' },
    });

    // If a DOM detector caught this (not the network path), use it as a
    // training signal to learn the real apply endpoint.
    if (source === 'mutation' || source === 'dom-poll') calibrate();
  }

  // ── Strategy 1 (PRIMARY): network interception ─────────────────────────────
  // Fires either from the interceptor's hard-coded match, or from a URL the
  // extension has *learned* corresponds to a successful apply (see below).
  document.addEventListener('__sjt_applied__', () => logApplication('network'));

  // ── SELF-LEARNING: figure out the apply endpoint automatically ─────────────
  // The interceptor broadcasts every POST URL. We keep a short rolling buffer
  // of recent POSTs; when the DOM detector confirms a successful apply, the
  // URLs that fired in the seconds just before are "candidates". A candidate
  // that lines up with 2 separate successful applies gets promoted to the
  // confirmed apply endpoint — after which network detection runs on its own.
  let recentPosts   = [];          // [{ url, time }]
  let confirmedUrl  = null;        // learned apply endpoint, once known

  // Ignore obvious noise: tracking, telemetry, realtime, media, metrics.
  const JUNK = /(\/li\/track|\/realtime|realtimeFrontend|\/metrics|\/beacon|\.licdn\.com|voyagerMetrics|\/messaging\/|presence|typing)/i;

  chrome.storage.local.get('sjt_confirmed_apply_url', (r) => {
    confirmedUrl = r.sjt_confirmed_apply_url || null;
    if (confirmedUrl) console.log('[SmartJobTracker] Using learned apply endpoint:', confirmedUrl);
  });

  document.addEventListener('__sjt_post__', (e) => {
    const url = e.detail;
    if (!url || JUNK.test(url)) return;
    recentPosts.push({ url, time: Date.now() });
    // keep only the last 15 seconds
    const cutoff = Date.now() - 15_000;
    recentPosts = recentPosts.filter(p => p.time > cutoff);
    // If we've already learned the endpoint, fire network detection directly.
    if (confirmedUrl && url.split('?')[0] === confirmedUrl) {
      logApplication('network-learned');
    }
  });

  // Called when the DOM detector confirms an apply. Scores recent POST URLs.
  function calibrate() {
    if (confirmedUrl) return; // already learned — nothing to do
    const cutoff = Date.now() - 12_000;
    const candidates = [...new Set(
      recentPosts.filter(p => p.time > cutoff).map(p => p.url.split('?')[0])
    )];
    if (!candidates.length) return;

    chrome.storage.local.get('sjt_url_scores', (r) => {
      const scores = r.sjt_url_scores || {};
      for (const url of candidates) {
        scores[url] = (scores[url] || 0) + 1;
        if (scores[url] >= 2) {
          confirmedUrl = url;
          chrome.storage.local.set({ sjt_confirmed_apply_url: url });
          console.log('[SmartJobTracker] 🎓 Learned apply endpoint:', url);
        }
      }
      chrome.storage.local.set({ sjt_url_scores: scores });
    });
  }

  // ── Strategy 2 & 3: DOM — only match unambiguous post-submit phrases ───────
  // These phrases ONLY appear after a successful Easy Apply submission.
  // They do NOT appear on job listing pages passively.
  const SUCCESS_PHRASES = [
    'application was sent',
    'application submitted',
    'successfully applied',
  ];

  function hasSuccess(text) {
    const lower = (text || '').toLowerCase();
    return SUCCESS_PHRASES.some(p => lower.includes(p));
  }

  // MutationObserver — catches the success modal the instant it appears
  new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === Node.ELEMENT_NODE && hasSuccess(node.innerText)) {
          logApplication('mutation');
          return;
        }
      }
    }
  }).observe(document.body, { childList: true, subtree: true });

  // Polling fallback every 2s
  setInterval(() => {
    const dialog = document.querySelector('[role="dialog"]') || document.body;
    const alerts = dialog.querySelectorAll('[role="alert"],[role="status"]');
    for (const el of alerts) {
      if (hasSuccess(el.innerText)) { logApplication('dom-poll'); return; }
    }
    if (dialog.querySelector('[class*="inline-feedback--success"]')) {
      logApplication('dom-poll');
    }
  }, 2000);

  console.log('[SmartJobTracker] LinkedIn listener active (network + mutation + dom-poll)');
})();
