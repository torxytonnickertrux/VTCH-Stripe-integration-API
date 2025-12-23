# Integração para Lojas — Liberação Pós-Pagamento (HMAC)

Este guia descreve como uma loja cliente deve receber a confirmação de pagamento e liberar um pedido automaticamente, com segurança via HMAC-SHA256.

## Requisitos
- Endpoint público na loja: `POST /payments/events/`
- Corpo em JSON e cabeçalho `X_PAYMENTS_SIGNATURE` (hexdigest HMAC-SHA256 do corpo)
- Segredo compartilhado com a API (`PAYMENTS_EVENTS_SECRET`)

## Fluxo
1. A conta conectada do vendedor é criada com `storeDomain` (ex.: `https://loja.com`).
2. Após `checkout.session.completed`, a API envia para `<storeDomain>/payments/events/`:
   ```json
   {
     "id": "evt_...",
     "type": "checkout.session.completed",
     "order_id": "ord_123",
     "status": "pago"
   }
   ```
3. A loja valida o HMAC e, se `status='pago'` e `order_id` presente, atualiza o pedido para pago.
4. Eventos repetidos (mesmo `id`) devem ser ignorados (idempotência).

## Redirecionamento Pós-Pagamento
- Crie rotas na loja:
  - `GET /checkout/success?session_id=<id>` para confirmar pagamento e exibir resumo.
  - `GET /checkout/cancel` para retorno ao carrinho ou re-tentativa.
- Gere URLs absolutas:
  - `successUrl`: `https://loja.com/checkout/success?session_id={{CHECKOUT_SESSION_ID}}`
  - `cancelUrl`: `https://loja.com/checkout/cancel`
- Envie nas requisições à API:
  - `POST /api/v1/create-checkout-session`
  - `POST /api/v1/subscribe-to-platform`
- Fallback:
  - Quando não enviar, a API usa `storeDomain` (se definido) ou Home/Done da API para redirecionar.
- Exemplos de rotas:
  - Node/Express:
    ```js
    app.get('/checkout/success', (req, res) => {
      const sessionId = req.query.session_id;
      res.render('checkout-success', { sessionId });
    });
    app.get('/checkout/cancel', (req, res) => {
      res.render('checkout-cancel');
    });
    ```
  - Django:
    ```py
    def checkout_success(request):
        session_id = request.GET.get('session_id')
        return render(request, 'orders/success.html', {'session_id': session_id})
    def checkout_cancel(request):
        return render(request, 'orders/cancel.html')
    ```

## Verificador HMAC (Exemplo em Python)
```python
import hmac, hashlib, json
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET = "<PAYMENTS_EVENTS_SECRET>"  # deve ser igual ao configurado na API

@app.route("/payments/events/", methods=["POST"])
def events():
    body = request.data
    sig = request.headers.get("X_PAYMENTS_SIGNATURE") or ""
    calc = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, sig):
        return jsonify({"error": "invalid_signature"}), 400
    data = json.loads(body.decode("utf-8"))
    if data.get("order_id") and data.get("status") == "pago":
        # atualizar pedido para "pago"
        # ex.: Order.update_status(order_id, "paid")
        ...
    return jsonify({"status": "ok"})
```

## Teste Manual
1. Obtenha `PAYMENTS_EVENTS_SECRET`.
2. Monte o corpo:
   ```json
   {"id":"evt_test","type":"checkout.session.completed","order_id":"ord_1","status":"pago"}
   ```
3. Gere a assinatura:
   - hexdigest HMAC-SHA256 do corpo usando `PAYMENTS_EVENTS_SECRET`.
4. Envie:
   ```
   curl -X POST https://loja.com/payments/events/ \
     -H "Content-Type: application/json" \
     -H "X_PAYMENTS_SIGNATURE: <hmac_hex>" \
     -d '{"id":"evt_test","type":"checkout.session.completed","order_id":"ord_1","status":"pago"}'
   ```

## Checklist de Configuração
- `PAYMENTS_EVENTS_SECRET`: mesmo valor na API e na loja
- `PAYMENTS_EVENTS_PATH`: default `/payments/events/`
- `PAYMENTS_EVENTS_HEADER`: default `X_PAYMENTS_SIGNATURE`
- `storeDomain` definido ao criar a conta conectada

## Observações
- Fallback de URLs de retorno (se `successUrl`/`cancelUrl` não forem enviados):
  - `success`: `https://loja/checkout/success?session_id={CHECKOUT_SESSION_ID}`
  - `cancel`: `https://loja/checkout/cancel`
- Idempotência: a API não reprocessa eventos com `id` já registrado e evita reenvios.
