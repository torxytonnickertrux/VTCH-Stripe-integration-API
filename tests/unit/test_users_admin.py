from types import SimpleNamespace
import pytest
import importlib

@pytest.mark.unit
def test_admin_users_local_only(app_module):
    c = app_module.app.test_client()
    r = c.get("/users", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    assert "Usuários" in r.get_data(as_text=True)
    r = c.get("/users", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403

@pytest.mark.unit
def test_admin_create_user_and_store(app_module, client):
    c = app_module.app.test_client()
    r = c.post("/admin/users/create", json={"email":"admin_create@example.com","password":"secret"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    uid = r.get_json()["id"]
    app_module.stripe_client.v2.core.accounts.create = lambda payload: SimpleNamespace(id="acct_admin_1")
    r = c.post(f"/admin/users/{uid}/stores/create", json={"email":"seller@example.com","storeDomain":"https://loja.com"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    r = c.get(f"/admin/users/{uid}/stores", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    stores = r.get_json()["stores"]
    assert any(s["accountId"] == "acct_admin_1" for s in stores)
