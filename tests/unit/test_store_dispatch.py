import json
from types import SimpleNamespace
import importlib
import pytest

@pytest.mark.unit
def test_dispatch_event_to_store_with_hmac(monkeypatch):
    monkeypatch.setenv("PAYMENTS_EVENTS_SECRET", "secret123")
    server = importlib.import_module("server")
    importlib.reload(server)
    server.Config.PAYMENTS_EVENTS_SECRET = "secret123"
    client = server.app.test_client()
    client.post("/api/v1/auth/register", json={"email":"k@example.com","password":"secret"})
    r = client.post("/api/v1/auth/login", json={"email":"k@example.com","password":"secret"})
    access = r.get_json()["access_token"]
    server.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_user_6")
    r = client.post("/api/v1/create-connect-account", json={"email":"k@example.com","storeDomain":"https://loja.com"}, headers={"Authorization": f"Bearer {access}"})
    evt = {"id":"evt_test_1","type":"checkout.session.completed","data":{"object":{"status":"complete","metadata":{"orderId":"ord_1"},"client_reference_id":None}},"account":"acct_user_6"}
    posted = {}
    def fake_post(url, data=None, headers=None, timeout=None):
        posted["url"] = url
        posted["data"] = data
        posted["headers"] = headers
        posted["timeout"] = timeout
        return SimpleNamespace(status_code=200)
    monkeypatch.setattr(server.requests, "post", fake_post)
    server.verify_webhook = lambda payload, sig, sec: evt
    r = client.post("/webhook", data=b"{}")
    assert r.status_code == 200
    assert posted["url"] == "https://loja.com/payments/events/"
    body = json.loads(posted["data"])
    assert body["order_id"] == "ord_1" and body["status"] == "pago"
    assert server.Config.PAYMENTS_EVENTS_HEADER in posted["headers"]

@pytest.mark.unit
def test_dispatch_idempotent(monkeypatch):
    monkeypatch.setenv("PAYMENTS_EVENTS_SECRET", "secret123")
    server = importlib.import_module("server")
    importlib.reload(server)
    server.Config.PAYMENTS_EVENTS_SECRET = "secret123"
    client = server.app.test_client()
    client.post("/api/v1/auth/register", json={"email":"l@example.com","password":"secret"})
    r = client.post("/api/v1/auth/login", json={"email":"l@example.com","password":"secret"})
    access = r.get_json()["access_token"]
    server.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_user_7")
    client.post("/api/v1/create-connect-account", json={"email":"l@example.com","storeDomain":"https://loja.com"}, headers={"Authorization": f"Bearer {access}"})
    evt = {"id":"evt_test_2","type":"checkout.session.completed","data":{"object":{"status":"complete","metadata":{"orderId":"ord_2"}}},"account":"acct_user_7"}
    calls = {"count":0}
    def fake_post(url, data=None, headers=None, timeout=None):
        calls["count"] += 1
        return SimpleNamespace(status_code=200)
    monkeypatch.setattr(server.requests, "post", fake_post)
    server.verify_webhook = lambda payload, sig, sec: evt
    r = client.post("/webhook", data=b"{}")
    assert r.status_code == 200
    r = client.post("/webhook", data=b"{}")
    assert r.status_code == 200
    assert calls["count"] == 1
