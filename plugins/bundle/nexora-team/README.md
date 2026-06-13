# Nexora Team — Plugin QwenPaw

> **ID:** `nexora-team` · **Versão:** 1.0.0 · **Idioma:** pt-BR
> **Status:** ✅ instalável, com 34 testes verdes.

Plugin que materializa o time de atendentes brasileiros
([`qwenpaw.agents.br_team`](../../../src/qwenpaw/agents/br_team/)) no
QwenPaw — registra 5 agentes pt-BR prontos para WhatsApp/Pix/Agenda,
adiciona a ferramenta `convene_meeting` para reuniões multi-agente e
expõe uma API HTTP em `/api/nexora-team/*`.

## O que ele instala

| Componente | Descrição |
|---|---|
| **5 agentes** | `nexora-orchestrator`, `nexora-atendente`, `nexora-agendamento`, `nexora-vendas`, `nexora-financeiro` |
| **Skill** | `nexora-meeting-pt` (orquestrador convoca reuniões) |
| **Tool** | `convene_meeting(topic, participants, context)` |
| **HTTP API** | `/api/nexora-team/team`, `/api/nexora-team/meeting` |
| **Env vars** | `WHATSAPP_PROVIDER`, `WHATSAPP_TOKEN`, `PIX_PROVIDER`, `PIX_TOKEN`, `BRASILAPI_BASE_URL` (placeholders no Console) |

## Como instalar

1. Coloque a pasta `nexora-team/` em `<qwenpaw>/plugins/bundle/`
   (já está, neste repo).
2. Reinicie o backend do QwenPaw — o hook `nexora_team_init` roda
   no startup:
   - copia o skill para o pool global;
   - registra os 5 agentes via `save_agent_config`;
   - publica `convene_meeting` no registry de tools;
   - cria placeholders das envs no Console.
3. Recarregue a página do Console — os 5 agentes aparecem em
   "Agents", o orquestrador já vem com `convene_meeting` enabled.
4. **Opcional**: preencha as envs (`WHATSAPP_TOKEN`, `PIX_TOKEN`).
   Os stubs já funcionam sem isso (modo demo).

## API HTTP

Prefixo: `/api/nexora-team`

### Time

```
GET  /team
GET  /team/build   ← preview de um TeamBlueprint (POST body)
```

### Reuniões

```
POST   /meeting                  → convoca, devolve transcript
GET    /meeting                  → lista (?limit=20&status=completed)
GET    /meeting/{id}             → recupera uma reunião
DELETE /meeting                  → limpa store (admin/test)
GET    /meeting/_/participants   → roster (helper para UI)
```

### Exemplo curl

```bash
curl -X POST http://localhost:8000/api/nexora-team/meeting \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Cliente quer migrar do plano anual para mensal",
    "participants": ["vendas", "financeiro", "agendamento"],
    "context": "Anual R$1200, mensal R$149, sessão hoje 18h"
  }'
```

Resposta (resumida):

```json
{
  "id": "mtg-7c2f1a3b9e44",
  "topic": "Cliente quer migrar do plano anual para mensal",
  "convener": "nexora-orchestrator",
  "participants": [
    "nexora-vendas", "nexora-financeiro", "nexora-agendamento"
  ],
  "status": "completed",
  "summary": "Reunião sobre: ...\n• vendas: ...\n• financeiro: ...",
  "contributions": [
    {
      "agent_id": "nexora-vendas",
      "role": "vendas",
      "content": "Política permite downgrade após 7 dias...",
      "elapsed_ms": 812,
      "error": null
    }
  ]
}
```

## A ferramenta `convene_meeting`

Disponível para o orquestrador como tool nativa. Faz **N
`chat_with_agent` em paralelo**, captura timeouts e exceções por
agente, e sintetiza um sumário. Útil quando o caso toca 2+
departamentos e um hand-off sequencial perderia contexto.

Em ambiente de teste (sem `MultiAgentManager` ativo), o tool detecta
ausência do import e usa um stub determinístico — testes rodam
offline em < 2s.

## Arquitetura

```
plugins/bundle/nexora-team/
├── plugin.json          ← manifest (id, entry, deps, meta)
├── plugin.py            ← NexoraTeamPlugin (register/_on_startup/_on_shutdown)
├── constants.py         ← AGENT_SPECS, ALL_AGENT_IDS, AGENT_ROLE_MAP
├── agents_setup.py      ← ensure_builtin_agents / uninstall_agents
├── routers_setup.py     ← build_plugin_routers()
├── routers/
│   ├── team.py          ← GET /team, POST /team/build
│   └── meeting.py       ← POST/GET/DELETE /meeting
├── tools/
│   └── meeting_tools.py ← convene_meeting (paraleliza chat_with_agent)
├── store/
│   └── meetings.py      ← MeetingStore in-memory (thread-safe, evict 200)
├── skills/
│   └── nexora-meeting-pt/SKILL.md
└── README.md
```

### Decisões-chave

1. **Zero duplicação.** O plugin importa
   `qwenpaw.agents.br_team.prompts` para popular a `PERSONA.md` de
   cada workspace de agente — o conteúdo dos prompts mora num só
   lugar.
2. **Hub-and-Spoke explícito.** Os 4 especialistas têm
   `chat_with_agent` **desabilitado** (`enabled: false`). Só o
   orquestrador encaminha. Isso evita loops e mantém o trace claro.
3. **Reunião é episódica.** Cada `convene_meeting` cria um
   `Meeting` com transcript próprio. A store é circular (200) — em
   produção, plugar Postgres mantendo a interface
   `MeetingStore.{create, add_contribution, finish, get, list}`.
4. **Uninstall limpa.** O patch do `PluginLoader.unload_plugin`
   remove perfis de agentes, workspaces e skill do pool.

## Testes

```powershell
python -m pytest tests/unit/plugins/nexora_team/ -q
# 34 passed in 0.7s
```

Cobertura por arquivo:

| Arquivo | Foco |
|---|---|
| `test_store.py` | CRUD, eviction, filtros, ISO timestamps |
| `test_meeting_tool.py` | Default participants, role alias, dedup, timeout, exception |
| `test_routers.py` | TestClient FastAPI — todos 8 endpoints |
| `test_constants_and_smoke.py` | Specs consistentes, manifest, skill MD |

## Troca de stubs por integrações reais

Os agentes usam o toolkit do `br_team`. Para apontar para os
provedores reais sem mexer no plugin:

| Stub | Substituir em | Provedor sugerido |
|---|---|---|
| WhatsApp | `src/qwenpaw/agents/br_team/tools/whatsapp_tools.py` | Z-API, Evolution, Twilio |
| Pix | `src/qwenpaw/agents/br_team/tools/pagamento_tools.py` | Gerencianet, Mercado Pago, Asaas |
| CNPJ/CEP | `src/qwenpaw/agents/br_team/tools/cnpj_cep_tools.py` | BrasilAPI (`https://brasilapi.com.br`) |
| Agenda | `src/qwenpaw/agents/br_team/tools/agenda_tools.py` | Google Calendar, Outlook, Doctoralia |

O plugin não precisa ser reinstalado — basta editar os módulos do
`br_team` e reiniciar.

## Compliance

- **LGPD art. 11** — `nexora-recepcionista_saude` (papel disponível
  via `br_team.factory` mas não registrado por padrão neste plugin)
  bloqueia discussão clínica.
- **CDC art. 49** — `nexora-suporte` (idem) cita 7 dias de
  arrependimento.
- **WhatsApp HSM** — separação dura `send_whatsapp_message` (24h) ×
  `send_whatsapp_template` (fora 24h).
- **Reunião** — `convene_meeting` aceita `context` mas o skill
  `nexora-meeting-pt` instrui a NUNCA enviar CPF/cartão nesse campo.

## Roadmap

- [ ] Frontend (Console card listando reuniões em tempo real)
- [ ] Persistência Postgres para `MeetingStore`
- [ ] Multi-tenant (cada empresa tem seu time isolado)
- [ ] CLI: `qwenpaw nexora-team meet --topic "..." --with vendas,financeiro`
- [ ] Auto-build a partir do `TeamBlueprint` do DiscoveryAgent
