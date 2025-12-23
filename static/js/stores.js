async function fetchJSON(url) {
  const res = await fetch(url);
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return null;
  return await res.json();
}
function renderStores(stores) {
  const tbody = document.querySelector("#storesTable tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  (stores || []).forEach(s => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.accountId}</td>
      <td>${s.email}</td>
      <td>
        <input class="form-control form-control-sm" value="${s.storeDomain || ""}" data-account="${s.accountId}" data-field="storeDomain" />
      </td>
      <td class="d-flex gap-2">
        <a class="btn btn-sm btn-outline-secondary" href="/stores/${encodeURIComponent(s.accountId)}">Abrir</a>
        <button class="btn btn-sm btn-primary" data-action="save" data-account="${s.accountId}">Salvar</button>
        <button class="btn btn-sm btn-danger" data-action="delete" data-account="${s.accountId}">Excluir</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}
document.addEventListener("DOMContentLoaded", async () => {
  const data = await fetchJSON("/stores/list");
  renderStores(data && data.stores);
  const statusEl = document.getElementById("storesStatus");
  if (statusEl) {
    statusEl.textContent = `Total: ${(data && data.stores && data.stores.length) || 0}`;
  }
  const form = document.getElementById("updateStoreForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accountId = document.getElementById("updAccountId").value.trim();
      const storeDomain = document.getElementById("updStoreDomain").value.trim();
      const res = await fetch("/admin/stores/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId, storeDomain })
      });
      const el = document.getElementById("updateResult");
      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : await res.text();
      if (el) el.textContent = typeof body === "string" ? body : JSON.stringify(body);
      const data2 = await fetchJSON("/stores/list");
      renderStores(data2 && data2.stores);
    });
  }
  const upForm = document.getElementById("upsertStoreForm");
  if (upForm) {
    upForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const userId = Number(document.getElementById("upUserId").value);
      const accountId = document.getElementById("upAccountId").value.trim();
      const storeDomain = document.getElementById("upStoreDomain").value.trim();
      const res = await fetch("/admin/stores/upsert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId, accountId, storeDomain })
      });
      const el = document.getElementById("upsertResult");
      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : await res.text();
      if (el) el.textContent = typeof body === "string" ? body : JSON.stringify(body);
      const data2 = await fetchJSON("/stores/list");
      renderStores(data2 && data2.stores);
    });
  }
  document.body.addEventListener("click", async (e) => {
    const t = e.target;
    if (t && t.dataset && t.dataset.action === "save") {
      const accountId = t.dataset.account;
      const input = document.querySelector(`input[data-account="${accountId}"][data-field="storeDomain"]`);
      const storeDomain = input ? input.value.trim() : "";
      const res = await fetch("/admin/stores/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId, storeDomain })
      });
      const data2 = await fetchJSON("/stores/list");
      renderStores(data2 && data2.stores);
    }
    if (t && t.dataset && t.dataset.action === "delete") {
      const accountId = t.dataset.account;
      await fetch(`/admin/stores/delete/${encodeURIComponent(accountId)}`, { method: "DELETE" });
      const data2 = await fetchJSON("/stores/list");
      renderStores(data2 && data2.stores);
    }
  });
});
