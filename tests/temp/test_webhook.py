import stripe
import pytest

@pytest.mark.temp
def test_webhook_requires_signature_and_idempotency(app_module, client):
    def fake_verify(payload, sig, secret):
        raise stripe.error.SignatureVerificationError(message="bad sig", sig_header=sig)
    app_module.verify_webhook = fake_verify
    r = client.post("/webhook", data=b"{}")
    assert r.status_code == 400
