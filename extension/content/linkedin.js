// Detection strategies (whichever fires first wins):
// 1. Network interception event from linkedin_interceptor.js (MAIN world)
// 2. MutationObserver watching for success messages after submit click
// 3. DOM polling every 2s — but ONLY after submit button is clicked

(function () {
  'use strict';

  let lastLogged    = '';
  let alreadyFired  = false;
  let submitClicked = false; // guard — only trust DOM signals after submit click

  // ── Job info extraction ────────────────────────────────────────────────────
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

  // ── Log once per unique role+company ──────────────────────────────────────
  function logApplication(source) {
    if (alreadyFired) return;

    const { role, company } = extractJobInfo();
    if (!role || !company) return;

    const key = `${role}||${company}`;
    if (key === lastLogged) return;
    lastLogged    = key;
    alreadyFired  = true;
    submitClicked = false;

    setTimeout(() => { alreadyFired = false; }, 30_000);

    console.log(`[SmartJobTracker] ✅ Detected via ${source}:`, { role, company });
    chrome.runtime.sendMessage({
      type: 'JOB_APPLIED',
      data: { company, role, source: 'LinkedIn' },
    });
  }

  // ── Track submit button clicks ────────────────────────────────────────────
  // DOM/mutation detection only arms itself after the user actually clicks submit.
  // This prevents false positives from "Applied X days ago" text on the page.
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const text  = (btn.innerText || '').toLowerCase();
    const label = (btn.getAttribute('aria-label') || '').toLowerCase();
    const combined = text + ' ' + label;
    if (combined.includes('submit application') || combined.includes('submit')) {
      console.log('[SmartJobTracker] Submit button clicked — arming DOM detection');
      submitClicked = true;
      // Disarm after 15s in case submit fails / user is still on form
      setTimeout(() => { submitClicked = false; }, 15_000);
    }
  }, true);

  // ── Strategy 1: Network interception event (no guard needed) ──────────────
  document.addEventListener('__sjt_applied__', () => {
    console.log('[SmartJobTracker] Network event received');
    logApplication('network');
  });

  // ── Strategy 2: MutationObserver (only fires after submitClicked) ─────────
  // Only check "application was sent" / "application submitted" — very specific
  // post-submit phrases that don't appear during form filling.
  const POST_SUBMIT_PHRASES = [
    'application was sent',
    'application submitted',
    'successfully applied',
  ];

  function isPostSubmitText(text) {
    const lower = text.toLowerCase();
    return POST_SUBMIT_PHRASES.some(p => lower.includes(p));
  }

  function checkNodeForSuccess(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) return false;
    const text = node.innerText || '';
    if (isPostSubmitText(text)) return true;
    const headings = node.querySelectorAll?.('h1,h2,h3');
    if (headings) {
      for (const h of headings) {
        if (isPostSubmitText(h.innerText || '')) return true;
      }
    }
    return false;
  }

  const observer = new MutationObserver((mutations) => {
    if (!submitClicked) return; // don't check unless user clicked submit
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (checkNodeForSuccess(node)) {
          console.log('[SmartJobTracker] MutationObserver detected success');
          logApplication('mutation');
          return;
        }
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // ── Strategy 3: DOM polling (only active after submitClicked) ─────────────
  function pollCheck() {
    if (!submitClicked) return false;

    // Only look inside the Easy Apply modal (dialog), not the whole page.
    // This avoids matching "Applied 3 days ago" badges on job cards.
    const dialog = document.querySelector('[role="dialog"]');
    const scope  = dialog || document.body;

    const alerts = scope.querySelectorAll('[role="alert"], [role="status"]');
    for (const el of alerts) {
      if (isPostSubmitText(el.innerText || '')) return true;
    }
    if (scope.querySelector('[class*="inline-feedback--success"]')) return true;
    if (scope.querySelector('.post-apply-timeline, [class*="post-apply"]')) return true;
    return false;
  }

  setInterval(() => {
    if (pollCheck()) logApplication('dom-poll');
  }, 2000);

  console.log('[SmartJobTracker] LinkedIn listener active ✅ (network + mutation + dom-poll)');
})();
