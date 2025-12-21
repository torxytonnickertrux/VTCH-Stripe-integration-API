#! /usr/bin/env python3.6

import os
import json
import time
from flask import Flask, jsonify, request, redirect, make_response, g, render_template
from functools import wraps
from dotenv import load_dotenv
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from core.config import Config
from core.logging import configure_logging, bind_request_context
from core.rate_limit import init_limiter
from core.auth import auth_required, generate_access_token, generate_refresh_token
from core.schemas import (
    parse_and_validate,
    CreateProductSchema,
    CreateCheckoutSessionSchema,
    SubscribePlatformSchema,
    CreatePortalSessionSchema,
)
from core.db import init_db, SessionLocal, User, StripeAccount, WebhookEvent, WebhookLog
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
load_dotenv()
stripe.api_key = Config.STRIPE_SECRET_KEY
stripe_client = StripeClient(str(Config.STRIPE_SECRET_KEY))
app = Flask(__name__)
CORS(app)
configure_logging()
bind_request_context(app)
limiter = init_limiter(app)
init_db()
app.start_time = time.time()

@app.route('/', methods=['GET'])
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
    if g.get('stripe_account_id') and account_id != g.get('stripe_account_id'):
        return False
    return True

def local_only(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr or ''
        if ip not in ('127.0.0.1', '::1'):
            return jsonify({'error': 'forbidden'}), 403
        return fn(*args, **kwargs)
    return wrapper
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
    endpoint_secret = Config.STRIPE_WEBHOOK_SECRET
    if not endpoint_secret:
        return jsonify({'error': 'webhook_secret_not_configured'}), 500
    sig_header = request.headers.get('stripe-signature')
    try:
        event = verify_webhook(request.data, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError as e:
        logger = structlog.get_logger()
        logger.warning("webhook_invalid_signature", request_id=g.get('request_id'), error=str(e))
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

    match event['type']:
        case 'customer.subscription.trial_will_end':
            subscription = event['data']['object']
            status = subscription['status']
            logger.info("webhook_subscription_trial_will_end", request_id=g.get('request_id'), event_id=event['id'], status=status)
        case 'customer.subscription.deleted':
            subscription = event['data']['object']
            status = subscription['status']
            logger.info("webhook_subscription_deleted", request_id=g.get('request_id'), event_id=event['id'], status=status)
        case 'checkout.session.completed':
            session = event['data']['object']
            status = session['status']
            logger.info("webhook_checkout_completed", request_id=g.get('request_id'), event_id=event['id'], status=status)
            db2 = SessionLocal()
            try:
                exists = db2.query(WebhookEvent).filter_by(event_id=event['id']).first()
                if exists:
                    logger.info("webhook_duplicate", request_id=g.get('request_id'), event_id=event['id'])
                    return jsonify({'status': 'duplicate'}), 200
                db2.add(WebhookEvent(event_id=event['id']))
                db2.commit()
            finally:
                db2.close()
        case 'checkout.session.async_payment_failed':
            session = event['data']['object']
            status = session['status']
            logger.info("webhook_checkout_async_payment_failed", request_id=g.get('request_id'), event_id=event['id'], status=status)
        case _:
            logger.info("webhook_unhandled_type", request_id=g.get('request_id'), event_id=event['id'], event_type=event['type'])

    return jsonify({'status': 'success'})

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
    app.run(port=4242, host="::1", debug=False)
