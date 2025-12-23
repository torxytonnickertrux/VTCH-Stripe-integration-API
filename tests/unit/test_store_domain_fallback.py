from types import SimpleNamespace
import pytest
import json

def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}

@pytest.mark.unit
def test_checkout_fallback_uses_store_domain(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "sd@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "sd@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    app_module.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_sd_1")
    r = client.post("/api/v1/create-connect-account", json={"email": "sd@example.com", "storeDomain": "https://loja.com"}, headers=auth_headers(access))
    assert r.status_code == 200
    # ensure saved in DB
    db = app_module.SessionLocal()
    try:
        acc = db.query(app_module.StripeAccount).filter_by(account_id="acct_sd_1").first()
        assert acc and acc.store_domain == "https://loja.com"
    finally:
        db.close()
    # login again to refresh token context
    r = client.post("/api/v1/auth/login", json={"email": "sd@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    class PriceObj:
        def __init__(self, type_): self.type = type_
    app_module.retrieve_price = lambda price_id, account_id: PriceObj("payment")
    captured = {}
    class SessionObj:
        def __init__(self, url): self.url = url
    def fake_create_session(account_id, price_id, mode, success_url, cancel_url, fee_amount):
        captured["success_url"] = success_url
        captured["cancel_url"] = cancel_url
        return SessionObj("https://checkout.stripe.com/test_session")
    app_module.create_checkout_session_connected = fake_create_session
    r = client.post("/api/v1/create-checkout-session", json={"accountId": "acct_sd_1", "priceId": "price_x"}, headers=auth_headers(access))
    assert r.status_code == 303
    assert captured["success_url"] == "https://loja.com/checkout/success?session_id={CHECKOUT_SESSION_ID}"
    assert captured["cancel_url"] == "https://loja.com/checkout/cancel"

@pytest.mark.unit
def test_platform_subscribe_fallback_uses_store_domain(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "ps@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "ps@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    app_module.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_sd_2")
    client.post("/api/v1/create-connect-account", json={"email": "ps@example.com", "storeDomain": "https://loja.com"}, headers=auth_headers(access))
    captured = {}
    class SessionObj:
        def __init__(self, url): self.url = url
    def fake_platform_session(account_id, price_id, success_url, cancel_url):
        captured["success_url"] = success_url
        captured["cancel_url"] = cancel_url
        return SessionObj("https://checkout.stripe.com/platform_session")
    app_module.create_checkout_session_platform = fake_platform_session
    r = client.post("/api/v1/subscribe-to-platform", json={"accountId": "acct_sd_2"}, headers=auth_headers(access))
    assert r.status_code == 200
    body = r.get_json()
    assert "url" in body
    assert captured["success_url"] == "https://loja.com/checkout/success?session_id={CHECKOUT_SESSION_ID}"
    assert captured["cancel_url"] == "https://loja.com/checkout/cancel"
