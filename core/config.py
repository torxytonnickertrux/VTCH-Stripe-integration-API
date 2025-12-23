import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY") or ""
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") or ""
    DOMAIN = os.getenv("DOMAIN") or "http://localhost:4242"
    API_VERSION = os.getenv("API_VERSION") or "v1.0.0"
    DOCS_PUBLIC = ((os.getenv("DOCS_PUBLIC") or "1").lower() not in ("0", "false", "no"))
    PAYMENTS_EVENTS_SECRET = os.getenv("PAYMENTS_EVENTS_SECRET") or ""
    PAYMENTS_EVENTS_PATH = os.getenv("PAYMENTS_EVENTS_PATH") or "/payments/events/"
    PAYMENTS_EVENTS_HEADER = os.getenv("PAYMENTS_EVENTS_HEADER") or "X-Payments-Signature"
    PLATFORM_PRICE_ID = os.getenv("PLATFORM_PRICE_ID") or ""
    JWT_SECRET = os.getenv("JWT_SECRET") or "change-me"
    JWT_ALG = "HS256"
    JWT_ACCESS_TTL_SECONDS = int(os.getenv("JWT_ACCESS_TTL_SECONDS") or "900")
    JWT_REFRESH_TTL_SECONDS = int(os.getenv("JWT_REFRESH_TTL_SECONDS") or "604800")
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT") or "100/hour"
    RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN") or "10/minute"
    RATE_LIMIT_CHECKOUT = os.getenv("RATE_LIMIT_CHECKOUT") or "30/minute"
    RATE_LIMIT_WEBHOOK = os.getenv("RATE_LIMIT_WEBHOOK") or "300/minute"
    DB_DIALECT = os.getenv("DB_DIALECT") or ""
    MYSQL_HOST = os.getenv("MYSQL_HOST") or ""
    MYSQL_PORT = int(os.getenv("MYSQL_PORT") or "3306")
    MYSQL_DB = os.getenv("MYSQL_DB") or ""
    MYSQL_USER = os.getenv("MYSQL_USER") or ""
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD") or ""
    DATABASE_URL = ""

    @staticmethod
    def compute_database_url():
        explicit = os.getenv("DATABASE_URL")
        if explicit:
            return explicit
        if (os.getenv("DB_DIALECT") or "").lower() == "mysql" or os.getenv("MYSQL_HOST"):
            host = os.getenv("MYSQL_HOST") or "localhost"
            port = os.getenv("MYSQL_PORT") or "3306"
            db = os.getenv("MYSQL_DB") or "app"
            user = os.getenv("MYSQL_USER") or "root"
            pwd = os.getenv("MYSQL_PASSWORD") or ""
            return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"
        return "sqlite:///app.db"

Config.DATABASE_URL = Config.compute_database_url()
