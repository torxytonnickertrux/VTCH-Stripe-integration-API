from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, UniqueConstraint, DateTime, Text, inspect, text
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

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False)
    event_type = Column(String(255), nullable=False)
    payload = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        inspector = inspect(engine)
        cols = [c["name"] for c in inspector.get_columns("stripe_accounts")]
        if "store_domain" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE stripe_accounts ADD COLUMN store_domain VARCHAR(512)"))
    except Exception:
        pass
