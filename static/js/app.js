function getAccess() { return localStorage.getItem("access_token") || ""; }
function authHeaders() {
  const access = getAccess();
  return access ? { "Authorization": "Bearer " + access, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}
async function apiFetch(path, options = {}) {
  const headers = Object.assign({}, authHeaders(), options.headers || {});
  const res = await fetch(path, Object.assign({}, options, { headers }));
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  return { status: res.status, body };
}
function renderStores(accounts) {
  const tbody = document.querySelector("#storesTable tbody");
  tbody.innerHTML = "";
  (accounts || []).forEach(acc => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${acc.accountId}</td>
      <td>${acc.storeDomain || ""}</td>
      <td class="d-flex gap-2">
        <button class="btn btn-sm btn-outline-primary" data-action="onboard" data-id="${acc.accountId}">Onboarding</button>
        <button class="btn btn-sm btn-outline-secondary" data-action="status" data-id="${acc.accountId}">Status</button>
        <button class="btn btn-sm btn-outline-success" data-action="update-domain" data-id="${acc.accountId}">Salvar domínio</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}
document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("logoutBtn")?.addEventListener("click", () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/auth";
  });
  const me = await apiFetch("/api/v1/me");
  if (me.status !== 200) { window.location.href = "/auth"; return; }
  document.getElementById("meSummary").textContent = `Usuário: ${me.body.email} | Contas: ${me.body.accounts.length}`;
  renderStores(me.body.accounts);
  document.getElementById("createStoreBtn")?.addEventListener("click", async () => {
    const email = document.getElementById("newStoreEmail").value;
    const storeDomain = document.getElementById("newStoreDomain").value;
    const r = await apiFetch("/api/v1/create-connect-account", { method: "POST", body: JSON.stringify({ email, storeDomain }) });
    document.getElementById("createStoreResult").textContent = r.status === 200 ? `Conta criada: ${r.body.accountId}` : (r.body?.error || "Erro");
    const me2 = await apiFetch("/api/v1/me"); renderStores(me2.body.accounts);
  });
  document.querySelector("#storesTable")?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button"); if (!btn) return;
    const id = btn.dataset.id;
    const action = btn.dataset.action;
    if (action === "onboard") {
      const r = await apiFetch("/api/v1/create-account-link", { method: "POST", body: JSON.stringify({ accountId: id }) });
      if (r.status === 200 && r.body.url) window.open(r.body.url, "_blank");
      else alert(r.body?.error || "Erro");
    } else if (action === "status") {
      const r = await apiFetch(`/api/v1/account-status/${id}`);
      if (r.status === 200) alert(`Payouts: ${r.body.payoutsEnabled}, Charges: ${r.body.chargesEnabled}, Details: ${r.body.detailsSubmitted}`);
      else alert(r.body?.error || "Erro");
    } else if (action === "update-domain") {
      const val = prompt("Novo domínio da loja (https://loja.com):");
      if (!val) return;
      const r = await apiFetch("/api/v1/update-store-domain", { method: "POST", body: JSON.stringify({ accountId: id, storeDomain: val }) });
      if (r.status === 200) {
        const me3 = await apiFetch("/api/v1/me"); renderStores(me3.body.accounts);
      } else alert(r.body?.error || "Erro");
    }
  });
});

