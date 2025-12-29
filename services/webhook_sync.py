import time
import json
import hmac
import hashlib
from datetime import datetime, timedelta
import stripe
import structlog
from core.config import Config
from core.db import SessionLocal, StripeAccount, WebhookEvent, WebhookLog, StoreDispatch, OrderCorrelation, WebhookSyncLog
import requests

def _now_ts_minus(minutes):
    return int((datetime.utcnow() - timedelta(minutes=minutes)).timestamp())

def _extract_order_id(event):
    obj = (event.get("data") or {}).get("object") or {}
    meta = obj.get("metadata") or {}
    return meta.get("orderId") or obj.get("client_reference_id")

def _normalize_status(obj):
    raw = obj.get("payment_status") or obj.get("status")
    if raw in ("paid", "succeeded", "completed", "complete"):
        return "paid"
    return None

def _resolve_account_id(order_id, fallback_account):
    if fallback_account:
        return fallback_account
    db = SessionLocal()
    try:
        corr = db.query(OrderCorrelation).filter_by(order_id=order_id).first()
        return corr.account_id if corr else None
    finally:
        db.close()

def _dispatch_to_store(account_id, order_id, status, event_id, logger):
    db = SessionLocal()
    try:
        acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        if not acc or not acc.store_domain or not Config.PAYMENTS_EVENTS_SECRET:
            return False
        payload = {"orderId": order_id, "status": status}
        body = json.dumps(payload, separators=(",", ":"))
        sig = hmac.new(
            Config.PAYMENTS_EVENTS_SECRET.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        ep = acc.store_domain.rstrip("/") + Config.PAYMENTS_EVENTS_PATH
        headers = {Config.PAYMENTS_EVENTS_HEADER: sig, "Content-Type": "application/json"}
        dispatch = db.query(StoreDispatch).filter_by(event_id=event_id).first()
        if not dispatch:
            dispatch = StoreDispatch(event_id=event_id, account_id=account_id, order_id=order_id, status=status, attempts=0)
            db.add(dispatch)
            db.commit()
        delays = [1, 2, 4]
        for attempt, dly in enumerate(delays, start=1):
            try:
                r = requests.post(ep, data=body, headers=headers, timeout=5)
                logger.info("webhook_sync_store_response", event_id=event_id, status_code=getattr(r, "status_code", None))
                dispatch.attempts = attempt
                if getattr(r, "status_code", 0) == 200:
                    dispatch.delivered_at = datetime.utcnow()
                    db.add(dispatch)
                    db.commit()
                    return True
            except Exception:
                logger.info("webhook_sync_retry_scheduled", event_id=event_id, attempt=attempt, delay_seconds=dly)
                dispatch.attempts = attempt
                db.add(dispatch)
                db.commit()
            time.sleep(dly)
        return False
    finally:
        db.close()

def run_sync_once():
    logger = structlog.get_logger()
    if not Config.WEBHOOK_SYNC_ENABLED:
        return
    db = SessionLocal()
    try:
        accounts = db.query(StripeAccount).all()
    finally:
        db.close()
    for acc in accounts:
        slog = WebhookSyncLog(account_id=acc.account_id, started_at=datetime.utcnow())
        rec, ign, fail = 0, 0, 0
        dbs = SessionLocal()
        try:
            dbs.add(slog)
            dbs.commit()
        finally:
            dbs.close()
        try:
            params = {
                "types": ["checkout.session.completed", "payment_intent.succeeded"],
                "created": {"gte": _now_ts_minus(Config.WEBHOOK_SYNC_LOOKBACK_MINUTES)},
                "limit": 50,
            }
            events = stripe.Event.list(**params, stripe_account=acc.account_id)
            for ev in events.auto_paging_iter():
                ev_id = ev.get("id")
                ev_type = ev.get("type")
                obj = (ev.get("data") or {}).get("object") or {}
                order_id = _extract_order_id(ev)
                status = _normalize_status(obj)
                if not order_id or not status:
                    ign += 1
                    continue
                dbx = SessionLocal()
                try:
                    exists_evt = dbx.query(WebhookEvent).filter_by(event_id=ev_id).first()
                    dispatch = dbx.query(StoreDispatch).filter_by(event_id=ev_id).first()
                finally:
                    dbx.close()
                if exists_evt and dispatch and dispatch.delivered_at:
                    ign += 1
                    continue
                dbp = SessionLocal()
                try:
                    if not exists_evt:
                        dbp.add(WebhookEvent(event_id=ev_id))
                        dbp.add(WebhookLog(event_id=ev_id, event_type=ev_type, payload=json.dumps(ev)))
                        dbp.commit()
                finally:
                    dbp.close()
                account_id = _resolve_account_id(order_id, ev.get("account"))
                if not account_id:
                    ign += 1
                    continue
                ok = _dispatch_to_store(account_id, order_id, status, ev_id, logger)
                if ok:
                    rec += 1
                else:
                    fail += 1
        except Exception as e:
            logger.warning("webhook_sync_error", account_id=acc.account_id, error=str(e))
        finally:
            dbf = SessionLocal()
            try:
                slog.finished_at = datetime.utcnow()
                slog.recovered_events = rec
                slog.ignored_events = ign
                slog.failed_notifications = fail
                dbf.add(slog)
                dbf.commit()
            finally:
                dbf.close()

def start_worker():
    if not Config.WEBHOOK_SYNC_ENABLED:
        return
    import threading
    t = threading.Thread(target=_loop, name="WebhookSyncWorker", daemon=True)
    t.start()

def _loop():
    while Config.WEBHOOK_SYNC_ENABLED:
        try:
            run_sync_once()
        finally:
            time.sleep(max(1, Config.WEBHOOK_SYNC_INTERVAL_MINUTES * 60))
