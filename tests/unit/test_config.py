import os
import importlib
import pytest

def reload_config(monkeypatch, envs):
    for k in list(os.environ.keys()):
        if k in envs:
            continue
    for k, v in envs.items():
        monkeypatch.setenv(k, v if v is not None else "")
    if "core.config" in list(importlib.sys.modules.keys()):
        importlib.reload(importlib.import_module("core.config"))
    else:
        importlib.import_module("core.config")
    return importlib.import_module("core.config").Config

@pytest.mark.unit
def test_database_url_explicit(monkeypatch):
    Config = reload_config(monkeypatch, {
        "DATABASE_URL": "postgresql://u:pw@h:5432/db",
        "DB_DIALECT": "",
        "MYSQL_HOST": "",
    })
    assert Config.DATABASE_URL == "postgresql://u:pw@h:5432/db"

@pytest.mark.unit
def test_database_url_mysql(monkeypatch):
    Config = reload_config(monkeypatch, {
        "DATABASE_URL": "",
        "DB_DIALECT": "mysql",
        "MYSQL_HOST": "db",
        "MYSQL_PORT": "3307",
        "MYSQL_DB": "appdb",
        "MYSQL_USER": "user",
        "MYSQL_PASSWORD": "pw",
    })
    assert Config.DATABASE_URL == "mysql+pymysql://user:pw@db:3307/appdb"

@pytest.mark.unit
def test_database_url_sqlite_fallback(monkeypatch):
    Config = reload_config(monkeypatch, {
        "DATABASE_URL": "",
        "DB_DIALECT": "",
        "MYSQL_HOST": "",
    })
    assert Config.DATABASE_URL == "sqlite:///app.db"

@pytest.mark.unit
def test_jwt_and_rate_limits(monkeypatch):
    Config = reload_config(monkeypatch, {
        "JWT_SECRET": "s",
        "JWT_ACCESS_TTL_SECONDS": "1200",
        "JWT_REFRESH_TTL_SECONDS": "86400",
        "RATE_LIMIT_DEFAULT": "200/hour",
        "RATE_LIMIT_LOGIN": "20/minute",
        "RATE_LIMIT_CHECKOUT": "60/minute",
        "RATE_LIMIT_WEBHOOK": "600/minute",
    })
    assert Config.JWT_SECRET == "s"
    assert Config.JWT_ALG == "HS256"
    assert Config.JWT_ACCESS_TTL_SECONDS == 1200
    assert Config.JWT_REFRESH_TTL_SECONDS == 86400
    assert Config.RATE_LIMIT_DEFAULT == "200/hour"
    assert Config.RATE_LIMIT_LOGIN == "20/minute"
    assert Config.RATE_LIMIT_CHECKOUT == "60/minute"
    assert Config.RATE_LIMIT_WEBHOOK == "600/minute"

@pytest.mark.unit
def test_api_version_and_domain_defaults(monkeypatch):
    Config = reload_config(monkeypatch, {
        "API_VERSION": "",
        "DOMAIN": "",
    })
    assert Config.API_VERSION == "v1.0.0"
    assert Config.DOMAIN == "http://localhost:4242"
