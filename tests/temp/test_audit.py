import json
from types import SimpleNamespace
import pytest

def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}

@pytest.mark.temp
def test_webhook_audit_persists_payload(app_module, client):
    def ok_verify(payload, sig, secret):
        return {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {"object": {"status": "complete", "metadata": {"orderId": "ORD_123"}}},
        }
    app_module.verify_webhook = ok_verify
    r = client.post("/webhook", data=b"{}")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "success"
    db = app_module.SessionLocal()
    try:
        log = db.query(app_module.WebhookLog).filter_by(event_id="evt_test_123").first()
        assert log is not None
        assert log.event_type == "checkout.session.completed"
        payload = json.loads(log.payload)
        assert payload["id"] == "evt_test_123"
    finally:
        db.close()

@pytest.mark.temp
def test_checkout_session_status_endpoint(app_module, client):
    client.post("/api/v1/auth/register", json={"email": "s@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "s@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    def fake_retrieve(session_id, stripe_account=None):
        return SimpleNamespace(
            id=session_id,
            status="complete",
            payment_status="paid",
            mode="payment",
            amount_total=9900,
            currency="brl",
        )
    app_module.stripe.checkout.Session.retrieve = fake_retrieve
    r = client.get(
        "/api/v1/checkout-session/cs_test_123",
        headers=auth_headers(access),
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["id"] == "cs_test_123"
    assert body["status"] == "complete"
    assert body["payment_status"] == "paid"
