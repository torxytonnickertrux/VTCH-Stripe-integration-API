import structlog
import logging
import uuid
from flask import g, request

def configure_logging():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

def bind_request_context(app):
    @app.before_request
    def assign_request_id():
        g.request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    @app.after_request
    def inject_request_id(response):
        response.headers["X-Request-Id"] = g.get("request_id") or ""
        return response
