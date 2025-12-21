import json
from types import SimpleNamespace
import pytest

def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}

@pytest.mark.unit
def test_done_route_renders(client):
    r = client.get("/done?session_id=cs_test_123")
    assert r.status_code == 200
    assert "cs_test_123" in r.get_data(as_text=True)

@pytest.mark.unit
def test_get_checkout_session_platform_and_error(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    def fake_retrieve(session_id):
        return SimpleNamespace(id=session_id, status="complete", payment_status="paid", mode="payment", amount_total=1000, currency="brl")
    app_module.stripe.checkout.Session.retrieve = fake_retrieve
    r = client.get("/api/v1/checkout-session/cs_platform?id=ignored&accountId=platform", headers=auth_headers(access))
    assert r.status_code == 200
    body = r.get_json()
    assert body["id"] == "cs_platform"
    class E(Exception): pass
    def bad_retrieve(session_id, stripe_account=None):
        raise E("not found")
    app_module.stripe.checkout.Session.retrieve = bad_retrieve
    r = client.get("/api/v1/checkout-session/cs_missing?accountId=acct_any", headers=auth_headers(access))
    assert r.status_code == 404

@pytest.mark.unit
def test_create_account_link_paths(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.post("/api/v1/create-account-link", json={}, headers=auth_headers(access))
    assert r.status_code == 400
    def fake_accounts_create(payload): return SimpleNamespace(id="acct_user_1")
    app_module.stripe_client.v2.core.accounts.create = fake_accounts_create
    r = client.post("/api/v1/create-connect-account", json={"email":"a@example.com"}, headers=auth_headers(access))
    acct = r.get_json()["accountId"]
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.post("/api/v1/create-account-link", json={"accountId":"acct_wrong"}, headers=auth_headers(access))
    assert r.status_code == 403
    def fake_links_create(payload): return SimpleNamespace(url="https://link.example")
    app_module.stripe_client.v2.core.account_links.create = fake_links_create
    r = client.post("/api/v1/create-account-link", json={"accountId":acct}, headers=auth_headers(access))
    assert r.status_code == 200
    assert "url" in r.get_json()

@pytest.mark.unit
def test_account_status_paths(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "b@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    def fake_accounts_create(payload): return SimpleNamespace(id="acct_user_2")
    app_module.stripe_client.v2.core.accounts.create = fake_accounts_create
    r = client.post("/api/v1/create-connect-account", json={"email":"b@example.com"}, headers=auth_headers(access))
    acct = r.get_json()["accountId"]
    r = client.post("/api/v1/auth/login", json={"email": "b@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.get(f"/api/v1/account-status/{acct}x", headers=auth_headers(access))
    assert r.status_code == 403
    def fake_accounts_retrieve(account_id, opts):
        return {
            "id": account_id,
            "configuration": {"merchant": {"capabilities": {"stripe_balance": {"payouts": {"status": "active"}}, "card_payments": {"status": "active"}}}},
            "requirements": {"summary": {"minimum_deadline": {"status": None}}, "entries": []},
        }
    app_module.stripe_client.v2.core.accounts.retrieve = fake_accounts_retrieve
    r = client.get(f"/api/v1/account-status/{acct}", headers=auth_headers(access))
    assert r.status_code == 200
    body = r.get_json()
    assert body["payoutsEnabled"] and body["chargesEnabled"] and body["detailsSubmitted"]

@pytest.mark.unit
def test_get_products_paths(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "d@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "d@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    def fake_accounts_create(payload): return SimpleNamespace(id="acct_user_3")
    app_module.stripe_client.v2.core.accounts.create = fake_accounts_create
    r = client.post("/api/v1/create-connect-account", json={"email":"d@example.com"}, headers=auth_headers(access))
    acct = r.get_json()["accountId"]
    r = client.post("/api/v1/auth/login", json={"email": "d@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.get(f"/api/v1/products/{acct}x", headers=auth_headers(access))
    assert r.status_code == 403
    class P:
        def __init__(self): self.data = [SimpleNamespace(product=SimpleNamespace(id="prod1", name="N", description="D"), unit_amount=1234, id="price1")]
    app_module.list_prices_with_products = lambda account_id: P()
    r = client.get(f"/api/v1/products/{acct}", headers=auth_headers(access))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list) and r.get_json()[0]["priceId"] == "price1"

@pytest.mark.unit
def test_create_product_paths(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "e@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "e@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.post("/api/v1/create-product", json={}, headers=auth_headers(access))
    assert r.status_code == 400
    def fake_accounts_create(payload): return SimpleNamespace(id="acct_user_4")
    app_module.stripe_client.v2.core.accounts.create = fake_accounts_create
    r = client.post("/api/v1/create-connect-account", json={"email":"e@example.com"}, headers=auth_headers(access))
    acct = r.get_json()["accountId"]
    r = client.post("/api/v1/auth/login", json={"email": "e@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.post("/api/v1/create-product", json={"productName":"A","productDescription":"B","productPrice":1000,"accountId":"acct_wrong"}, headers=auth_headers(access))
    assert r.status_code == 403
    class Product: 
        def __init__(self, id): self.id = id
    class Price:
        def __init__(self, id): self.id = id
    app_module.create_product_on_account = lambda n,d,a: Product("prod_x")
    app_module.create_price_for_product = lambda pid,amt,acc,intv: Price("price_x")
    r = client.post("/api/v1/create-product", json={"productName":"A","productDescription":"B","productPrice":1000,"accountId":acct,"recurringInterval":""}, headers=auth_headers(access))
    assert r.status_code == 200
    assert r.get_json()["priceId"] == "price_x"

@pytest.mark.unit
def test_create_portal_session_redirect(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "g@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "g@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    app_module.stripe.checkout.Session.retrieve = lambda sid: SimpleNamespace(customer_account="acct_ca")
    app_module.stripe.billing_portal.Session.create = lambda **kwargs: SimpleNamespace(url="https://portal.example")
    r = client.post("/api/v1/create-portal-session", json={"session_id":"cs_test"}, headers=auth_headers(access))
    assert r.status_code == 303
    assert r.headers.get("Location")

@pytest.mark.unit
def test_checkout_session_uses_store_urls(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "h@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "h@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    app_module.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_user_5")
    r = client.post("/api/v1/create-connect-account", json={"email":"h@example.com","storeDomain":"https://loja.com"}, headers=auth_headers(access))
    acct = r.get_json()["accountId"]
    r = client.post("/api/v1/auth/login", json={"email": "h@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    class PriceObj:
        def __init__(self, type_): self.type = type_
    app_module.retrieve_price = lambda pid, acc: PriceObj("recurring")
    captured = {}
    def fake_create_session(account_id, price_id, mode, success_url, cancel_url, fee_amount):
        captured.update({"success_url": success_url, "cancel_url": cancel_url})
        return SimpleNamespace(url="https://checkout.stripe.com/test_session")
    app_module.create_checkout_session_connected = fake_create_session
    r = client.post("/api/v1/create-checkout-session", json={
        "accountId": acct,
        "priceId": "price_abc",
        "successUrl": "https://loja.com/ok",
        "cancelUrl": "https://loja.com/cancel"
    }, headers=auth_headers(access))
    assert r.status_code == 303
    assert captured["success_url"] == "https://loja.com/ok"
    assert captured["cancel_url"] == "https://loja.com/cancel"

@pytest.mark.unit
def test_subscribe_platform_uses_store_urls(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "i@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "i@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    captured = {}
    def fake_platform_session(account_id, price_id, success_url, cancel_url):
        captured.update({"success_url": success_url, "cancel_url": cancel_url})
        return SimpleNamespace(url="https://checkout.stripe.com/platform_session")
    app_module.create_checkout_session_platform = fake_platform_session
    client.post("/api/v1/auth/register", json={"email": "j@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "j@example.com", "password": "secret"})
    access2 = r.get_json()["access_token"]
    app_module.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_platform")
    r = client.post("/api/v1/create-connect-account", json={"email":"j@example.com","storeDomain":"https://loja.com"}, headers=auth_headers(access2))
    r = client.post("/api/v1/auth/login", json={"email": "j@example.com", "password": "secret"})
    access2 = r.get_json()["access_token"]
    r = client.post("/api/v1/subscribe-to-platform", json={
        "accountId": "acct_platform"
    }, headers=auth_headers(access2))
    assert r.status_code == 200
    assert captured["success_url"].startswith("https://loja.com/checkout/success")
    assert captured["cancel_url"] == "https://loja.com/checkout/cancel"
@pytest.mark.unit
def test_webhook_event_types_and_idempotency(app_module, client):
    evt = {"id":"evt1","type":"checkout.session.completed","data":{"object":{"status":"complete"}}}
    app_module.verify_webhook = lambda payload,sig,sec: evt
    r = client.post("/webhook", data=b"{}")
    assert r.status_code == 200
    r = client.post("/webhook", data=b"{}")
    assert r.status_code == 200
    assert r.get_json().get("status") in ("success","duplicate")
    for t in ["customer.subscription.trial_will_end","customer.subscription.deleted","checkout.session.async_payment_failed","payment_intent.succeeded"]:
        evt["id"] = "evt_"+t
        evt["type"] = t
        r = client.post("/webhook", data=b"{}")
        assert r.status_code == 200

@pytest.mark.unit
def test_auth_errors_and_refresh(app_module, client):
    r = client.post("/api/v1/auth/login", json={"email": "no@example.com", "password": "bad"})
    assert r.status_code == 401
    client.post("/api/v1/auth/register", json={"email": "z@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/register", json={"email": "z@example.com", "password": "secret"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/login", json={"email": "z@example.com", "password": "secret"})
    tokens = r.get_json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]
    r = client.post("/api/v1/auth/refresh", headers={"Authorization":"bad header"})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 200
    assert "access_token" in r.get_json()
