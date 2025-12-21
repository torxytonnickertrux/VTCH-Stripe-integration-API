# Backend SaaS / Marketplace (Flask + Stripe)

Este projeto implementa uma API robusta para um SaaS financeiro, utilizando Flask e Stripe Connect. A arquitetura foca em segurança, escalabilidade e manutenibilidade, seguindo boas práticas de engenharia de software.

## 🚀 Funcionalidades

- **Autenticação e Segurança**: JWT (Access/Refresh), bcrypt para senhas, validação de ownership (usuário só acessa seus dados).
- **Integração Stripe**: Checkout, Portal do Cliente, Assinaturas, Connect (contas vinculadas).
- **Validação**: Pydantic para schemas rigorosos de entrada.
- **Observabilidade**: Logs estruturados (JSON) e Rate Limiting configurável.
- **Persistência**: Suporte híbrido a MySQL (Produção) e SQLite (Dev).

## 📂 Estrutura do Projeto

```
integracao_srtipe/
├── core/
│   ├── auth.py          # Lógica de autenticação JWT
│   ├── config.py        # Configurações e variáveis de ambiente
│   ├── db.py            # Modelos SQLAlchemy e sessão
│   ├── logging.py       # Configuração de logs estruturados
│   ├── rate_limit.py    # Configuração do Flask-Limiter
│   ├── schemas.py       # Schemas Pydantic para validação
│   └── stripe_service.py # Lógica centralizada do Stripe
├── docs/
│   ├── API.md           # Documentação dos endpoints
│   └── README.md        # Este arquivo
├── tests/               # Testes automatizados (pytest)
├── server.py            # Entrypoint da aplicação
└── requirements.txt     # Dependências
```

## 🛠️ Configuração e Instalação

### 1. Pré-requisitos
- Python 3.8+
- MySQL (opcional, para produção)

### 2. Instalação
```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente (Windows)
.\.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Variáveis de Ambiente (.env)
Crie um arquivo `.env` na raiz com base nas chaves abaixo:

```ini
# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
PLATFORM_PRICE_ID=price_...
DOMAIN=http://localhost:4242

# Segurança
JWT_SECRET=sua_chave_secreta_jwt
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=604800

# Rate Limit
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_LOGIN=10/minute
RATE_LIMIT_CHECKOUT=30/minute

# Banco de Dados (Escolha um modo)

# MODO 1: SQLite (Padrão para Dev)
# Não é necessário configurar nada extra, usará sqlite:///app.db

# MODO 2: MySQL (Produção)
DB_DIALECT=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=nome_do_banco
MYSQL_USER=usuario
MYSQL_PASSWORD=senha
```

## ▶️ Execução
 
 ### Rodar o Servidor (Desenvolvimento)
 ```bash
 python server.py
 ```
 O servidor iniciará em `http://localhost:4242`.
 
 ### Rodar o Servidor (Produção)
 **Nunca** utilize `python server.py` em produção. Utilize um servidor WSGI robusto.
 
 #### Opção 1: Windows (Waitress)
 ```bash
 # Instalar waitress (se ainda não instalou)
 pip install waitress
 
 # Rodar via script
 .\start_prod.bat
 
 # Ou rodar manualmente
 waitress-serve --port=4242 --call wsgi:app
 ```
 
 #### Opção 2: Linux/Docker (Gunicorn)
 ```bash
 # Instalar gunicorn
 pip install gunicorn
 
 # Rodar com config
 gunicorn -c gunicorn_config.py wsgi:app
 ```

### Rodar Testes
```bash
pytest
```

## 📚 Documentação da API
Consulte [docs/API.md](API.md) para detalhes completos sobre os endpoints, formatos de request/response e códigos de erro.

## � Modelo de Negócio (SaaS + Marketplace)

- A plataforma opera como um intermediador de pagamentos (Marketplace) sobre Stripe Connect: compradores pagam por produtos/serviços ofertados em contas conectadas dos vendedores, enquanto a plataforma orquestra o fluxo, valida ownership e aplica regras de cobrança.
- Cada usuário autenticado pode criar e gerenciar sua própria conta Stripe Connect pela API v1 (`POST /api/v1/create-connect-account`, `POST /api/v1/create-account-link`, `GET /api/v1/account-status/<account_id>`). O isolamento é multi-tenant: cada usuário só acessa recursos da sua conta.
- Os pagamentos são processados diretamente nas contas conectadas: o Checkout é criado na conta do vendedor, e o `mode` (one-time ou subscription) é derivado automaticamente do `Price.type` do Stripe.
- A plataforma não é apenas um gateway; ela entrega um SaaS financeiro multi-tenant com autenticação (JWT), validação de ownership, rate limiting e observabilidade, além de endpoints de produto, checkout e portal.

### Formas de monetização
- Assinatura da plataforma: `POST /api/v1/subscribe-to-platform` utiliza `PLATFORM_PRICE_ID` para criar uma sessão de checkout de assinatura (recorrente) na conta da própria plataforma.
- Taxas por transação: a plataforma pode cobrar uma taxa por operação via `application_fee_amount`.
  - Pagamentos avulsos (one-time): taxa aplicada em `payment_intent_data.application_fee_amount`.
  - Assinaturas (recorrentes): taxa aplicada em `subscription_data.application_fee_amount`.
  - Observação: o valor da taxa é definido no backend conforme regras de negócio atuais da API v1.
- Modelo híbrido: é possível combinar assinatura de uso da plataforma + taxa por transação.

### Tipos de cobrança suportados
- Pagamentos avulsos (one-time): crie produtos sem `recurringInterval` via `POST /api/v1/create-product` e utilize `POST /api/v1/create-checkout-session` para abrir o checkout na conta conectada.
- Pagamentos recorrentes (assinaturas): crie preços com `recurringInterval` (`month`/`year`) e a sessão de checkout será gerada com `mode=subscription` conforme o `Price.type`.

### Fluxo de dinheiro
- Comprador → paga via Checkout na conta conectada do vendedor.
- Plataforma → recebe sua parcela quando configurada, via `application_fee_amount` na criação da sessão de checkout.
- Assinatura da plataforma → cobrada na conta da plataforma usando `PLATFORM_PRICE_ID`.

### Compatibilidade e aderência
- Compatível com Stripe Connect e com os endpoints disponíveis na API v1 descritos em `docs/API.md`.
- Webhooks em `/webhook` tratam eventos de Checkout/Assinatura com idempotência básica e validação de assinatura.
- Este documento reflete o comportamento atual da API; não promete funcionalidades além das implementadas (ex.: configuração dinâmica de taxas pelo cliente não está exposta na API v1).

## �🛡️ Decisões Arquiteturais
1.  **Camadas**: Separação clara entre Rotas (server.py), Regras (core/), e Dados (core/db.py).
2.  **Logs**: Uso de `structlog` para logs JSON, facilitando ingestão por ferramentas como Datadog/ELK.
3.  **Banco de Dados**: Abstração via SQLAlchemy permite troca transparente entre SQLite (dev) e MySQL (prod).

## 🔮 Próximos Passos
- Implementar migrações de banco de dados com Alembic.
- Configurar Redis como backend para o Rate Limiter.
- Adicionar pipeline de CI/CD.
