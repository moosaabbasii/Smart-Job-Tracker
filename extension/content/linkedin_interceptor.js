// Runs in the PAGE's MAIN world — intercepts LinkedIn's own fetch/XHR calls.
// Fires __sjt_applied__ on the document when an application submission is detected.

(function () {
  'use strict';

  function notifyApplied() {
    console.log('[SmartJobTracker-MAIN] Firing __sjt_applied__ event');
    document.dispatchEvent(new CustomEvent('__sjt_applied__', { bubbles: true }));
  }

  // LinkedIn job application POSTs match one of these patterns:
  // - /jobs/applybutton/
  // - /jobs/application-manager/
  // - /jobs/applicantTracking/
  // - /apply (general fallback)
  // - /uas/authenticate (sometimes used)
  function isApplyURL(url) {
    return /linkedin\.com.*\/(applybutton|application-manager|applicantTracking|easyApplyModal|apply)/i.test(url);
  }

  // ── Intercept fetch ──────────────────────────────────────────────────────────
  const origFetch = window.fetch;
  window.fetch = function (...args) {
    const req    = args[0];
    const url    = req instanceof Request ? req.url : String(req || '');
    const opts   = args[1] || {};
    const method = (opts.method || (req instanceof Request ? req.method : 'GET')).toUpperCase();

    const promise = origFetch.apply(this, args);

    if (method === 'POST') {
      promise.then(response => {
        // Clone check — don't consume the real response body
        if (response.ok && isApplyURL(url)) {
          notifyApplied();
        }
      }).catch(() => {});
    }

    return promise;
  };

  // ── Intercept XHR ───────────────────────────────────────────────────────────
  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.__sjt_method = method;
    this.__sjt_url    = String(url || '');
    return origOpen.call(this, method, url, ...rest);
  };

  const origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function (...args) {
    this.addEventListener('load', () => {
      if (
        this.__sjt_method?.toUpperCase() === 'POST' &&
        this.status >= 200 && this.status < 300 &&
        isApplyURL(this.__sjt_url)
      ) {
        notifyApplied();
      }
    });
    return origSend.apply(this, args);
  };

  console.log('[SmartJobTracker-MAIN] Network interceptor active ✅');
})();
