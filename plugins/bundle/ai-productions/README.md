# AI Productions — Vitrine dos Agentes

Plugin que centraliza **tudo o que os agentes de IA produzem** —
posts, peças de marketing, landing pages, documentos, e-mails,
roteiros, anúncios — com **fluxo de aprovação humano** e **envio
automático de notificações** para o time.

> Pense neste plugin como um **Kanban de saídas dos agentes**: cada
> entrega vira um cartão, alguém revisa, aprova ou rejeita, e o time
> recebe uma notificação a cada passo.

---

## ✨ O que ele entrega

- **Catálogo** de produções (filtrável por time, tipo, status, agente, tag).
- **Aprovação humana**: rascunho → pendente → aprovado → publicado, com auditoria completa.
- **Notificações**: dispara um aviso para o time a cada evento importante (`approval_requested`, `approved`, `rejected`, `published`).
- **Ferramentas para agentes** prontas para serem chamadas dentro dos prompts:
  - `register_production`
  - `request_approval`
  - `send_team_notification`
- **API REST** completa em `/api/ai-productions/*` — fácil de plugar em qualquer dashboard ou Console.

---

## 🚀 Instalação

1. Coloque o pacote em `plugins/bundle/ai-productions/`.
2. Reinicie / recarregue a plataforma (ou clique em **Reload Plugins** no Console).
3. Confirme nos logs:
   ```
   AIProductionsPlugin.register() called
   [ai-productions] registering router at /api/ai-productions/productions
   [ai-productions] registering router at /api/ai-productions/notifications
   [ai-productions] registered tools: register_production, request_approval, send_team_notification
   ```

Pronto. Nenhuma variável de ambiente obrigatória.

---

## 🧱 Tipos de produção suportados

`post`, `landing_page`, `document`, `email`, `ad_creative`, `image`,
`video`, `script`, `blog_article`, `social_caption`, `press_release`,
`newsletter`, `report`, `spreadsheet`, `code_snippet`, `other`.

Liste com:
```bash
curl http://localhost:8000/api/ai-productions/productions/_types
```

---

## 🔁 Ciclo de vida de uma produção

```
draft ──► pending_approval ──► approved ──► published
   │                │                          │
   │                └── rejected ──► (volta para pending)
   ▼
archived  ◄────── pode vir de qualquer estado
```

Transições inválidas retornam HTTP **409** e nada é alterado.

---

## 🛠️ Ferramentas para agentes

### `register_production`
```python
await register_production(
    title="Post de lançamento - Linha Verão 2026",
    type="post",
    team="marketing",
    agent_id="jotaduo-vendas",
    agent_name="Jotaduo Vendas",
    summary="Anúncio do drop de verão com CTA para Pix.",
    content="🌞 A nova coleção chegou...",
    tags=["instagram", "drop-verao"],
    requires_approval=True,
    auto_request_approval=True,
)
```
Retorna `{ok, production, notification}`. Se `auto_request_approval=True`
(padrão), a produção já entra em `pending_approval` e o time recebe a
notificação `production.approval_requested`.

### `request_approval`
```python
await request_approval(
    production_id="prod-abc123",
    actor="jotaduo-orchestrator",
    note="Cliente quer publicar amanhã às 9h.",
)
```

### `send_team_notification`
```python
await send_team_notification(
    team="marketing",
    title="Reunião editorial agendada",
    body="Quarta 15h. Pauta: drop de verão.",
    level="info",
)
```

---

## 🌐 API REST

Todas montadas em `/api/ai-productions/`.

### Produções

| Método | Rota | Descrição |
|---|---|---|
| `GET`    | `/productions` | Lista (query: `team`, `type`, `status`, `agent_id`, `tag`, `limit`) |
| `POST`   | `/productions` | Cria uma produção |
| `GET`    | `/productions/_types` | Tipos e statuses suportados |
| `GET`    | `/productions/_stats` | Contadores por status/time/tipo |
| `GET`    | `/productions/{id}` | Detalhe + histórico de auditoria |
| `PATCH`  | `/productions/{id}` | Edita campos (gera audit) |
| `POST`   | `/productions/{id}/request-approval` | Move para `pending_approval` |
| `POST`   | `/productions/{id}/approve` | Move para `approved` |
| `POST`   | `/productions/{id}/reject` | Move para `rejected` (exige `reason`) |
| `POST`   | `/productions/{id}/publish` | Move para `published` |
| `POST`   | `/productions/{id}/archive` | Arquiva |
| `DELETE` | `/productions/{id}` | Remove |
| `DELETE` | `/productions` | Limpa tudo (admin/test) |

### Notificações

| Método | Rota | Descrição |
|---|---|---|
| `GET`    | `/notifications` | Lista (query: `team`, `unread_only`, `kind`, `production_id`, `limit`) |
| `POST`   | `/notifications` | Envia nova notificação |
| `GET`    | `/notifications/_unread` | Contador de não lidas |
| `POST`   | `/notifications/_read_all` | Marca todas como lidas (opc: `?team=...`) |
| `POST`   | `/notifications/{id}/read` | Marca uma como lida |
| `DELETE` | `/notifications/{id}` | Remove |
| `DELETE` | `/notifications` | Limpa tudo (admin/test) |

---

## 🧪 Exemplo end-to-end

```bash
# 1) Agente cria a peça (pelo HTTP ou via tool)
curl -X POST http://localhost:8000/api/ai-productions/productions \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Landing - Black Friday",
    "type": "landing_page",
    "team": "marketing",
    "agent_id": "jotaduo-orchestrator",
    "agent_name": "Jotaduo Orchestrator",
    "summary": "Hero + 3 CTAs + Pix",
    "content_url": "https://figma.com/file/xyz",
    "tags": ["bf", "lp"]
  }'

# 2) Humano lista pendentes
curl "http://localhost:8000/api/ai-productions/productions?status=pending_approval"

# 3) Humano aprova
curl -X POST http://localhost:8000/api/ai-productions/productions/prod-xxx/approve \
  -H 'Content-Type: application/json' \
  -d '{"actor":"ruth","note":"Pode publicar"}'

# 4) Notificações geradas
curl "http://localhost:8000/api/ai-productions/notifications?team=marketing"
```

---

## 🗄️ Armazenamento

A v1 usa stores em memória (`ProductionStore`, `NotificationStore`) com
retenção FIFO (2000 produções, 1000 notificações). Para produção, troque
por Postgres mantendo a mesma interface — os routers não dependem do
backend.

---

## 🧹 Desinstalação

O plugin patcheia `PluginLoader.unload_plugin` para limpar os stores
quando você desinstala. Nenhum efeito colateral fica no sistema.
