import stripe
from core.config import Config

stripe.api_key = Config.STRIPE_SECRET_KEY

def create_product_on_account(name, description, account_id):
    product = stripe.Product.create(name=name, description=description, stripe_account=account_id)
    return product

def create_price_for_product(product_id, unit_amount, account_id, recurring_interval=None):
    price_data = {
        "product": product_id,
        "unit_amount": unit_amount,
        "currency": "brl",
        "stripe_account": account_id,
    }
    if recurring_interval:
        price_data["recurring"] = {"interval": recurring_interval}
        
    price = stripe.Price.create(**price_data)
    return price

def list_prices_with_products(account_id):
    if account_id != "platform":
        prices = stripe.Price.list(expand=["data.product"], active=True, limit=100, stripe_account=account_id)
    else:
        prices = stripe.Price.list(expand=["data.product"], active=True, limit=100)
    return prices

def create_checkout_session_platform(account_id, price_id, success_url, cancel_url):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_account=account_id,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session

def create_checkout_session_connected(account_id, price_id, mode, success_url, cancel_url, fee_amount):
    checkout_session = stripe.checkout.Session.create(
        line_items=[{"price": price_id, "quantity": 1}],
        mode=mode,
        success_url=success_url,
        cancel_url=cancel_url,
        **(
            {"subscription_data": {"application_fee_amount": fee_amount}}
            if mode == "subscription"
            else {"payment_intent_data": {"application_fee_amount": fee_amount}}
        ),
        stripe_account=account_id,
    )
    return checkout_session

def retrieve_price(price_id, account_id):
    return stripe.Price.retrieve(price_id, stripe_account=account_id)

def verify_webhook(payload, sig_header, endpoint_secret):
    return stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
