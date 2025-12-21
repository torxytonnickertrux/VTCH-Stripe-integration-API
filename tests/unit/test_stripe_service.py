from types import SimpleNamespace
import pytest
import importlib

@pytest.mark.unit
def test_create_product_on_account(app_module, monkeypatch):
    svc = importlib.import_module("core.stripe_service")
    captured = {}
    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="prod_test")
    monkeypatch.setattr(svc.stripe.Product, "create", fake_create)
    p = svc.create_product_on_account("N", "D", "acct_1")
    assert p.id == "prod_test"
    assert captured["name"] == "N" and captured["description"] == "D" and captured["stripe_account"] == "acct_1"

@pytest.mark.unit
def test_create_price_for_product(app_module, monkeypatch):
    svc = importlib.import_module("core.stripe_service")
    calls = []
    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id="price_test")
    monkeypatch.setattr(svc.stripe.Price, "create", fake_create)
    svc.create_price_for_product("prod_x", 1234, "acct_1")
    svc.create_price_for_product("prod_x", 1234, "acct_1", "month")
    assert calls[0]["product"] == "prod_x" and calls[0]["unit_amount"] == 1234 and calls[0]["currency"] == "brl" and calls[0]["stripe_account"] == "acct_1" and "recurring" not in calls[0]
    assert calls[1]["recurring"]["interval"] == "month"

@pytest.mark.unit
def test_list_prices_with_products(app_module, monkeypatch):
    svc = importlib.import_module("core.stripe_service")
    def fake_list(**kwargs):
        return SimpleNamespace(data=[], kwargs=kwargs)
    monkeypatch.setattr(svc.stripe.Price, "list", fake_list)
    r1 = svc.list_prices_with_products("platform")
    r2 = svc.list_prices_with_products("acct_1")
    assert r1.kwargs["expand"] == ["data.product"] and r1.kwargs["active"] and r1.kwargs["limit"] == 100 and "stripe_account" not in r1.kwargs
    assert r2.kwargs["stripe_account"] == "acct_1"

@pytest.mark.unit
def test_create_checkout_sessions(app_module, monkeypatch):
    svc = importlib.import_module("core.stripe_service")
    calls = []
    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(url="https://checkout.example")
    monkeypatch.setattr(svc.stripe.checkout.Session, "create", fake_create)
    s1 = svc.create_checkout_session_platform("acct_x", "price_y", "https://s", "https://c")
    assert s1.url and calls[0]["mode"] == "subscription" and calls[0]["line_items"][0]["price"] == "price_y" and calls[0]["customer_account"] == "acct_x"
    s2 = svc.create_checkout_session_connected("acct_1", "price_y", "payment", "https://s", "https://c", 100)
    s3 = svc.create_checkout_session_connected("acct_1", "price_y", "subscription", "https://s", "https://c", 200)
    assert s2.url and calls[1]["stripe_account"] == "acct_1" and "payment_intent_data" in calls[1] and calls[1]["payment_intent_data"]["application_fee_amount"] == 100
    assert s3.url and calls[2]["stripe_account"] == "acct_1" and "subscription_data" in calls[2] and calls[2]["subscription_data"]["application_fee_amount"] == 200

@pytest.mark.unit
def test_retrieve_price(app_module, monkeypatch):
    svc = importlib.import_module("core.stripe_service")
    def fake_retrieve(pid, stripe_account=None):
        return SimpleNamespace(id=pid, sa=stripe_account)
    monkeypatch.setattr(svc.stripe.Price, "retrieve", fake_retrieve)
    r = svc.retrieve_price("price_x", "acct_1")
    assert r.id == "price_x" and r.sa == "acct_1"

@pytest.mark.unit
def test_verify_webhook(app_module, monkeypatch):
    svc = importlib.import_module("core.stripe_service")
    def fake_construct(payload, sig, secret):
        return {"id":"evt_x","type":"t"}
    monkeypatch.setattr(svc.stripe.Webhook, "construct_event", fake_construct)
    evt = svc.verify_webhook(b"{}", "sig", "sec")
    assert evt["id"] == "evt_x"
