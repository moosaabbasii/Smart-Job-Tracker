// Workday (*.myworkdayjobs.com) — detects the application submission confirmation

(function () {
  let logged = false;

  function checkConfirmation() {
    if (logged) return;

    const bodyText = document.body?.innerText?.toLowerCase() || "";
    const isConfirm =
      bodyText.includes("you have successfully submitted") ||
      bodyText.includes("application submitted") ||
      bodyText.includes("thank you for applying") ||
      bodyText.includes("your application has been received") ||
      document.querySelector("[data-automation-id='confirmationPage']") !== null;

    if (!isConfirm) return;

    const { company, role } = extractWorkday();
    if (!company && !role) return;

    logged = true;
    chrome.runtime.sendMessage({
      type: "JOB_APPLIED",
      data: { company, role, source: "Workday" },
    });
  }

  function extractWorkday() {
    // Company: extract from subdomain e.g. amazon.wd5.myworkdayjobs.com
    const host    = window.location.hostname; // e.g. amazon.wd5.myworkdayjobs.com
    const company = host.split(".")[0].replace(/-/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());

    // Role: Workday renders job title in a specific element
    const role =
      document.querySelector("[data-automation-id='jobPostingHeader']")?.innerText?.trim() ||
      document.querySelector(".css-1q2dra3")?.innerText?.trim() ||
      document.querySelector("h2[data-automation-id]")?.innerText?.trim() ||
      document.querySelector("h1")?.innerText?.trim() ||
      "";

    return { company, role };
  }

  // Workday is a heavy SPA — poll every second for the confirmation
  const interval = setInterval(() => {
    checkConfirmation();
    if (logged) clearInterval(interval);
  }, 1000);

  // Also watch DOM mutations
  new MutationObserver(checkConfirmation).observe(document.body, {
    childList: true,
    subtree: true,
  });
})();
