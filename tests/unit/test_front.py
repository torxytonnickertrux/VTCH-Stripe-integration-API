import pytest

@pytest.mark.unit
def test_home_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "VTCH stripe integration API" in body
    assert "Infra de Pagamentos" in body

@pytest.mark.unit
def test_docs_renders(client):
    r = client.get("/docs")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Documentação Interativa" in body
    assert "/api/v1/auth/login" in body

@pytest.mark.unit
def test_config_page_local_only(app_module):
    c = app_module.app.test_client()
    r = c.get("/config", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    assert "Configuração Local" in r.get_data(as_text=True)
    r = c.get("/config", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403

@pytest.mark.unit
def test_health_and_status_json(app_module, client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "online"
    r = client.get("/status")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "online"
    assert "uptime_seconds" in body
    assert body["version"] == app_module.Config.API_VERSION

@pytest.mark.unit
def test_health_rate_limit_exempt(client):
    for _ in range(20):
        r = client.get("/health")
        assert r.status_code == 200

@pytest.mark.unit
def test_static_assets_accessible(client):
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/hero-animation.js").status_code == 200
    assert client.get("/static/js/home-ui.js").status_code == 200

@pytest.mark.unit
def test_debug_routes_contains_core_routes(client):
    r = client.get("/debug/routes")
    assert r.status_code == 200
    data = r.get_json()
    joined = "\n".join(data)
    assert "/" in joined and "/docs" in joined and "/health" in joined and "/status" in joined
