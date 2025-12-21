import types
import pytest

def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}

@pytest.mark.unit
def test_checkout_validation_and_success(app_module, client):
    r = client.post("/api/v1/auth/register", json={"email": "c@example.com", "password": "secret"})
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"email": "c@example.com", "password": "secret"})
    tokens = r.get_json()
    access = tokens["access_token"]
    r = client.post("/api/v1/create-checkout-session", json={}, headers=auth_headers(access))
    assert r.status_code == 400
    from types import SimpleNamespace
    app_module.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_test_123")
    r = client.post("/api/v1/create-connect-account", json={"email": "c@example.com"}, headers=auth_headers(access))
    assert r.status_code == 200
    account_id = r.get_json()["accountId"]
    r = client.post("/api/v1/auth/login", json={"email": "c@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.post("/api/v1/create-checkout-session", json={"accountId": "acct_wrong", "priceId": "price_x"}, headers=auth_headers(access))
    assert r.status_code == 403
    class PriceObj:
        def __init__(self, type_): self.type = type_
    def fake_retrieve_price(price_id, account_id): return PriceObj("recurring")
    class SessionObj:
        def __init__(self, url): self.url = url
    def fake_create_session(account_id, price_id, mode, success_url, cancel_url, fee_amount):
        return SessionObj("https://checkout.stripe.com/test_session")
    app_module.retrieve_price = fake_retrieve_price
    app_module.create_checkout_session_connected = fake_create_session
    r = client.post("/api/v1/create-checkout-session", json={"accountId": account_id, "priceId": "price_x"}, headers=auth_headers(access))
    assert r.status_code == 303
    assert r.headers.get("Location")

@pytest.mark.unit
def test_subscribe_platform_requires_env_and_works(app_module, client):
    r = client.post("/api/v1/auth/register", json={"email": "p@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "p@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    class SessionObj:
        def __init__(self, url): self.url = url
    def fake_platform_session(account_id, price_id, success_url, cancel_url):
        return SessionObj("https://checkout.stripe.com/platform_session")
    app_module.create_checkout_session_platform = fake_platform_session
    r = client.post("/api/v1/subscribe-to-platform", json={"accountId": "acct_platform"}, headers=auth_headers(access))
    assert r.status_code == 200
    assert "url" in r.get_json()
