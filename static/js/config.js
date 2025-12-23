document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("storeConfigForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accountId = document.getElementById("configAccountId").value.trim();
      const storeDomain = document.getElementById("configStoreDomain").value.trim();
      const res = await fetch("/config/store", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId, storeDomain })
      });
      const el = document.getElementById("storeConfigResult");
      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : await res.text();
      if (el) el.textContent = typeof body === "string" ? body : JSON.stringify(body);
    });
  }
});
