// Indeed — detects the "Application submitted" confirmation page

(function () {
  let logged = false;

  function checkConfirmation() {
    if (logged) return;

    // Indeed shows a confirmation page at /applied or with a specific heading
    const confirmSelectors = [
      "[data-testid='application-submitted']",
      ".ia-ApplicationSubmitted",
      "h1.ia-ApplicationSubmitted-heading",
    ];

    const isConfirmPage =
      window.location.href.includes("/applied") ||
      window.location.href.includes("application-submitted") ||
      confirmSelectors.some((sel) => document.querySelector(sel));

    if (!isConfirmPage) return;

    const { company, role } = extractIndeed();
    if (!company && !role) return;

    logged = true;
    chrome.runtime.sendMessage({
      type: "JOB_APPLIED",
      data: { company, role, source: "Indeed" },
    });
  }

  function extractIndeed() {
    // Role from page heading or document title
    let role =
      document.querySelector("h1.jobsearch-JobInfoHeader-title")?.innerText?.trim() ||
      document.querySelector("[data-testid='jobsearch-JobInfoHeader-title']")?.innerText?.trim() ||
      "";

    // Fallback: parse from document title "Job Title - Company - Indeed"
    if (!role && document.title.includes(" - ")) {
      role = document.title.split(" - ")[0].trim();
    }

    // Company
    let company =
      document.querySelector("[data-testid='inlineHeader-companyName'] a")?.innerText?.trim() ||
      document.querySelector(".jobsearch-InlineCompanyRating-companyName")?.innerText?.trim() ||
      "";

    if (!company && document.title.includes(" - ")) {
      const parts = document.title.split(" - ");
      company = parts[1]?.trim() || "";
    }

    return { company, role };
  }

  // Run on load and watch for SPA navigation
  checkConfirmation();
  const observer = new MutationObserver(checkConfirmation);
  observer.observe(document.body, { childList: true, subtree: true });

  // Reset on navigation so we can catch the next application
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      logged = false;
      setTimeout(checkConfirmation, 800);
    }
  }).observe(document, { subtree: true, childList: true });
})();
