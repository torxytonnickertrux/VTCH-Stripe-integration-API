import importlib
import pytest

@pytest.mark.unit
def test_docs_public_default(app_module):
    client = app_module.app.test_client()
    r = client.get("/docs")
    assert r.status_code == 200
    assert "Documentação Interativa" in r.get_data(as_text=True)

@pytest.mark.unit
def test_docs_private_requires_auth(monkeypatch):
    monkeypatch.setenv("DOCS_PUBLIC", "0")
    cfg = importlib.import_module("core.config")
    importlib.reload(cfg)
    server = importlib.import_module("server")
    importlib.reload(server)
    client = server.app.test_client()
    r = client.get("/docs")
    assert r.status_code == 401
    r = client.post("/api/v1/auth/register", json={"email": "docs@example.com", "password": "secret"})
    r = client.post("/api/v1/auth/login", json={"email": "docs@example.com", "password": "secret"})
    access = r.get_json()["access_token"]
    r = client.get("/docs", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
