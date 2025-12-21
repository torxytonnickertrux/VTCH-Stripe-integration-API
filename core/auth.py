import time
from functools import wraps
from flask import request, jsonify, g, current_app
import jwt
from core.config import Config

def generate_access_token(sub, extra=None):
    payload = {"sub": sub, "exp": int(time.time()) + Config.JWT_ACCESS_TTL_SECONDS}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALG)

def generate_refresh_token(sub, extra=None):
    payload = {"sub": sub, "exp": int(time.time()) + Config.JWT_REFRESH_TTL_SECONDS, "type": "refresh"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALG)

def decode_token(token):
    return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALG])

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization") or ""
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "unauthorized"}), 401
        try:
            claims = decode_token(parts[1])
            g.user_id = claims.get("sub")
            g.stripe_account_id = claims.get("stripe_account_id")
            try:
                current_app.rate_limit_identity = g.user_id or None
            except Exception:
                pass
        except Exception:
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper
