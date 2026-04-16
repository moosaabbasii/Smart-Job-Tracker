// Lever (jobs.lever.co) — detects the application confirmation page

(function () {
  let logged = false;

  function checkConfirmation() {
    if (logged) return;

    const bodyText = document.body?.innerText?.toLowerCase() || "";
    const isConfirm =
      bodyText.includes("application has been submitted") ||
      bodyText.includes("your application was received") ||
      bodyText.includes("thanks for applying") ||
      document.querySelector(".application-confirmation") !== null ||
      window.location.href.includes("/confirmation");

    if (!isConfirm) return;

    const { company, role } = extractLever();
    if (!company && !role) return;

    logged = true;
    chrome.runtime.sendMessage({
      type: "JOB_APPLIED",
      data: { company, role, source: "Lever" },
    });
  }

  function extractLever() {
    // URL: jobs.lever.co/{company}/{job-id}
    const pathParts = window.location.pathname.split("/").filter(Boolean);
    const company   = pathParts[0]
      ? pathParts[0].replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
      : "";

    // Role from the posting headline
    const role =
      document.querySelector(".posting-headline h2")?.innerText?.trim() ||
      document.querySelector("h2")?.innerText?.trim() ||
      document.querySelector(".role-title")?.innerText?.trim() ||
      "";

    return { company, role };
  }

  checkConfirmation();
  new MutationObserver(checkConfirmation).observe(document.body, {
    childList: true,
    subtree: true,
  });

  // Handle SPA navigation
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      logged = false;
      setTimeout(checkConfirmation, 600);
    }
  }).observe(document, { subtree: true, childList: true });
})();
