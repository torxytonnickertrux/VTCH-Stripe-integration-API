from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.config import Config

def init_limiter(app):
    storage_uri = getattr(Config, "LIMITER_STORAGE_URL", "") or None
    limiter = Limiter(
        app=app,
        key_func=lambda: getattr(app, "rate_limit_identity", None) or get_remote_address(),
        default_limits=[Config.RATE_LIMIT_DEFAULT],
        storage_uri=storage_uri,
    )
    return limiter
