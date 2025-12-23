const state = { access: "", refresh: "" };
function setTokens(access, refresh) {
  state.access = access || "";
  state.refresh = refresh || "";
  const el = document.getElementById("loginStatus");
  if (el) el.textContent = state.access ? "Logado" : "Deslogado";
}
async function apiFetch(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (state.access) headers["Authorization"] = "Bearer " + state.access;
  const res = await fetch(path, Object.assign({}, options, { headers }));
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  return { status: res.status, body };
}
document.addEventListener("DOMContentLoaded", () => {
  const regForm = document.getElementById("registerForm");
  if (regForm) {
    regForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("regEmail").value.trim();
      const password = document.getElementById("regPassword").value.trim();
      const r = await apiFetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const el = document.getElementById("registerResult");
      if (el) el.textContent = typeof r.body === "string" ? r.body : JSON.stringify(r.body);
    });
  }
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("loginEmail").value.trim();
      const password = document.getElementById("loginPassword").value.trim();
      const r = await apiFetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (r.status === 200 && r.body && r.body.access_token) {
        setTokens(r.body.access_token, r.body.refresh_token);
      } else {
        setTokens("", "");
      }
    });
  }
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      setTokens("", "");
    });
  }
  const whoamiBtn = document.getElementById("whoamiBtn");
  if (whoamiBtn) {
    whoamiBtn.addEventListener("click", async () => {
      const r = await apiFetch("/api/v1/me");
      const out = document.getElementById("whoamiOut");
      if (out) out.textContent = typeof r.body === "string" ? r.body : JSON.stringify(r.body, null, 2);
    });
  }
  const createConnectForm = document.getElementById("createConnectForm");
  if (createConnectForm) {
    createConnectForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("sellerEmail").value.trim();
      const storeDomain = document.getElementById("sellerStoreDomain").value.trim();
      const r = await apiFetch("/api/v1/create-connect-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, storeDomain }),
      });
      const el = document.getElementById("createConnectResult");
      if (el) el.textContent = typeof r.body === "string" ? r.body : JSON.stringify(r.body);
    });
  }
});
