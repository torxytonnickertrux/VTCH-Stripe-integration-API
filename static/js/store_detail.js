async function fetchJSON(url) {
  const res = await fetch(url);
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return null;
  return await res.json();
}
function renderDispatches(items) {
  const tbody = document.querySelector("#dispatchesTable tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  (items || []).forEach(i => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i.eventId}</td>
      <td>${i.orderId || ""}</td>
      <td>${i.status || ""}</td>
      <td>${i.attempts || 0}</td>
      <td>${i.deliveredAt || ""}</td>
    `;
    tbody.appendChild(tr);
  });
}
function renderWebhooks(items) {
  const tbody = document.querySelector("#webhooksTable tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  (items || []).forEach(i => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i.eventId}</td>
      <td>${i.type}</td>
      <td>${i.receivedAt || ""}</td>
    `;
    tbody.appendChild(tr);
  });
}
document.addEventListener("DOMContentLoaded", async () => {
  const summ = document.getElementById("summary");
  const info = await fetchJSON(`/stores/get/${encodeURIComponent(accountId)}`);
  if (summ && info) {
    summ.textContent = `Loja: ${info.accountId} · Usuário: ${info.email || info.userId || "N/D"} · storeDomain: ${info.storeDomain || ""}`;
    const inp = document.getElementById("detailStoreDomain");
    if (inp) inp.value = info.storeDomain || "";
  }
  const d = await fetchJSON(`/stores/dispatches/${encodeURIComponent(accountId)}`);
  renderDispatches(d && d.dispatches);
  const w = await fetchJSON(`/stores/webhooks/${encodeURIComponent(accountId)}`);
  renderWebhooks(w && w.webhooks);
  const form = document.getElementById("storeDetailUpdateForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const storeDomain = document.getElementById("detailStoreDomain").value.trim();
      const res = await fetch("/admin/stores/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId, storeDomain })
      });
      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : await res.text();
      const el = document.getElementById("detailResult");
      if (el) el.textContent = typeof body === "string" ? body : JSON.stringify(body);
    });
  }
  const delBtn = document.getElementById("detailDeleteBtn");
  if (delBtn) {
    delBtn.addEventListener("click", async () => {
      await fetch(`/admin/stores/delete/${encodeURIComponent(accountId)}`, { method: "DELETE" });
      const el = document.getElementById("detailResult");
      if (el) el.textContent = "Loja removida";
    });
  }
});
