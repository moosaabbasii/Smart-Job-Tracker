// Greenhouse (boards.greenhouse.io) — detects the thank-you confirmation page

(function () {
  let logged = false;

  function checkConfirmation() {
    if (logged) return;

    const bodyText = document.body?.innerText?.toLowerCase() || "";
    const isConfirm =
      bodyText.includes("application has been submitted") ||
      bodyText.includes("thank you for applying") ||
      bodyText.includes("thank you for your interest") ||
      document.querySelector("#confirmation_message") !== null;

    if (!isConfirm) return;

    const { company, role } = extractGreenhouse();
    if (!company && !role) return;

    logged = true;
    chrome.runtime.sendMessage({
      type: "JOB_APPLIED",
      data: { company, role, source: "Greenhouse" },
    });
  }

  function extractGreenhouse() {
    // URL: boards.greenhouse.io/{company}/jobs/{id}
    const pathParts = window.location.pathname.split("/").filter(Boolean);
    const company   = pathParts[0]
      ? pathParts[0].replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
      : "";

    // Role from the page heading
    const role =
      document.querySelector("#header h1")?.innerText?.trim() ||
      document.querySelector(".app-title")?.innerText?.trim() ||
      document.querySelector("h1")?.innerText?.trim() ||
      "";

    return { company, role };
  }

  checkConfirmation();
  new MutationObserver(checkConfirmation).observe(document.body, {
    childList: true,
    subtree: true,
  });
})();
