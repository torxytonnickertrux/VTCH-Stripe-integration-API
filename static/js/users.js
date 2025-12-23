async function fetchJSON(url) {
  const res = await fetch(url);
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return null;
  return await res.json();
}
function renderUsers(users) {
  const tbody = document.querySelector("#usersTable tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  (users || []).forEach(u => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${u.id}</td>
      <td>${u.email}</td>
      <td>
        <a class="btn btn-sm btn-outline-secondary" href="/users/${u.id}">Abrir</a>
      </td>
    `;
    tbody.appendChild(tr);
  });
}
document.addEventListener("DOMContentLoaded", async () => {
  const data = await fetchJSON("/admin/users/list");
  renderUsers(data && data.users);
  const statusEl = document.getElementById("usersStatus");
  if (statusEl) statusEl.textContent = `Total: ${(data && data.users && data.users.length) || 0}`;
  const form = document.getElementById("createUserForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("newUserEmail").value.trim();
      const password = document.getElementById("newUserPassword").value.trim();
      const res = await fetch("/admin/users/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const el = document.getElementById("createUserResult");
      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : await res.text();
      if (el) el.textContent = typeof body === "string" ? body : JSON.stringify(body);
      const data2 = await fetchJSON("/admin/users/list");
      renderUsers(data2 && data2.users);
    });
  }
});
