// Runs in the PAGE's MAIN world — intercepts LinkedIn's own fetch/XHR calls.
// Fires __sjt_applied__ on the document when an application submission is detected.

(function () {
  'use strict';

  function notifyApplied(url) {
    console.log('[SmartJobTracker-MAIN] ✅ Apply request matched:', url);
    document.dispatchEvent(new CustomEvent('__sjt_applied__', { bubbles: true }));
  }

  // LinkedIn's job application submission goes through their internal
  // "voyager" API. The exact queryId/path changes over time, but it is
  // always under /voyager/api/ and the URL or request body mentions
  // "jobApplication" or "easyApply" (case varies).
  function isApplyURL(url) {
    if (!/linkedin\.com\/voyager\/api\//i.test(url)) return false;
    return /jobapplication|easyapply|jobapply/i.test(url);
  }

  // Broadcast every outgoing POST URL to the isolated-world script so it can
  // self-learn which endpoint corresponds to a successful application.
  function logCandidate(kind, url, status) {
    document.dispatchEvent(new CustomEvent('__sjt_post__', { detail: String(url || '') }));
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
        logCandidate('fetch', url, response.status);
        if (response.ok && isApplyURL(url)) {
          notifyApplied(url);
        }
      }).catch(() => {});
    }

    return promise;
  };

  // ── Intercept sendBeacon ─────────────────────────────────────────────────────
  // LinkedIn fires some submissions (and lots of tracking) via sendBeacon,
  // which is NOT covered by the fetch/XHR patches above.
  const origBeacon = navigator.sendBeacon?.bind(navigator);
  if (origBeacon) {
    navigator.sendBeacon = function (url, data) {
      const u = String(url || '');
      logCandidate('beacon', u);
      if (isApplyURL(u)) notifyApplied(u);
      return origBeacon(url, data);
    };
  }

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
      const method = this.__sjt_method?.toUpperCase();
      const url     = this.__sjt_url;
      if (method === 'POST') {
        logCandidate('xhr', url, this.status);
        if (this.status >= 200 && this.status < 300 && isApplyURL(url)) {
          notifyApplied(url);
        }
      }
    });
    return origSend.apply(this, args);
  };

  console.log('[SmartJobTracker-MAIN] Network interceptor active ✅');
})();
