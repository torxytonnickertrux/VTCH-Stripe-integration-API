#! /usr/bin/env python3.6

import os
import json
import time
from flask import Flask, jsonify, request, redirect, make_response, g, render_template
from functools import wraps
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from core.config import Config
from core.logging import configure_logging, bind_request_context
from core.rate_limit import init_limiter
from core.auth import auth_required, generate_access_token, generate_refresh_token
from core.config_audit import audit_config
from core.http import ok, error
from core.schemas import (
    parse_and_validate,
    CreateProductSchema,
    CreateCheckoutSessionSchema,
    SubscribePlatformSchema,
    CreatePortalSessionSchema,
)
from core.db import init_db, SessionLocal, User, StripeAccount, WebhookEvent, WebhookLog, StoreDispatch
from core.stripe_service import (
    create_product_on_account,
    create_price_for_product,
    list_prices_with_products,
    create_checkout_session_platform,
    create_checkout_session_connected,
    retrieve_price,
    verify_webhook,
)
import stripe
import structlog
from stripe import StripeClient
import jwt
import hmac
import hashlib
import requests
from services.webhook_sync import run_sync_once, start_worker
from sqlalchemy import text
stripe.api_key = Config.STRIPE_SECRET_KEY
stripe_client = StripeClient(str(Config.STRIPE_SECRET_KEY))
app = Flask(__name__)
CORS(app)
configure_logging()
bind_request_context(app)
limiter = init_limiter(app)
init_db()
app.start_time = time.time()
def _mask_headers(headers):
    masked = {}
    for k, v in headers.items():
        kl = (k or "").lower()
        if kl in ("authorization", "stripe-signature", "x-payments-signature", "x_payments_signature"):
            masked[k] = "***"
        else:
            masked[k] = v
    return masked
def _collect_post_payload():
    payload = {}
    j = request.get_json(silent=True)
    if j and isinstance(j, dict):
        payload["json"] = j
    if request.form:
        payload["form"] = request.form.to_dict()
    raw = request.get_data(cache=True, as_text=True)
    if raw:
        payload["raw"] = raw[:2000]
    return payload
@app.before_request
def _log_incoming_post():
    if request.method == "POST":
        logger = structlog.get_logger()
        logger.info(
            "incoming_post",
            path=request.path,
            method=request.method,
            remote_addr=request.remote_addr,
            headers=_mask_headers(request.headers),
            body=_collect_post_payload(),
        )
def local_only(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr or ''
        if ip not in ('127.0.0.1', '::1'):
            return jsonify({'error': 'forbidden'}), 403
        return fn(*args, **kwargs)
    return wrapper
@app.route('/config', methods=['GET'])
@local_only
def config_view():
    cfg = {
        'DOMAIN': Config.DOMAIN,
        'API_VERSION': Config.API_VERSION,
        'DOCS_PUBLIC': Config.DOCS_PUBLIC,
        'RATE_LIMIT_DEFAULT': Config.RATE_LIMIT_DEFAULT,
        'RATE_LIMIT_LOGIN': Config.RATE_LIMIT_LOGIN,
        'RATE_LIMIT_CHECKOUT': Config.RATE_LIMIT_CHECKOUT,
        'RATE_LIMIT_WEBHOOK': Config.RATE_LIMIT_WEBHOOK,
        'PLATFORM_PRICE_ID': True if Config.PLATFORM_PRICE_ID else False,
        'STRIPE_WEBHOOK_SECRET': True if Config.STRIPE_WEBHOOK_SECRET else False,
        'PAYMENTS_EVENTS_SECRET': True if Config.PAYMENTS_EVENTS_SECRET else False,
        'PAYMENTS_EVENTS_PATH': Config.PAYMENTS_EVENTS_PATH,
        'PAYMENTS_EVENTS_HEADER': Config.PAYMENTS_EVENTS_HEADER,
    }
    audit = audit_config()
    return render_template('config.html', cfg=cfg, audit=audit)
@app.route('/config/audit', methods=['GET'])
@local_only
def config_audit_json():
    return jsonify(audit_config())
@app.route('/config/store', methods=['POST'])
@local_only
def config_store():
    data = parse_request_body()
    account_id = data.get('accountId')
    store_domain = data.get('storeDomain')
    if not account_id or not store_domain:
        return error('invalid_payload', 400)
    db = SessionLocal()
    try:
        acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        if not acc:
            return error('account_not_found', 404)
        acc.store_domain = store_domain
        db.add(acc)
        db.commit()
        return ok({'status': 'updated', 'accountId': account_id, 'storeDomain': store_domain})
    finally:
        db.close()
@app.route('/stores', methods=['GET'])
@local_only
def stores_view():
    return render_template('stores.html')
@app.route('/stores/list', methods=['GET'])
@local_only
def stores_list():
    db = SessionLocal()
    try:
        rows = db.query(StripeAccount, User).join(User, StripeAccount.user_id == User.id).all()
        data = []
        for acc, user in rows:
            data.append({
                'accountId': acc.account_id,
                'userId': user.id,
                'email': user.email,
                'storeDomain': acc.store_domain
            })
        return ok({'stores': data})
    finally:
        db.close()
@app.route('/stores/<account_id>', methods=['GET'])
@local_only
def store_detail_view(account_id):
    return render_template('store_detail.html', account_id=account_id)
@app.route('/stores/get/<account_id>', methods=['GET'])
@local_only
def stores_get(account_id):
    db = SessionLocal()
    try:
        acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        if not acc:
            return error('account_not_found', 404)
        user = db.query(User).filter_by(id=acc.user_id).first()
        return ok({
            'accountId': acc.account_id,
            'userId': acc.user_id,
            'email': user.email if user else None,
            'storeDomain': acc.store_domain
        })
    finally:
        db.close()
@app.route('/stores/dispatches/<account_id>', methods=['GET'])
@local_only
def stores_dispatches(account_id):
    db = SessionLocal()
    try:
        rows = db.query(StoreDispatch).filter_by(account_id=account_id).order_by(StoreDispatch.id.desc()).limit(200).all()
        data = []
        for d in rows:
            data.append({
                'eventId': d.event_id,
                'orderId': d.order_id,
                'status': d.status,
                'attempts': d.attempts,
                'deliveredAt': d.delivered_at.isoformat() if d.delivered_at else None
            })
        return ok({'dispatches': data})
    finally:
        db.close()
@app.route('/stores/webhooks/<account_id>', methods=['GET'])
@local_only
def stores_webhooks(account_id):
    db = SessionLocal()
    try:
        rows = db.query(WebhookLog).order_by(WebhookLog.id.desc()).limit(400).all()
        data = []
        for w in rows:
            try:
                ev = json.loads(w.payload)
                if ev.get('account') == account_id:
                    data.append({
                        'eventId': ev.get('id'),
                        'type': ev.get('type'),
                        'receivedAt': w.received_at.isoformat() if w.received_at else None
                    })
            except Exception:
                pass
        return ok({'webhooks': data})
    finally:
        db.close()
@app.route('/admin/stores/update', methods=['POST'])
@local_only
def admin_stores_update_post():
    data = parse_request_body()
    account_id = data.get('accountId')
    store_domain = data.get('storeDomain')
    if not account_id or not store_domain:
        return error('invalid_payload', 400)
    db = SessionLocal()
    try:
        acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        if not acc:
            return error('account_not_found', 404)
        acc.store_domain = store_domain
        db.add(acc)
        db.commit()
        return ok({'status': 'updated', 'accountId': account_id, 'storeDomain': store_domain})
    finally:
        db.close()
@app.route('/admin/stores/upsert', methods=['POST'])
@local_only
def admin_stores_upsert():
    data = parse_request_body()
    user_id = data.get('userId')
    account_id = data.get('accountId')
    store_domain = data.get('storeDomain')
    if not user_id or not account_id:
        return error('invalid_payload', 400)
    db = SessionLocal()
    try:
        acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        if acc:
            acc.store_domain = store_domain
            db.add(acc)
            db.commit()
            return ok({'status': 'updated', 'accountId': account_id, 'storeDomain': store_domain})
        u = db.query(User).filter_by(id=user_id).first()
        if not u:
            return error('user_not_found', 404)
        acc = StripeAccount(user_id=user_id, account_id=account_id, store_domain=store_domain)
        db.add(acc)
        db.commit()
        return ok({'status': 'created', 'accountId': account_id, 'storeDomain': store_domain})
    finally:
        db.close()
@app.route('/admin/stores/create', methods=['POST'])
@local_only
def admin_stores_create():
    data = parse_request_body()
    user_id = data.get('userId')
    email = data.get('email')
    store_domain = data.get('storeDomain')
    if not user_id or not email:
        return error('invalid_payload', 400)
    payload = {
        "display_name": email,
        "contact_email": email,
        "dashboard": "full",
        "defaults": {
            "responsibilities": {
                "fees_collector": "stripe",
                "losses_collector": "stripe",
            }
        },
        "identity": {
            "country": "BR",
            "entity_type": "company",
        },
        "configuration": {
            "customer": {},
            "merchant": {
                "capabilities": {
                    "card_payments": {"requested": True},
                }
            },
        },
    }
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(id=int(user_id)).first()
        if not u:
            return error('user_not_found', 404)
        acct = stripe_client.v2.core.accounts.create(payload)
        db.add(StripeAccount(user_id=u.id, account_id=acct.id, store_domain=store_domain))
        db.commit()
        return ok({'status': 'created', 'accountId': acct.id, 'storeDomain': store_domain, 'userId': u.id})
    finally:
        db.close()
@app.route('/admin/stores/update/<account_id>', methods=['PUT'])
@local_only
def admin_stores_update(account_id):
    data = parse_request_body()
    store_domain = data.get('storeDomain')
    if not store_domain:
        return error('invalid_payload', 400)
    db = SessionLocal()
    try:
        acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        if not acc:
            return error('account_not_found', 404)
        acc.store_domain = store_domain
        db.add(acc)
        db.commit()
        return ok({'status': 'updated', 'accountId': account_id, 'storeDomain': store_domain})
    finally:
        db.close()
@app.route('/admin/stores/delete/<account_id>', methods=['DELETE'])
@local_only
def admin_stores_delete(account_id):
    db = SessionLocal()
    try:
        acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        if not acc:
            return error('account_not_found', 404)
        db.delete(acc)
        db.commit()
        return ok({'status': 'deleted', 'accountId': account_id})
    finally:
        db.close()
@app.route('/api/v1/me', methods=['GET'])
def me():
    def _inner():
        db = SessionLocal()
        try:
            uid = g.user_id
            user = db.query(User).filter_by(id=uid).first()
            accounts = db.query(StripeAccount).filter_by(user_id=uid).all()
            return jsonify({
                'id': user.id,
                'email': user.email,
                'accounts': [{'accountId': a.account_id, 'storeDomain': a.store_domain} for a in accounts]
            })
        finally:
            db.close()
    return auth_required(_inner)()
@app.route('/users', methods=['GET'])
@local_only
def users_view():
    return render_template('users.html')
@app.route('/local/auth', methods=['GET'])
@local_only
def local_auth_view():
    return render_template('local_auth.html')
@app.route('/users/<int:user_id>', methods=['GET'])
@local_only
def user_detail_view(user_id):
    return render_template('user_detail.html', user_id=user_id)
@app.route('/admin/users/list', methods=['GET'])
@local_only
def admin_users_list():
    db = SessionLocal()
    try:
        rows = db.query(User).order_by(User.id.asc()).all()
        return ok({'users': [{'id': u.id, 'email': u.email} for u in rows]})
    finally:
        db.close()
@app.route('/admin/users/create', methods=['POST'])
@local_only
def admin_users_create():
    data = parse_request_body()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return error('invalid_payload', 400)
    db = SessionLocal()
    try:
        exists = db.query(User).filter_by(email=email).first()
        if exists:
            return error('email_exists', 409)
        user = User(email=email, password_hash=generate_password_hash(password))
        db.add(user)
        db.commit()
        return ok({'status': 'created', 'id': user.id, 'email': user.email})
    finally:
        db.close()
@app.route('/admin/users/delete/<int:user_id>', methods=['DELETE'])
@local_only
def admin_users_delete(user_id):
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(id=user_id).first()
        if not u:
            return error('not_found', 404)
        db.delete(u)
        db.commit()
        return ok({'status': 'deleted', 'id': user_id})
    finally:
        db.close()
@app.route('/admin/users/<int:user_id>/stores', methods=['GET'])
@local_only
def admin_user_stores(user_id):
    db = SessionLocal()
    try:
        rows = db.query(StripeAccount).filter_by(user_id=user_id).all()
        return ok({'stores': [{'accountId': a.account_id, 'storeDomain': a.store_domain} for a in rows]})
    finally:
        db.close()
@app.route('/admin/users/<int:user_id>/stores/create', methods=['POST'])
@local_only
def admin_user_store_create(user_id):
    data = parse_request_body()
    email = data.get('email')
    store_domain = data.get('storeDomain')
    if not email:
        return error('invalid_payload', 400)
    payload = {
        "display_name": email,
        "contact_email": email,
        "dashboard": "full",
        "defaults": {
            "responsibilities": {
                "fees_collector": "stripe",
                "losses_collector": "stripe",
            }
        },
        "identity": {
            "country": "BR",
            "entity_type": "company",
        },
        "configuration": {
            "customer": {},
            "merchant": {
                "capabilities": {
                    "card_payments": {"requested": True},
                }
            },
        },
    }
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(id=user_id).first()
        if not u:
            return jsonify({'error': 'user_not_found'}), 404
        acct = stripe_client.v2.core.accounts.create(payload)
        db.add(StripeAccount(user_id=user_id, account_id=acct.id, store_domain=store_domain))
        db.commit()
        return jsonify({'status': 'created', 'accountId': acct.id, 'storeDomain': store_domain})
    finally:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def home():
    domain = Config.DOMAIN
    env = 'SANDBOX' if ('localhost' in domain or 'ngrok' in domain) else 'PRODUCTION'
    return render_template('index.html', api_version=Config.API_VERSION, environment=env, domain=domain)

@app.route('/docs', methods=['GET'])
def docs():
    if Config.DOCS_PUBLIC:
        return render_template('docs.html')
    return auth_required(lambda: render_template('docs.html'))()

@app.route('/health', methods=['GET'])
@limiter.exempt
def health():
    return jsonify({'status': 'online', 'version': Config.API_VERSION})

@app.route('/status', methods=['GET'])
@limiter.exempt
def status():
    uptime = int(time.time() - app.start_time)
    domain = Config.DOMAIN
    env = 'SANDBOX' if ('localhost' in domain or 'ngrok' in domain) else 'PRODUCTION'
    return jsonify({
        'system': 'active',
        'status': 'online',
        'version': Config.API_VERSION,
        'environment': env,
        'domain': domain,
        'uptime_seconds': uptime,
        'rate_limits': {
            'default': Config.RATE_LIMIT_DEFAULT,
            'login': Config.RATE_LIMIT_LOGIN,
            'checkout': Config.RATE_LIMIT_CHECKOUT,
            'webhook': Config.RATE_LIMIT_WEBHOOK
        }
    })

@app.route('/done', methods=['GET'])
def done():
    session_id = request.args.get('session_id')
    return render_template('done.html', session_id=session_id)

@app.route('/debug/routes', methods=['GET'])
def debug_routes():
    return jsonify(sorted([str(r) for r in app.url_map.iter_rules()]))

# Helper method to parse request body (JSON or form data)
def parse_request_body():
    data = {}

    json_data = request.get_json(silent=True)
    if json_data and isinstance(json_data, dict):
        data.update(json_data)

    if request.form:
        data.update(request.form.to_dict())

    if request.args:
        data.update(request.args.to_dict())

    return data

def enforce_account_ownership(account_id):
    uid = g.get('user_id')
    if not uid or not account_id:
        return False
    db = SessionLocal()
    try:
        exists = db.query(StripeAccount).filter_by(user_id=uid, account_id=account_id).first()
        return True if exists else False
    finally:
        db.close()

@app.route('/api/create-product', methods=['POST'])
@app.route('/api/v1/create-product', methods=['POST'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def create_product():
    data = parse_request_body()
    payload, err = parse_and_validate(CreateProductSchema, data)
    if err:
        return jsonify(err), 400
    product_name = payload.productName
    product_description = payload.productDescription
    product_price = payload.productPrice
    account_id = payload.accountId
    recurring_interval = payload.recurringInterval
    if not enforce_account_ownership(account_id):
        return jsonify({'error': 'forbidden'}), 403

    try:
        product = create_product_on_account(product_name, product_description, account_id)
        price = create_price_for_product(product.id, product_price, account_id, recurring_interval)

        return jsonify({
            'productName': product_name,
            'productDescription': product_description,
            'productPrice': product_price,
            'priceId': price.id,
            'type': 'recurring' if recurring_interval else 'one_time'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-connect-account', methods=['POST'])
@app.route('/api/v1/create-connect-account', methods=['POST'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def create_connect_account():
    data = parse_request_body()

    try:
        account = stripe_client.v2.core.accounts.create({
            "display_name": data.get("email"),
            "contact_email": data.get("email"),
            "dashboard": "full",
            "defaults": {
                "responsibilities": {
                    "fees_collector": "stripe",
                    "losses_collector": "stripe",
                }
            },
            "identity": {
                "country": "BR",
                "entity_type": "company",
            },
            "configuration": {
                "customer": {},
                "merchant": {
                    "capabilities": {
                        "card_payments": {"requested": True},
                    }
                },
            },
        })
        db = SessionLocal()
        try:
            if g.get('user_id'):
                existing = db.query(StripeAccount).filter_by(account_id=account.id).first()
                if not existing:
                    db.add(StripeAccount(user_id=int(g.user_id), account_id=account.id, store_domain=data.get("storeDomain")))
                else:
                    if data.get("storeDomain"):
                        existing.store_domain = data.get("storeDomain")
                        db.add(existing)
                db.commit()
        finally:
            db.close()
        return jsonify({'accountId': account.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/checkout-session/<session_id>', methods=['GET'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def get_checkout_session(session_id):
    account_id = request.args.get('accountId') or g.get('stripe_account_id')
    try:
        if account_id and account_id != 'platform':
            s = stripe.checkout.Session.retrieve(session_id, stripe_account=account_id)
        else:
            s = stripe.checkout.Session.retrieve(session_id)
        return jsonify({
            'id': s.id,
            'status': s.status,
            'payment_status': s.payment_status,
            'mode': s.mode,
            'amount_total': s.amount_total,
            'currency': s.currency,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/create-account-link', methods=['POST'])
@app.route('/api/v1/create-account-link', methods=['POST'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def create_account_link():
    data = parse_request_body()
    account_id = data.get('accountId')
    if not account_id:
        return jsonify({'error': 'invalid_payload'}), 400
    if not enforce_account_ownership(account_id):
        return jsonify({'error': 'forbidden'}), 403

    try:
        account_link = stripe_client.v2.core.account_links.create({
            "account": account_id,
            "use_case": {
                "type": "account_onboarding",
                "account_onboarding": {
                    "configurations": ["merchant", "customer"],
                    "refresh_url": "https://example.com",
                    "return_url": f"https://example.com?accountId={account_id}",
                },
            },
        })

        return jsonify({'url': account_link.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/account-status/<account_id>', methods=['GET'])
@app.route('/api/v1/account-status/<account_id>', methods=['GET'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def account_status(account_id):
    try:
        if not enforce_account_ownership(account_id):
            return jsonify({'error': 'forbidden'}), 403
        account = stripe_client.v2.core.accounts.retrieve(
            account_id, {
                "include": [
                    "requirements",
                    "configuration.merchant"
                ]
            }
        )
        payouts_enabled = (
            (account.get("configuration") or {}).get("merchant") or {}
        ).get("capabilities", {}).get("stripe_balance", {}).get("payouts", {}).get(
            "status"
        ) == "active"
        charges_enabled = (
            (account.get("configuration") or {}).get("merchant") or {}
        ).get("capabilities", {}).get("card_payments", {}).get("status") == "active"
        summary_status = (
            ((account.get("requirements") or {}).get("summary") or {})
            .get("minimum_deadline", {})
            .get("status")
        )
        details_submitted = (summary_status is None) or (
            summary_status == "eventually_due"
        )
        return jsonify(
            {
                "id": account["id"],
                "payoutsEnabled": payouts_enabled,
                "chargesEnabled": charges_enabled,
                "detailsSubmitted": details_submitted,
                "requirements": (account.get("requirements") or {}).get("entries"),
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<account_id>', methods=['GET'])
@app.route('/api/v1/products/<account_id>', methods=['GET'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def get_products(account_id):
    try:
        if not enforce_account_ownership(account_id):
            return jsonify({'error': 'forbidden'}), 403
        prices = list_prices_with_products(account_id)

        products = []
        for price in prices.data:
            products.append({
                'id': price.product.id,
                'name': price.product.name,
                'description': price.product.description,
                'price': price.unit_amount,
                'priceId': price.id,
                'image': 'https://i.imgur.com/6Mvijcm.png'
            })

        return jsonify(products)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/subscribe-to-platform', methods=['POST'])
@app.route('/api/v1/subscribe-to-platform', methods=['POST'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_CHECKOUT)
def subscribe_to_platform():
    try:
        data = parse_request_body()
        payload, err = parse_and_validate(SubscribePlatformSchema, data)
        if err:
            return jsonify(err), 400
        account_id = payload.accountId
        price_id = Config.PLATFORM_PRICE_ID
        db = SessionLocal()
        try:
            acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        finally:
            db.close()
        sd = acc.store_domain if acc and acc.store_domain else None
        success_url = payload.successUrl or (sd and f"{sd}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}") or f"{Config.DOMAIN}?session_id={{CHECKOUT_SESSION_ID}}&success=true"
        cancel_url = payload.cancelUrl or (sd and f"{sd}/checkout/cancel") or f"{Config.DOMAIN}?canceled=true"
        if not account_id:
            return jsonify({'error': 'accountId ausente'}), 400
        if not price_id:
            return jsonify({'error': 'PLATFORM_PRICE_ID vazio ou não configurado'}), 400
        session = create_checkout_session_platform(
            account_id,
            price_id,
            success_url,
            cancel_url,
        )
        return jsonify({'url': session.url})
    except stripe.error.InvalidRequestError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/create-checkout-session', methods=['POST'])
@app.route('/api/v1/create-checkout-session', methods=['POST'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_CHECKOUT)
def create_checkout_session():
    try:
        data = parse_request_body()
        payload, err = parse_and_validate(CreateCheckoutSessionSchema, data)
        if err:
            return jsonify(err), 400
        account_id = payload.accountId
        price_id = payload.priceId
        order_id = getattr(payload, "orderId", None)
        db = SessionLocal()
        try:
            acc = db.query(StripeAccount).filter_by(account_id=account_id).first()
        finally:
            db.close()
        sd = acc.store_domain if acc and acc.store_domain else None
        success_url = payload.successUrl or (sd and f"{sd}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}") or f"{Config.DOMAIN}/done?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = payload.cancelUrl or (sd and f"{sd}/checkout/cancel") or f"{Config.DOMAIN}"
        if not account_id:
            return jsonify({'error': 'accountId ausente'}), 400
        if not price_id:
            return jsonify({'error': 'priceId ausente'}), 400
        if not enforce_account_ownership(account_id):
            return jsonify({'error': 'forbidden'}), 403
        price = retrieve_price(price_id, account_id)
        price_type = price.type
        mode = 'subscription' if price_type == 'recurring' else 'payment'
        from flask import g as _g
        setattr(_g, "order_id", order_id)
        if order_id:
            dbc = SessionLocal()
            try:
                from core.db import OrderCorrelation
                exists = dbc.query(OrderCorrelation).filter_by(order_id=order_id).first()
                if not exists:
                    dbc.add(OrderCorrelation(order_id=order_id, account_id=account_id))
                    dbc.commit()
            finally:
                dbc.close()
        checkout_session = create_checkout_session_connected(
            account_id,
            price_id,
            mode,
            success_url,
            cancel_url,
            123,
        )
        response = make_response(redirect(checkout_session.url, code=303))
        return response
    except stripe.error.InvalidRequestError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/create-portal-session', methods=['POST'])
@app.route('/api/v1/create-portal-session', methods=['POST'])
@auth_required
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def create_portal_session():
    data = parse_request_body()
    payload, err = parse_and_validate(CreatePortalSessionSchema, data)
    if err:
        return jsonify(err), 400
    session_id = payload.session_id
    checkout_session = stripe.checkout.Session.retrieve(session_id)
    portal_session = stripe.billing_portal.Session.create(
        customer_account=checkout_session.customer_account,
        return_url=f"{Config.DOMAIN}/?session_id={session_id}",
    )

    return redirect(portal_session.url, code=303)

@app.route('/webhook', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_WEBHOOK)
def webhook_received():
    secrets_raw = Config.STRIPE_WEBHOOK_SECRET
    if not secrets_raw:
        return jsonify({'error': 'webhook_secret_not_configured'}), 500
    sig_header = request.headers.get('stripe-signature')
    body = request.get_data(cache=True)
    event = None
    for sec in [s.strip() for s in str(secrets_raw).split(',') if s.strip()]:
        try:
            event = verify_webhook(body, sig_header, sec)
            break
        except stripe.error.SignatureVerificationError as e:
            event = None
            continue
    if event is None:
        logger = structlog.get_logger()
        logger.warning("webhook_invalid_signature", request_id=g.get('request_id'), error="signature_mismatch_all_secrets")
        return jsonify({'error': 'invalid_signature'}), 400

    logger = structlog.get_logger()
    logger.info("webhook_received", request_id=g.get('request_id'), event_id=event.get('id'), event_type=event.get('type'))

    # Persist event log (idempotente por event_id)
    db = SessionLocal()
    try:
        exists_log = db.query(WebhookLog).filter_by(event_id=event['id']).first()
        if not exists_log:
            db.add(WebhookLog(event_id=event['id'], event_type=event['type'], payload=json.dumps(event)))
            db.commit()
    finally:
        db.close()

    etype = event.get('type')
    if etype in ('checkout.session.completed', 'payment_intent.succeeded'):
        obj = event['data']['object']
        raw_status = obj.get('payment_status') or obj.get('status')
        if raw_status in ('paid', 'succeeded', 'completed', 'complete'):
            normalized_status = 'paid'
        else:
            logger.info("webhook_ignored_nonfinal", request_id=g.get('request_id'), event_id=event['id'], event_type=etype, status=raw_status)
            return jsonify({'status': 'ignored'}), 200
        db2 = SessionLocal()
        try:
            exists = db2.query(WebhookEvent).filter_by(event_id=event['id']).first()
            if exists:
                logger.info("webhook_duplicate", request_id=g.get('request_id'), event_id=event['id'])
                return jsonify({'status': 'duplicate'}), 200
            db2.add(WebhookEvent(event_id=event['id'], status=normalized_status, processed_at=None, source="webhook"))
            db2.commit()
        finally:
            db2.close()
        acc_id = event.get('account')
        order_id = None
        if isinstance(obj, dict):
            meta = obj.get('metadata') or {}
            order_id = meta.get('orderId') or obj.get('client_reference_id')
        if not order_id:
            logger.info("webhook_missing_order_id", request_id=g.get('request_id'), event_id=event['id'], event_type=etype)
            return jsonify({'status': 'no_order_id'}), 200
        if not acc_id:
            # try resolve account via order correlation
            dbcorr = SessionLocal()
            try:
                from core.db import OrderCorrelation
                corr = dbcorr.query(OrderCorrelation).filter_by(order_id=order_id).first()
                if corr:
                    acc_id = corr.account_id
                    logger.info("webhook_account_resolved_from_correlation", request_id=g.get('request_id'), event_id=event['id'], order_id=order_id, account_id=acc_id)
                else:
                    logger.info("webhook_account_unresolved", request_id=g.get('request_id'), event_id=event['id'], order_id=order_id)
                    return jsonify({'status': 'success'}), 200
            finally:
                dbcorr.close()
        dispatch_store_webhook(acc_id, order_id, normalized_status, event.get("id"))
    else:
        logger.info("webhook_unhandled_type", request_id=g.get('request_id'), event_id=event['id'], event_type=event['type'])

    return jsonify({'status': 'success'})

def dispatch_store_webhook(account_id, order_id, status, event_id):
    db3 = SessionLocal()
    try:
        acc = db3.query(StripeAccount).filter_by(account_id=account_id).first()
        if acc and acc.store_domain and Config.PAYMENTS_EVENTS_SECRET:
            payload = {"orderId": order_id, "status": status}
            body = json.dumps(payload, separators=(",", ":"))
            sig = hmac.new(
                Config.PAYMENTS_EVENTS_SECRET.encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            ep = acc.store_domain.rstrip("/") + Config.PAYMENTS_EVENTS_PATH
            headers = {Config.PAYMENTS_EVENTS_HEADER: sig, "Content-Type": "application/json"}
            dispatch = db3.query(StoreDispatch).filter_by(event_id=event_id).first()
            if not dispatch:
                dispatch = StoreDispatch(event_id=event_id, account_id=account_id, order_id=order_id, status=status, attempts=0)
                db3.add(dispatch)
                db3.commit()
            logger = structlog.get_logger()
            delays = [1, 2, 4]
            for attempt, dly in enumerate(delays, start=1):
                try:
                    r = requests.post(ep, data=body, headers=headers, timeout=5)
                    logger.info("store_dispatch_response", request_id=g.get('request_id'), event_id=event_id, status_code=getattr(r, 'status_code', None))
                    dispatch.attempts = attempt
                    if getattr(r, 'status_code', 0) == 200:
                        from datetime import datetime
                        dispatch.delivered_at = datetime.utcnow()
                        db3.add(dispatch)
                        db3.commit()
                        break
                except Exception:
                    logger.info("store_dispatch_retry_scheduled", request_id=g.get('request_id'), event_id=event_id, attempt=attempt, delay_seconds=dly)
                    dispatch.attempts = attempt
                    db3.add(dispatch)
                    db3.commit()
                import time
                time.sleep(dly)
        # update processed_at
        db3.execute(text("UPDATE webhook_events SET processed_at=:ts, order_id=:oid, account_id=:acc, status=:st WHERE event_id=:eid"),
                    {"ts": datetime.utcnow(), "oid": order_id, "acc": account_id, "st": status, "eid": event_id})
        db3.commit()
    finally:
        db3.close()

@app.route('/internal/sync/stripe-events', methods=['POST'])
@local_only
def internal_sync_stripe_events():
    run_sync_once()
    return ok({"status": "sync_started"})

@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_LOGIN)
def login():
    data = parse_request_body()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'invalid_credentials'}), 401
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'invalid_credentials'}), 401
        account = db.query(StripeAccount).filter_by(user_id=user.id).first()
        access = generate_access_token(str(user.id), {'stripe_account_id': account.account_id if account else None})
        refresh = generate_refresh_token(str(user.id), {'stripe_account_id': account.account_id if account else None})
        return jsonify({'access_token': access, 'refresh_token': refresh})
    finally:
        db.close()

@app.route('/api/v1/auth/register', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_LOGIN)
def register():
    data = parse_request_body()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'invalid_payload'}), 400
    db = SessionLocal()
    try:
        exists = db.query(User).filter_by(email=email).first()
        if exists:
            return jsonify({'error': 'email_in_use'}), 400
        user = User(email=email, password_hash=generate_password_hash(password))
        db.add(user)
        db.commit()
        return jsonify({'status': 'registered'})
    finally:
        db.close()

@app.route('/api/v1/auth/refresh', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_LOGIN)
def refresh():
    auth = request.headers.get('Authorization') or ''
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return jsonify({'error': 'unauthorized'}), 401
    try:
        claims = jwt.decode(parts[1], Config.JWT_SECRET, algorithms=[Config.JWT_ALG])
        if claims.get('type') != 'refresh':
            return jsonify({'error': 'unauthorized'}), 401
        sub = claims.get('sub')
        stripe_account_id = claims.get('stripe_account_id')
        access = generate_access_token(sub, {'stripe_account_id': stripe_account_id})
        return jsonify({'access_token': access})
    except Exception:
        return jsonify({'error': 'unauthorized'}), 401

if __name__ == '__main__':
    app.rate_limit_identity = None
    try:
        start_worker()
    except Exception:
        pass
    app.run(port=4242, host="::1", debug=False)
