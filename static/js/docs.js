const state = { accessToken: "" };

function setToken(t) {
  state.accessToken = t || "";
  const el = document.getElementById("tokenStatus");
  if (el) el.textContent = state.accessToken ? "Token definido" : "Token vazio";
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (state.accessToken) headers["Authorization"] = "Bearer " + state.accessToken;
  const res = await fetch(path, Object.assign({}, options, { headers }));
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  return { status: res.status, body };
}

document.addEventListener("DOMContentLoaded", () => {
  const tokenForm = document.getElementById("tokenForm");
  if (tokenForm) {
    tokenForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const t = document.getElementById("accessTokenInput").value.trim();
      setToken(t);
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
      const el = document.getElementById("loginResult");
      if (el) {
        if (r.status === 200 && r.body && r.body.access_token) {
          setToken(r.body.access_token);
          el.textContent = "Login efetuado. Token definido.";
        } else {
          el.textContent = "Falha no login";
        }
      }
    });
  }

  const createConnectAccountForm = document.getElementById("createConnectAccountForm");
  if (createConnectAccountForm) {
    createConnectAccountForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("connectEmail").value.trim();
      const storeDomain = document.getElementById("connectStoreDomain").value.trim();
      const r = await apiFetch("/api/v1/create-connect-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, storeDomain }),
      });
      const el = document.getElementById("connectResult");
      if (el) el.textContent = JSON.stringify(r.body);
    });
  }

  const createAccountLinkForm = document.getElementById("createAccountLinkForm");
  if (createAccountLinkForm) {
    createAccountLinkForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accountId = document.getElementById("accountIdForLink").value.trim();
      const r = await apiFetch("/api/v1/create-account-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId }),
      });
      const el = document.getElementById("connectResult");
      if (el) el.textContent = JSON.stringify(r.body);
    });
  }

  const accountStatusForm = document.getElementById("accountStatusForm");
  if (accountStatusForm) {
    accountStatusForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accountId = document.getElementById("accountIdForStatus").value.trim();
      const r = await apiFetch("/api/v1/account-status/" + encodeURIComponent(accountId));
      const el = document.getElementById("connectResult");
      if (el) el.textContent = JSON.stringify(r.body);
    });
  }

  const createProductForm = document.getElementById("createProductForm");
  if (createProductForm) {
    createProductForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const productName = document.getElementById("productName").value.trim();
      const productDescription = document.getElementById("productDescription").value.trim();
      const productPrice = parseInt(document.getElementById("productPrice").value, 10);
      const accountId = document.getElementById("accountIdForProduct").value.trim();
      const recurringInterval = document.getElementById("recurringInterval").value || null;
      const r = await apiFetch("/api/v1/create-product", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ productName, productDescription, productPrice, accountId, recurringInterval }),
      });
      const el = document.getElementById("productsResult");
      if (el) el.textContent = JSON.stringify(r.body);
    });
  }

  const listProductsForm = document.getElementById("listProductsForm");
  if (listProductsForm) {
    listProductsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accountId = document.getElementById("accountIdForList").value.trim();
      const r = await apiFetch("/api/v1/products/" + encodeURIComponent(accountId));
      const el = document.getElementById("productsResult");
      if (el) el.textContent = JSON.stringify(r.body);
    });
  }

  const checkoutSessionForm = document.getElementById("checkoutSessionForm");
  if (checkoutSessionForm) {
    checkoutSessionForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accountId = document.getElementById("accountIdForCheckout").value.trim();
      const priceId = document.getElementById("priceIdForCheckout").value.trim();
      const successUrl = document.getElementById("successUrlForCheckout").value.trim();
      const cancelUrl = document.getElementById("cancelUrlForCheckout").value.trim();
      const r = await apiFetch("/api/v1/create-checkout-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId, priceId, successUrl, cancelUrl }),
        redirect: "manual",
      });
      const el = document.getElementById("productsResult");
      if (el) el.textContent = JSON.stringify(r.body);
      if (r.status === 200 && r.body && r.body.url) {
        window.location.href = r.body.url;
      }
    });
  }

  const subscribePlatformForm = document.getElementById("subscribePlatformForm");
  if (subscribePlatformForm) {
    subscribePlatformForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accountId = document.getElementById("accountIdForPlatform").value.trim();
      const successUrl = document.getElementById("successUrlForPlatform").value.trim();
      const cancelUrl = document.getElementById("cancelUrlForPlatform").value.trim();
      const r = await apiFetch("/api/v1/subscribe-to-platform", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId, successUrl, cancelUrl }),
      });
      const el = document.getElementById("productsResult");
      if (el) el.textContent = JSON.stringify(r.body);
      if (r.status === 200 && r.body && r.body.url) {
        window.location.href = r.body.url;
      }
    });
  }

  function curlPostJson(path, bodyObj) {
    const body = JSON.stringify(bodyObj || {});
    const auth = state.accessToken ? ` -H "Authorization: Bearer ${state.accessToken}"` : "";
    return `curl -X POST -H "Content-Type: application/json"${auth} -d '${body}' ${window.location.origin}${path}`;
  }
  function curlGet(path) {
    const auth = state.accessToken ? ` -H "Authorization: Bearer ${state.accessToken}"` : "";
    return `curl -X GET${auth} ${window.location.origin}${path}`;
  }

  function bind(id, fn) {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  }
  bind("curlCreateConnect", () => {
    const out = document.getElementById("curlCreateConnectOut");
    if (out) out.textContent = curlPostJson("/api/v1/create-connect-account", { email: "seller@example.com" });
  });
  bind("curlCreateAccountLink", () => {
    const out = document.getElementById("curlCreateAccountLinkOut");
    if (out) out.textContent = curlPostJson("/api/v1/create-account-link", { accountId: "acct_123" });
  });
  bind("curlAccountStatus", () => {
    const out = document.getElementById("curlAccountStatusOut");
    if (out) out.textContent = curlGet("/api/v1/account-status/acct_123");
  });
  bind("curlCreateProduct", () => {
    const out = document.getElementById("curlCreateProductOut");
    if (out) out.textContent = curlPostJson("/api/v1/create-product", {
      productName: "Serviço Pro",
      productDescription: "Plano profissional",
      productPrice: 9900,
      accountId: "acct_123",
      recurringInterval: "month"
    });
  });
  bind("curlListProducts", () => {
    const out = document.getElementById("curlListProductsOut");
    if (out) out.textContent = curlGet("/api/v1/products/acct_123");
  });
  bind("curlCreateCheckout", () => {
    const out = document.getElementById("curlCreateCheckoutOut");
    if (out) out.textContent = curlPostJson("/api/v1/create-checkout-session", {
      accountId: "acct_123",
      priceId: "price_abc"
    });
  });
  bind("curlSubscribePlatform", () => {
    const out = document.getElementById("curlSubscribePlatformOut");
    if (out) out.textContent = curlPostJson("/api/v1/subscribe-to-platform", { accountId: "acct_123" });
  });
});
