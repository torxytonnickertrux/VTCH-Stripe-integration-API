from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, UniqueConstraint, DateTime, Text, inspect, text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
from core.config import Config

engine = create_engine(Config.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    stripe_accounts = relationship("StripeAccount", back_populates="user")

class StripeAccount(Base):
    __tablename__ = "stripe_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(String(255), unique=True, nullable=False)
    store_domain = Column(String(512), nullable=True)
    user = relationship("User", back_populates="stripe_accounts")

class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    subscription_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    order_id = Column(String(255), nullable=True)
    account_id = Column(String(255), nullable=True)
    status = Column(String(64), nullable=True)
    source = Column(String(32), nullable=True)
    processed_at = Column(DateTime, nullable=True)

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False)
    event_type = Column(String(255), nullable=False)
    payload = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class StoreDispatch(Base):
    __tablename__ = "store_dispatch"
    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False)
    account_id = Column(String(255), nullable=False)
    order_id = Column(String(255), nullable=True)
    status = Column(String(64), nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    delivered_at = Column(DateTime, nullable=True)

class OrderCorrelation(Base):
    __tablename__ = "order_correlation"
    id = Column(Integer, primary_key=True)
    order_id = Column(String(255), unique=True, nullable=False)
    account_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class WebhookSyncLog(Base):
    __tablename__ = "webhook_sync_logs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    account_id = Column(String(255), nullable=True)
    recovered_events = Column(Integer, default=0, nullable=False)
    ignored_events = Column(Integer, default=0, nullable=False)
    failed_notifications = Column(Integer, default=0, nullable=False)
    message = Column(Text, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        inspector = inspect(engine)
        # add is_admin to users if missing
        ucols = [c["name"] for c in inspector.get_columns("users")]
        if "is_admin" not in ucols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
        cols = [c["name"] for c in inspector.get_columns("stripe_accounts")]
        if "store_domain" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE stripe_accounts ADD COLUMN store_domain VARCHAR(512)"))
        # ensure order_correlation exists
        tables = inspector.get_table_names()
        if "order_correlation" not in tables:
            with engine.begin() as conn:
                conn.execute(text("CREATE TABLE order_correlation (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id VARCHAR(255) UNIQUE NOT NULL, account_id VARCHAR(255) NOT NULL, created_at DATETIME NOT NULL)"))
        # alter webhook_events to include auditing columns if missing
        wcols = [c["name"] for c in inspector.get_columns("webhook_events")]
        with engine.begin() as conn:
            if "order_id" not in wcols:
                conn.execute(text("ALTER TABLE webhook_events ADD COLUMN order_id VARCHAR(255)"))
            if "account_id" not in wcols:
                conn.execute(text("ALTER TABLE webhook_events ADD COLUMN account_id VARCHAR(255)"))
            if "status" not in wcols:
                conn.execute(text("ALTER TABLE webhook_events ADD COLUMN status VARCHAR(64)"))
            if "source" not in wcols:
                conn.execute(text("ALTER TABLE webhook_events ADD COLUMN source VARCHAR(32)"))
            if "processed_at" not in wcols:
                conn.execute(text("ALTER TABLE webhook_events ADD COLUMN processed_at DATETIME"))
    except Exception:
        pass
