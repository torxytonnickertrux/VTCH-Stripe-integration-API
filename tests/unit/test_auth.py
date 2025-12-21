import json
import pytest

@pytest.mark.unit
def test_register_and_login_flow(client):
    r = client.post("/api/v1/auth/register", json={"email": "u@example.com", "password": "secret"})
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "secret"})
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data and "refresh_token" in data
    refresh = data["refresh_token"]
    r = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 200
    assert "access_token" in r.get_json()
