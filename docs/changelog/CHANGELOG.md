# Changelog

## 2025-12-20

- Auditabilidade de Webhooks
  - Log estruturado no console para todos os eventos (inclui assinatura inválida)
  - Persistência completa em `webhook_logs` (event_id, event_type, payload, received_at)
  - Idempotência mantida para `checkout.session.completed` em `webhook_events`

- Status de Sessão de Checkout
  - Endpoint `GET /api/v1/checkout-session/{session_id}` autenticado
  - Retorna `status`, `payment_status`, `mode`, `amount_total`, `currency`
  - Suporta conta conectada via `g.stripe_account_id` ou `accountId` query param

- Documentação e Home
  - Home técnica estilo Hero ASCII One em `/` (landing institucional)
  - Ambiente exibido dinamicamente (SANDBOX/PRODUCTION) e versão `v1.0.0`
  - CTAs: Documentação (`/docs`), Health (`/health`), Status (`/status`)
  - Animação leve em canvas com estética sci-fi/terminal
  - Docs interativas movidas para `/docs`
  - Efeitos UI/UX adicionais:
    - Glitch controlado no título
    - Indicador de latência com ping real a `/health`
    - Minimap técnico decorativo no footer
    - `API_VERSION` configurável via `.env`
  - Ajustes de layout:
    - Hero reduzida para exibir footer fixo
    - Card com margem maior e padding ampliado
    - Grid de fundo significativamente menos densa (hero/header/minimap)
  - Performance e túnel:
    - Ping reduzido para ~10s com jitter
    - Header `ngrok-skip-browser-warning: true` nas requisições do front

- Rota `/done` para pós-checkout com exibição de `session_id`

- Configuração de Domínio
  - `.env` atualizado: `DOMAIN=http://localhost:4242`

- Testes
  - Separação entre unitários e temporários
    - `tests/unit/`: `test_auth.py`, `test_checkout.py` (marcados com `@pytest.mark.unit`)
    - `tests/temp/`: `test_webhook.py`, `test_audit.py` (marcados com `@pytest.mark.temp`)
    - `pytest.ini` com `testpaths` e `markers`
  - Cobertura e novos testes:
    - `pytest-cov` configurado em `pytest.ini` com relatórios `html`
    - Front-end: `test_front.py` cobrindo Home, Docs, Health/Status e assets
    - Rotas servidor: `test_server_routes.py` cobrindo 303s/403s/404s e webhook multi-eventos
    - Stripe Service: `test_stripe_service.py` com mocks da SDK (100% no módulo)
    - Config: `test_config.py` cobrindo URLs de banco e defaults (100% no módulo)
    - Resultado geral: `TOTAL 92%` e `server.py 88%`

- Operação e Rate Limit
  - `/health` e `/status` isentos de rate limit
  - Aviso de storage in-memory do rate limiter documentado para ambiente de desenvolvimento

- Documentação técnica
  - Webhook multi-loja: endpoint único com roteamento por `event.account` e alternativa por conta
  - Liberação pós-checkout: seção com exemplos de `metadata`/`client_reference_id` e pseudo-fluxo
  - Criação de webhook via API (Python/Node) para contas conectadas
