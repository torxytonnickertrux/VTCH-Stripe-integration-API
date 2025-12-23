import pytest

@pytest.mark.unit
def test_admin_stores_update_not_found(app_module):
    c = app_module.app.test_client()
    r = c.post("/admin/stores/update", json={"accountId":"acct_missing","storeDomain":"https://loja.com"}, environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
    assert r.status_code == 404
    assert r.get_json()["error"] == "account_not_found"

@pytest.mark.unit
def test_admin_stores_upsert_create_and_update(app_module, client):
    c = app_module.app.test_client()
    # create a user
    r = c.post("/admin/users/create", json={"email":"crud@example.com","password":"secret"}, environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
    assert r.status_code == 200
    uid = r.get_json()["id"]
    # upsert create
    r = c.post("/admin/stores/upsert", json={"userId":uid,"accountId":"acct_crud_1","storeDomain":"https://loja.com"}, environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
    assert r.status_code == 200
    assert r.get_json()["status"] in ("created","updated")
    # update
    r = c.post("/admin/stores/update", json={"accountId":"acct_crud_1","storeDomain":"https://loja2.com"}, environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
    assert r.status_code == 200
    # delete
    r = c.delete("/admin/stores/delete/acct_crud_1", environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
    assert r.status_code == 200
