import os
import sys
import importlib
import pytest
from pathlib import Path

@pytest.fixture(scope="function")
def app_module(tmp_path_factory, monkeypatch):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    monkeypatch.setenv("DOMAIN", "http://localhost:4242")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setenv("PLATFORM_PRICE_ID", "price_test_platform")
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    import core.config
    importlib.reload(core.config)
    import server
    importlib.reload(server)
    return server

@pytest.fixture()
def app(app_module):
    return app_module.app

@pytest.fixture()
def client(app):
    return app.test_client()
