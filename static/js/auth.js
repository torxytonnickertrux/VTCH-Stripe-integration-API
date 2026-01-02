const state = { access: "", refresh: "" };
function setTokens(access, refresh) {
  state.access = access || "";
  state.refresh = refresh || "";
  if (state.access) localStorage.setItem("access_token", state.access);
  if (state.refresh) localStorage.setItem("refresh_token", state.refresh);
  const el = document.getElementById("loginStatus");
  if (el) el.textContent = state.access ? "Logado" : "Deslogado";
}
async function apiFetch(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  const res = await fetch(path, Object.assign({}, options, { headers }));
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  return { status: res.status, body };
}
document.addEventListener("DOMContentLoaded", () => {
  const regForm = document.getElementById("registerForm");
  const loginForm = document.getElementById("loginForm");
  const regRes = document.getElementById("registerResult");
  regForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;
    const { status, body } = await apiFetch("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) });
    regRes.textContent = status === 200 ? "Registrado. Faça login." : (body?.error || "Erro");
  });
  loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;
    const { status, body } = await apiFetch("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    if (status === 200 && body?.access_token) {
      setTokens(body.access_token, body.refresh_token);
      window.location.href = "/app";
    } else {
      setTokens("", "");
      alert(body?.error || "Credenciais inválidas");
    }
  });
});

