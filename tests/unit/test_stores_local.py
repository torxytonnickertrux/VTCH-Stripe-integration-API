import importlib
from types import SimpleNamespace
import pytest

@pytest.mark.unit
def test_stores_page_local_only(app_module):
    c = app_module.app.test_client()
    r = c.get("/stores", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    assert "Gerenciamento de Lojas" in r.get_data(as_text=True)
    r = c.get("/stores", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403

@pytest.mark.unit
def test_stores_list_and_detail_flow(app_module, client):
    client.post("/api/v1/auth/register", json={"email":"m@example.com","password":"secret"})
    r = client.post("/api/v1/auth/login", json={"email":"m@example.com","password":"secret"})
    access = r.get_json()["access_token"]
    app_module.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_m1")
    client.post("/api/v1/create-connect-account", json={"email":"m@example.com","storeDomain":"https://loja.com"}, headers={"Authorization": f"Bearer {access}"})
    c = app_module.app.test_client()
    r = c.get("/stores/list", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert any(s["accountId"] == "acct_m1" for s in data["stores"])
    r = c.get("/stores/acct_m1", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    assert "Detalhes da Loja" in r.get_data(as_text=True)
