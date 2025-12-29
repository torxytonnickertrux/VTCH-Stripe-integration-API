# API v1 — Documentação de Referência

Esta documentação descreve todas as rotas públicas da API v1, modelos de autenticação, integração Stripe (Connect, Checkout, Portal, Webhooks), formatos de requisição e resposta, exemplos de uso em cURL/JavaScript/Python e diretrizes de erro e rate limit. O conteúdo reflete o comportamento atual da API.

## Visão Geral do Produto e Modelo de Negócio
- Plataforma SaaS multi-tenant com integração Stripe Connect para marketplace.
- Usuários autenticados podem criar contas conectadas, definir produtos e preços, e abrir checkouts diretamente nessas contas.
- A plataforma pode cobrar assinatura própria (`PLATFORM_PRICE_ID`) e taxas por transação via `application_fee_amount`.
- Isolamento por usuário: validação de ownership impede acesso a `accountId` de terceiros.

## Base URLs
- Desenvolvimento: `http://localhost:4242`
- Produção/Externo (ex.: túnel): use sua URL pública. Se acessar via navegador e ver aviso do túnel, adicione o header `ngrok-skip-browser-warning: true` ou utilize um client HTTP.

## Autenticação (JWT)
- Fluxo:
  - `POST /api/v1/auth/register` cria usuário com `email` e `password`.
  - `POST /api/v1/auth/login` retorna `{"access_token","refresh_token"}`.
  - `POST /api/v1/auth/refresh` com `Authorization: Bearer <refresh>` retorna `{"access_token"}`.
- Claims:
  - `access_token`: `sub` (id do usuário), `exp`, opcional `stripe_account_id` associado ao usuário.
  - `refresh_token`: inclui `type: "refresh"`, `sub`, `exp`, e opcional `stripe_account_id`.
- Validades:
  - `JWT_ACCESS_TTL_SECONDS` padrão `900` (15 min).
  - `JWT_REFRESH_TTL_SECONDS` padrão `604800` (7 dias).
- Uso:
  - Envie `Authorization: Bearer <access_token>` nas rotas protegidas.
  - Quando `access` expirar, chame `POST /api/v1/auth/refresh` com o `refresh`.

### Exemplos de Autenticação
- cURL (Login):
  ```
  curl -X POST http://localhost:4242/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"secret"}'
  ```
- JavaScript (Fetch):
  ```
  const res = await fetch('http://localhost:4242/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'user@example.com', password: 'secret' })
  });
  const tokens = await res.json(); // { access_token, refresh_token }
  ```
- Python (requests):
  ```
  import requests
  r = requests.post('http://localhost:4242/api/v1/auth/login',
                    json={'email':'user@example.com','password':'secret'})
  tokens = r.json()
  ```

## Gestão de Contas Conectadas (Stripe Connect)

### Criar conta conectada
- Propósito: criar conta Stripe Connect V2 e vinculá-la ao usuário autenticado.
- Método/URL: `POST /api/v1/create-connect-account`
- Headers: `Authorization: Bearer <access_token>`
- Body: `{"email": "<email@dominio>"}`
- Parâmetros adicionais:
  - `storeDomain` (opcional): domínio da loja para fallback de URLs e liberação via HMAC (ex.: `https://loja.com`)
- Respostas:
  - Sucesso: `200` → `{"accountId":"acct_..."}`.
  - Erros: `401` (unauthorized), `500` (erro Stripe/outros).
- Exemplos:
  - cURL:
    ```
    curl -X POST http://localhost:4242/api/v1/create-connect-account \
      -H "Authorization: Bearer $ACCESS" \
      -H "Content-Type: application/json" \
      -d '{"email":"seller@example.com"}'
    ```
  - JS (Fetch):
    ```
    const res = await fetch('/api/v1/create-connect-account', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${access}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'seller@example.com' })
    });
    const data = await res.json(); // { accountId }
    ```
  - Python:
    ```
    import requests
    r = requests.post('http://localhost:4242/api/v1/create-connect-account',
                      headers={'Authorization': f'Bearer {access}'},
                      json={'email':'seller@example.com'})
    print(r.json())
    ```

### Criar Account Link (onboarding)
- Propósito: gerar link de onboarding para a conta conectada.
- Método/URL: `POST /api/v1/create-account-link`
- Headers: `Authorization: Bearer <access_token>`
- Body:
  - `accountId` (string, obrigatório)
- Respostas:
  - Sucesso: `200` → `{"url":"https://connect.stripe.com/..."}`
  - Erros: `400` (payload ausente), `403` (ownership), `401`, `500`.
- Observação: valida ownership (`accountId` deve pertencer ao usuário).

### Status da conta
- Método/URL: `GET /api/v1/account-status/<account_id>`
- Headers: `Authorization: Bearer <access_token>`
- Resposta (exemplo):
  ```
  {
    "id": "acct_...",
    "payoutsEnabled": true,
    "chargesEnabled": true,
    "detailsSubmitted": false,
    "requirements": [ ... ]
  }
  ```
- Erros: `403` (ownership), `401`, `500`.

## Produtos e Preços

### Criar Produto + Preço
- Propósito: criar `Product` e `Price` na conta conectada.
- Método/URL: `POST /api/v1/create-product`
- Headers: `Authorization: Bearer <access_token>`
- Body (schema exato):
  - `productName` (string, obrigatório)
  - `productDescription` (string, obrigatório)
  - `productPrice` (inteiro, centavos BRL, obrigatório)
  - `accountId` (string, obrigatório)
  - `recurringInterval` (opcional: `"month"` ou `"year"`; ausente → one-time)
- Respostas:
  - Sucesso: `200`
    ```
    {
      "productName": "...",
      "productDescription": "...",
      "productPrice": 1000,
      "priceId": "price_...",
      "type": "recurring" | "one_time"
    }
    ```
  - Erros: `400` (invalid_payload), `403` (ownership), `401`, `500`.

### Listar produtos/preços
- Método/URL: `GET /api/v1/products/<account_id>`
- Headers: `Authorization: Bearer <access_token>`
- Resposta:
  ```
  [
    {
      "id": "prod_...",
      "name": "Nome",
      "description": "Desc",
      "price": 1000,
      "priceId": "price_...",
      "image": "https://i.imgur.com/6Mvijcm.png"
    }
  ]
  ```
- Observa ownership; erros: `403`, `401`, `500`.

## Checkout

### Checkout na conta conectada
- Propósito: criar sessão de checkout na conta do vendedor; `mode` deriva de `Price.type`.
- Método/URL: `POST /api/v1/create-checkout-session`
- Headers: `Authorization: Bearer <access_token>`
- Body:
  - `accountId` (string, obrigatório)
  - `priceId` (string, obrigatório)
  - `successUrl` (string, opcional)
  - `cancelUrl` (string, opcional)
- Respostas:
- Sucesso: redireciona `303` para `session.url`.
  - Erros: `400` (invalid_payload/ausência), `403` (ownership), `401`, `500`.
- Observações:
- `mode` é `subscription` se `Price.type=recurring`; caso contrário `payment`.
- A plataforma pode aplicar taxa via `application_fee_amount`.
 - Se `successUrl`/`cancelUrl` não forem enviados e existir `storeDomain` cadastrado na conta, o fallback usa:
   - `success`: `https://loja/checkout/success?session_id={CHECKOUT_SESSION_ID}`
   - `cancel`: `https://loja/checkout/cancel`

### Assinar a plataforma (recorrente)
- Propósito: criar sessão de assinatura usando `PLATFORM_PRICE_ID` na conta da plataforma, para o `accountId` informado como `customer_account`.
- Método/URL: `POST /api/v1/subscribe-to-platform`
- Headers: `Authorization: Bearer <access_token>`
- Body:
  - `accountId` (string, obrigatório)
  - `successUrl` (string, opcional)
  - `cancelUrl` (string, opcional)
- Respostas:
  - Sucesso: `200` → `{"url":"https://checkout.stripe.com/..."}`
- Erros: `400` (accountId ausente, priceId plataforma não configurado), `401`, `500`.
 - Se `successUrl`/`cancelUrl` não forem enviados e existir `storeDomain` cadastrado para o `accountId`, o fallback usa os mesmos padrões de checkout acima.

## Portal do Cliente
- Propósito: abrir o Billing Portal do Stripe para gerenciar assinaturas.
- Método/URL: `POST /api/v1/create-portal-session`
- Headers: `Authorization: Bearer <access_token>`
- Body:
  - `session_id` (string, obrigatório; ID de `checkout.session` já concluída)
- Respostas:
  - Sucesso: redireciona `303` para `portal_session.url`.
  - Erros: `400` (invalid_payload), `401`.

## Webhooks
- Método/URL: `POST /webhook`
- Headers: `stripe-signature: <valor fornecido pelo Stripe>`
- Segurança:
  - Verificação de assinatura usando `STRIPE_WEBHOOK_SECRET`.
  - Idempotência básica via tabela `webhook_events` (ignora `event_id` já processado).
- Eventos suportados:
  - `checkout.session.completed` (com idempotência)
  - `checkout.session.async_payment_failed`
  - `customer.subscription.deleted`
  - `customer.subscription.trial_will_end`
- Respostas:
  - `200 {"status":"success"}` quando processado.
  - `200 {"status":"duplicate"}` se evento repetido.
  - `400 {"error":"invalid_signature"}` se verificação falhar.
  - `500 {"error":"webhook_secret_not_configured"}` se sem segredo.

### Verificação de Assinatura — Exemplos
- Python:
  ```
  import stripe
  endpoint_secret = "whsec_..."
  payload = request.data
  sig_header = request.headers.get("stripe-signature")
  try:
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
  except stripe.error.SignatureVerificationError:
    return {"error":"invalid_signature"}, 400
  ```
- Node.js:
  ```
  const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
  const endpointSecret = process.env.STRIPE_WEBHOOK_SECRET;
  const payload = req.rawBody;
  const sig = req.headers['stripe-signature'];
  let event;
  try {
    event = stripe.webhooks.constructEvent(payload, sig, endpointSecret);
  } catch (err) {
    return res.status(400).json({ error: 'invalid_signature' });
  }
  ```

## Tratamento de Erros e Códigos de Resposta
- `400 invalid_payload`: validação via Pydantic
  - Exemplo:
    ```
    {
      "error": "invalid_payload",
      "details": [
        {"loc":["productPrice"],"msg":"ensure this value is greater than 0","type":"value_error"}
      ]
    }
    ```
- `401 unauthorized`:
  - Falta/erro em `Authorization` ou token inválido/expirado.
- `403 forbidden`:
  - Violação de ownership (`accountId` não pertence ao usuário).
- `400` erros Stripe (ex.: `InvalidRequestError`):
  - Payload ausente ou `priceId` inválido.
- `500`:
  - Erros inesperados (ex.: falha de Stripe, configuração ausente como webhook secret).

## Rate Limits
- Padrão: `Config.RATE_LIMIT_DEFAULT` (`100/hour` padrão).
- Login: `Config.RATE_LIMIT_LOGIN` (`10/minute`).
- Checkout: `Config.RATE_LIMIT_CHECKOUT` (`30/minute`).
- Webhook: `Config.RATE_LIMIT_WEBHOOK` (`300/minute`).
- Identidade de rate limit:
  - Associada ao `user_id` quando autenticado.

## Referência de Endpoints (Resumo)
- `POST /api/v1/auth/register` — cria usuário.
- `POST /api/v1/auth/login` — retorna `access` e `refresh`.
- `POST /api/v1/auth/refresh` — emite novo `access`.
- `POST /api/v1/create-connect-account` — cria conta Stripe.
- `POST /api/v1/create-account-link` — link de onboarding.
- `GET  /api/v1/account-status/<account_id>` — status/requirements.
- `GET  /api/v1/products/<account_id>` — lista produtos/preços.
- `POST /api/v1/create-product` — cria produto + preço.
- `POST /api/v1/create-checkout-session` — checkout ligado ao preço.
- `POST /api/v1/subscribe-to-platform` — assinatura plataforma.
- `POST /api/v1/create-portal-session` — abre billing portal.
- `POST /webhook` — recebe eventos Stripe.

## Exemplos de Uso

### Criar produto + preço
- cURL:
  ```
  curl -X POST http://localhost:4242/api/v1/create-product \
    -H "Authorization: Bearer $ACCESS" \
    -H "Content-Type: application/json" \
    -d '{
      "productName":"Plano Pro",
      "productDescription":"Assinatura mensal",
      "productPrice": 2990,
      "accountId":"acct_123",
      "recurringInterval":"month"
    }'
  ```
- JS (Fetch):
  ```
  const res = await fetch('/api/v1/create-product', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      productName: 'Plano Pro',
      productDescription: 'Assinatura mensal',
      productPrice: 2990,
      accountId: 'acct_123',
      recurringInterval: 'month'
    })
  });
  const data = await res.json();
  ```
- Python:
  ```
  import requests
  payload = {
    "productName": "Plano Pro",
    "productDescription": "Assinatura mensal",
    "productPrice": 2990,
    "accountId": "acct_123",
    "recurringInterval": "month"
  }
  r = requests.post('http://localhost:4242/api/v1/create-product',
                    headers={'Authorization': f'Bearer {access}'},
                    json=payload)
  print(r.json())
  ```

### Checkout one-time
- cURL:
  ```
  curl -X POST http://localhost:4242/api/v1/create-checkout-session \
    -H "Authorization: Bearer $ACCESS" \
    -H "Content-Type: application/json" \
    -d '{"accountId":"acct_123","priceId":"price_one_time"}' \
    -i
  ```
  Resposta: `303 See Other` com `Location: https://checkout.stripe.com/...`

### Checkout assinatura
- cURL:
  ```
  curl -X POST http://localhost:4242/api/v1/create-checkout-session \
    -H "Authorization: Bearer $ACCESS" \
    -H "Content-Type: application/json" \
    -d '{"accountId":"acct_123","priceId":"price_recurring"}' \
    -i
  ```
  `mode=subscription` será inferido do `price_recurring`.

### Assinar a plataforma
- Python:
  ```
  import requests
  r = requests.post('http://localhost:4242/api/v1/subscribe-to-platform',
                    headers={'Authorization': f'Bearer {access}'},
                    json={'accountId':'acct_123'})
  print(r.json())  # { url: ... }
  ```

### Portal do cliente
- JS:
  ```
  const res = await fetch('/api/v1/create-portal-session', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${access}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: 'cs_test_...' })
  });
  // redireciona 303 para o portal
  ```

### Webhook (payloads comuns)
- `checkout.session.completed`:
  ```
  {
    "id":"evt_...",
    "type":"checkout.session.completed",
    "data":{"object":{"id":"cs_...","status":"complete", ...}}
  }
  ```
- `invoice.paid` (ex.: quando assinaturas são cobradas):
  ```
  {
    "id":"evt_...",
    "type":"invoice.paid",
    "data":{"object":{"id":"in_...","status":"paid", ...}}
  }
  ```
- `customer.subscription.updated`:
  ```
  {
    "id":"evt_...",
    "type":"customer.subscription.updated",
    "data":{"object":{"id":"sub_...","status":"active", ...}}
  }
  ```

## Liberação Pós-Pagamento (Lojas)
- Objetivo: ao concluir o pagamento, notificar automaticamente a loja cliente via webhook assinado com HMAC-SHA256 para liberar o pedido.
- Requisitos:
  - A conta conectada deve possuir `storeDomain` cadastrado (enviado ao criar a conta via `POST /api/v1/create-connect-account`).
  - `PAYMENTS_EVENTS_SECRET` definido na API (segredo compartilhado com a loja).
  - A loja deve expor um endpoint `POST <storeDomain>/payments/events/` aceitando `Content-Type: application/json` e o cabeçalho `X-Payments-Signature` com o hexdigest HMAC-SHA256 do corpo.
- Fluxo:
  - No `checkout.session.completed` (ou `payment_intent.succeeded`), a API monta:
    ```
    {"orderId":"<metadata.orderId | client_reference_id>","status":"paid"}
    ```
  - Assina com HMAC (`secret = PAYMENTS_EVENTS_SECRET`) e envia:
    - URL: `<storeDomain>/payments/events/`
    - Cabeçalho: `X-Payments-Signature: <hmac_sha256_hex_do_corpo>`
  - Idempotência: se o `event_id` já foi processado (tabela `webhook_events`), não reenviamos.
- Exemplo de verificador HMAC (Loja, Python):
  ```
  import hmac, hashlib, json
  from flask import request, jsonify
  SECRET = "<PAYMENTS_EVENTS_SECRET>"
  @app.route('/payments/events/', methods=['POST'])
  def events():
      body = request.data
      sig = request.headers.get('X-Payments-Signature') or ''
      calc = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
      if not hmac.compare_digest(calc, sig):
          return jsonify({'error':'invalid_signature'}), 400
      data = json.loads(body.decode('utf-8'))
      if data.get('orderId') and data.get('status') == 'paid':
          # atualizar pedido para 'paid'
          ...
      return jsonify({'status':'ok'})
  ```

### Redirecionamento Pós-Pagamento (Guia para Lojas)
- Rotas na loja:
  - `GET /checkout/success?session_id=<id>`: página de confirmação que recebe `session_id`.
  - `GET /checkout/cancel`: página de cancelamento/retorno ao carrinho.
- Geração de URLs:
  - Use URLs absolutas e públicas (https).
  - Inclua `{{CHECKOUT_SESSION_ID}}` em `successUrl`:
    - `successUrl`: `https://loja.com/checkout/success?session_id={{CHECKOUT_SESSION_ID}}`
    - `cancelUrl`: `https://loja.com/checkout/cancel`
- Envio para a API:
  - `POST /api/v1/create-checkout-session` body:
    ```
    {
      "accountId": "acct_123",
      "priceId": "price_abc",
      "successUrl": "https://loja.com/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
      "cancelUrl": "https://loja.com/checkout/cancel"
    }
    ```
  - `POST /api/v1/subscribe-to-platform` body:
    ```
    {
      "accountId": "acct_123",
      "successUrl": "https://loja.com/assinatura/ok?session_id={{CHECKOUT_SESSION_ID}}",
      "cancelUrl": "https://loja.com/assinatura/cancel"
    }
    ```
- Fallback:
  - Se a loja não enviar `successUrl`/`cancelUrl`, usamos `storeDomain` (se cadastrado) ou a Home/Done da API.
- Exemplos de rotas na loja:
  - Node/Express:
    ```
    app.get('/checkout/success', (req, res) => {
      const sessionId = req.query.session_id;
      res.render('checkout-success', { sessionId });
    });
    app.get('/checkout/cancel', (req, res) => {
      res.render('checkout-cancel');
    });
    ```
  - Django:
    ```
    def checkout_success(request):
        session_id = request.GET.get('session_id')
        return render(request, 'orders/success.html', {'session_id': session_id})
    def checkout_cancel(request):
        return render(request, 'orders/cancel.html')
    ```

## Boas Práticas de Integração
- Sempre validar ownership (`accountId`) do lado do cliente antes de chamar rotas.
- Tratar `401` e acionar refresh de token automaticamente quando possível.
- Persistir IDs relevantes (`priceId`, `session_id`) para reconciliação via webhooks.
- Implementar retry/backoff para rate limits.
- Registrar `event_id` de webhooks e garantir idempotência lado servidor/cliente.

## Variáveis de Ambiente Essenciais
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `PLATFORM_PRICE_ID`, `DOMAIN`.
- `JWT_SECRET`, `JWT_ACCESS_TTL_SECONDS`, `JWT_REFRESH_TTL_SECONDS`.
- Rate Limits: `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_LOGIN`, `RATE_LIMIT_CHECKOUT`, `RATE_LIMIT_WEBHOOK`.
 - Docs públicas: `DOCS_PUBLIC=1` para acesso sem autenticação; `0` para exigir token.
 - Liberação de lojas:
   - `PAYMENTS_EVENTS_SECRET` (HMAC)
   - `PAYMENTS_EVENTS_PATH` (padrão `/payments/events/`)
  - `PAYMENTS_EVENTS_HEADER` (padrão `X-Payments-Signature`)

## 🔄 Recuperação Automática de Webhooks Stripe
- A API executa periodicamente uma sincronização com a Stripe para recuperar eventos não recebidos via webhook.
- Esse processo:
  - Consulta a Stripe por eventos recentes (`checkout.session.completed`, `payment_intent.succeeded`) por conta conectada.
  - Reprocessa apenas eventos não persistidos localmente ou sem entrega à loja.
  - Reutiliza o mesmo fluxo de liberação pós-pagamento (normalização de status, correlação `orderId → accountId`, HMAC e idempotência).
  - Garante idempotência total pelo `event_id` e registro de tentativas no `store_dispatch`.
- Configuração:
  - `WEBHOOK_SYNC_ENABLED` (1/0), `WEBHOOK_SYNC_INTERVAL_MINUTES`, `WEBHOOK_SYNC_LOOKBACK_MINUTES`.
- Endpoints internos:
  - `POST /internal/sync/stripe-events` (apenas localhost) para disparo manual do sincronizador.

## Compatibilidade
- Todos os exemplos e formatos estão alinhados com os schemas e fluxos atuais da API.

## Admin e Ferramentas Locais (Somente localhost)
- Acesso restrito a `127.0.0.1` / `::1`. Úteis para desenvolvimento, inspeção e configuração.
- Endpoints:
  - `GET /config` — visão central com variáveis principais e auditoria visual (segredos mascarados).
  - `GET /config/audit` — auditoria de configurações em JSON com campos: `group`, `key`, `value/masked`, `required`, `ok`, `message`.
  - `GET /stores` — visão de lojas; edição inline de `storeDomain`, criação e exclusão.
  - `GET /stores/list` — lista lojas e usuários relacionados.
  - `GET /stores/get/<account_id>` — detalhes da loja (accountId, userId, email, storeDomain).
  - `GET /users` — visão de usuários.
- Observações:
  - Essas páginas não devem ser expostas publicamente.
  - `storeDomain` é usado como fallback para `successUrl`/`cancelUrl` e para liberação HMAC.
