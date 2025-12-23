async function fetchJSON(url) {
  const res = await fetch(url);
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return null;
  return await res.json();
}
function renderStores(items) {
  const tbody = document.querySelector("#userStoresTable tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  (items || []).forEach(i => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i.accountId}</td>
      <td>${i.storeDomain || ""}</td>
    `;
    tbody.appendChild(tr);
  });
}
document.addEventListener("DOMContentLoaded", async () => {
  const summ = document.getElementById("userSummary");
  if (summ) {
    const users = await fetchJSON("/admin/users/list");
    const u = (users && users.users || []).find(x => x.id === userId);
    summ.textContent = u ? `${u.email}` : `Usuário ${userId}`;
  }
  const stores = await fetchJSON(`/admin/users/${userId}/stores`);
  renderStores(stores && stores.stores);
  const form = document.getElementById("createUserStoreForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("userStoreEmail").value.trim();
      const storeDomain = document.getElementById("userStoreDomain").value.trim();
      const res = await fetch(`/admin/users/${userId}/stores/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, storeDomain })
      });
      const el = document.getElementById("createUserStoreResult");
      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : await res.text();
      if (el) el.textContent = typeof body === "string" ? body : JSON.stringify(body);
      const stores2 = await fetchJSON(`/admin/users/${userId}/stores`);
      renderStores(stores2 && stores2.stores);
    });
  }
});
