from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.config import Config

def init_limiter(app):
    limiter = Limiter(
        app=app,
        key_func=lambda: getattr(app, "rate_limit_identity", None) or get_remote_address(),
        default_limits=[Config.RATE_LIMIT_DEFAULT],
    )
    return limiter
