import re
from urllib.parse import urlparse
from core.config import Config

def _is_url(v):
    try:
        p = urlparse(v or "")
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def _has(v):
    return bool(v)

def _rate_valid(v):
    return isinstance(v, str) and "/" in v

def audit_config():
    items = []
    items.append({
        "group": "Geral",
        "key": "DOMAIN",
        "value": Config.DOMAIN,
        "masked": False,
        "required": True,
        "ok": _is_url(Config.DOMAIN),
        "message": "" if _is_url(Config.DOMAIN) else "URL inválida"
    })
    items.append({
        "group": "Geral",
        "key": "API_VERSION",
        "value": Config.API_VERSION,
        "masked": False,
        "required": True,
        "ok": bool(Config.API_VERSION),
        "message": "" if Config.API_VERSION else "Obrigatório"
    })
    items.append({
        "group": "Geral",
        "key": "DOCS_PUBLIC",
        "value": Config.DOCS_PUBLIC,
        "masked": False,
        "required": False,
        "ok": True,
        "message": ""
    })
    items.append({
        "group": "JWT",
        "key": "JWT_SECRET",
        "value": "***" if _has(Config.JWT_SECRET) else "",
        "masked": True,
        "required": True,
        "ok": _has(Config.JWT_SECRET) and Config.JWT_SECRET != "change-me",
        "message": "" if (_has(Config.JWT_SECRET) and Config.JWT_SECRET != "change-me") else "Defina um segredo forte"
    })
    items.append({
        "group": "JWT",
        "key": "JWT_ALG",
        "value": Config.JWT_ALG,
        "masked": False,
        "required": True,
        "ok": bool(Config.JWT_ALG),
        "message": "" if Config.JWT_ALG else "Obrigatório"
    })
    items.append({
        "group": "JWT",
        "key": "JWT_ACCESS_TTL_SECONDS",
        "value": Config.JWT_ACCESS_TTL_SECONDS,
        "masked": False,
        "required": True,
        "ok": isinstance(Config.JWT_ACCESS_TTL_SECONDS, int) and Config.JWT_ACCESS_TTL_SECONDS > 0,
        "message": "" if (isinstance(Config.JWT_ACCESS_TTL_SECONDS, int) and Config.JWT_ACCESS_TTL_SECONDS > 0) else "Deve ser > 0"
    })
    items.append({
        "group": "JWT",
        "key": "JWT_REFRESH_TTL_SECONDS",
        "value": Config.JWT_REFRESH_TTL_SECONDS,
        "masked": False,
        "required": True,
        "ok": isinstance(Config.JWT_REFRESH_TTL_SECONDS, int) and Config.JWT_REFRESH_TTL_SECONDS > 0,
        "message": "" if (isinstance(Config.JWT_REFRESH_TTL_SECONDS, int) and Config.JWT_REFRESH_TTL_SECONDS > 0) else "Deve ser > 0"
    })
    items.append({
        "group": "RateLimit",
        "key": "RATE_LIMIT_DEFAULT",
        "value": Config.RATE_LIMIT_DEFAULT,
        "masked": False,
        "required": True,
        "ok": _rate_valid(Config.RATE_LIMIT_DEFAULT),
        "message": "" if _rate_valid(Config.RATE_LIMIT_DEFAULT) else "Formato esperado N/unit"
    })
    items.append({
        "group": "RateLimit",
        "key": "RATE_LIMIT_LOGIN",
        "value": Config.RATE_LIMIT_LOGIN,
        "masked": False,
        "required": True,
        "ok": _rate_valid(Config.RATE_LIMIT_LOGIN),
        "message": "" if _rate_valid(Config.RATE_LIMIT_LOGIN) else "Formato esperado N/unit"
    })
    items.append({
        "group": "RateLimit",
        "key": "RATE_LIMIT_CHECKOUT",
        "value": Config.RATE_LIMIT_CHECKOUT,
        "masked": False,
        "required": True,
        "ok": _rate_valid(Config.RATE_LIMIT_CHECKOUT),
        "message": "" if _rate_valid(Config.RATE_LIMIT_CHECKOUT) else "Formato esperado N/unit"
    })
    items.append({
        "group": "RateLimit",
        "key": "RATE_LIMIT_WEBHOOK",
        "value": Config.RATE_LIMIT_WEBHOOK,
        "masked": False,
        "required": True,
        "ok": _rate_valid(Config.RATE_LIMIT_WEBHOOK),
        "message": "" if _rate_valid(Config.RATE_LIMIT_WEBHOOK) else "Formato esperado N/unit"
    })
    items.append({
        "group": "Stripe",
        "key": "STRIPE_SECRET_KEY",
        "value": "***" if _has(Config.STRIPE_SECRET_KEY) else "",
        "masked": True,
        "required": True,
        "ok": _has(Config.STRIPE_SECRET_KEY),
        "message": "" if _has(Config.STRIPE_SECRET_KEY) else "Obrigatório"
    })
    items.append({
        "group": "Stripe",
        "key": "STRIPE_WEBHOOK_SECRET",
        "value": "***" if _has(Config.STRIPE_WEBHOOK_SECRET) else "",
        "masked": True,
        "required": False,
        "ok": True if _has(Config.STRIPE_WEBHOOK_SECRET) else False,
        "message": "" if _has(Config.STRIPE_WEBHOOK_SECRET) else "Configure para validar webhooks"
    })
    items.append({
        "group": "Stripe",
        "key": "PLATFORM_PRICE_ID",
        "value": "***" if _has(Config.PLATFORM_PRICE_ID) else "",
        "masked": True,
        "required": False,
        "ok": True if _has(Config.PLATFORM_PRICE_ID) else False,
        "message": "" if _has(Config.PLATFORM_PRICE_ID) else "Necessário para assinatura de plataforma"
    })
    items.append({
        "group": "EventosPagamentos",
        "key": "PAYMENTS_EVENTS_SECRET",
        "value": "***" if _has(Config.PAYMENTS_EVENTS_SECRET) else "",
        "masked": True,
        "required": False,
        "ok": True if _has(Config.PAYMENTS_EVENTS_SECRET) else False,
        "message": "" if _has(Config.PAYMENTS_EVENTS_SECRET) else "Configurar para HMAC de eventos"
    })
    items.append({
        "group": "EventosPagamentos",
        "key": "PAYMENTS_EVENTS_PATH",
        "value": Config.PAYMENTS_EVENTS_PATH,
        "masked": False,
        "required": False,
        "ok": bool(Config.PAYMENTS_EVENTS_PATH),
        "message": "" if Config.PAYMENTS_EVENTS_PATH else "Obrigatório se usar HMAC"
    })
    items.append({
        "group": "EventosPagamentos",
        "key": "PAYMENTS_EVENTS_HEADER",
        "value": Config.PAYMENTS_EVENTS_HEADER,
        "masked": False,
        "required": False,
        "ok": bool(Config.PAYMENTS_EVENTS_HEADER),
        "message": "" if Config.PAYMENTS_EVENTS_HEADER else "Obrigatório se usar HMAC"
    })
    items.append({
        "group": "BancoDeDados",
        "key": "DATABASE_URL",
        "value": Config.DATABASE_URL,
        "masked": False,
        "required": True,
        "ok": bool(Config.DATABASE_URL),
        "message": "" if Config.DATABASE_URL else "Não resolvida"
    })
    mysql_required = (Config.DB_DIALECT or "").lower() == "mysql" or bool(Config.MYSQL_HOST)
    items.append({
        "group": "BancoDeDados",
        "key": "DB_DIALECT",
        "value": Config.DB_DIALECT,
        "masked": False,
        "required": False,
        "ok": True,
        "message": ""
    })
    items.append({
        "group": "BancoDeDados",
        "key": "MYSQL_HOST",
        "value": Config.MYSQL_HOST,
        "masked": False,
        "required": mysql_required,
        "ok": (not mysql_required) or bool(Config.MYSQL_HOST),
        "message": "" if ((not mysql_required) or bool(Config.MYSQL_HOST)) else "Obrigatório para MySQL"
    })
    items.append({
        "group": "BancoDeDados",
        "key": "MYSQL_DB",
        "value": Config.MYSQL_DB,
        "masked": False,
        "required": mysql_required,
        "ok": (not mysql_required) or bool(Config.MYSQL_DB),
        "message": "" if ((not mysql_required) or bool(Config.MYSQL_DB)) else "Obrigatório para MySQL"
    })
    items.append({
        "group": "BancoDeDados",
        "key": "MYSQL_USER",
        "value": Config.MYSQL_USER,
        "masked": False,
        "required": mysql_required,
        "ok": (not mysql_required) or bool(Config.MYSQL_USER),
        "message": "" if ((not mysql_required) or bool(Config.MYSQL_USER)) else "Obrigatório para MySQL"
    })
    return {"items": items}
