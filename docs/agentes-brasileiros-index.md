# Jotaduo · Agentes Brasileiros — Índice

> Ponto único de entrada para toda a stack de agentes BR do JotaDuo /
> Jotaduo. Cada link aponta para a documentação completa do componente.

## 🧭 Mapa rápido

| Camada | Pacote / pasta | Quem é? | Doc |
|---|---|---|---|
| **Time de agentes BR** | `src/jotaduo/agents/br_team/` | 8 sub-agentes especializados (atendente, vendas, suporte, financeiro, agendamento, marketing, catálogo, recepcionista de saúde) + `JotaduoOrchestrator` | [br-team-guide.md](./br-team-guide.md) |
| **Toolkit BR** | `src/jotaduo/agents/br_team/tools/` | WhatsApp, Pix/PagSeguro, agenda, BrasilAPI (CNPJ/CEP) | [br-team-guide.md#toolkit](./br-team-guide.md) |
| **Plugin instalável** | `plugins/bundle/jotaduo-team/` | Bundle JotaDuo com 5 agentes BR + tool `convene_meeting` + API HTTP | [plugins/bundle/jotaduo-team/README.md](../plugins/bundle/jotaduo-team/README.md) |
| **Meta-agente** | `src/jotaduo/agents/forge/` | `AgentForge` cria novos agentes/times/skills/plugins via scaffolding | [agent-forge.md](./agent-forge.md) |
| **Skills (pt-BR)** | `src/jotaduo/agents/skills/br_*-pt/` + `agent_forge-pt/` | 10 SKILL.md (9 BR + AgentForge) | [br-team-guide.md#skills](./br-team-guide.md) |

## 📦 O que está em produção?

```
src/jotaduo/agents/
├── br_team/                       ← 8 agentes BR + orquestrador
│   ├── orchestrator.py
│   ├── factory.py
│   ├── prompts.py
│   ├── specialists/
│   └── tools/                     ← whatsapp/pix/agenda/brasilapi
├── forge/                         ← meta-agente AgentForge
│   ├── agent.py
│   ├── _paths.py                  ← path guard
│   ├── prompts.py
│   └── tools/                     ← 5 scaffolders
└── skills/
    ├── br_atendente-pt/SKILL.md
    ├── br_vendas-pt/SKILL.md
    ├── br_suporte-pt/SKILL.md
    ├── br_financeiro-pt/SKILL.md
    ├── br_agendamento-pt/SKILL.md
    ├── br_marketing-pt/SKILL.md
    ├── br_catalogo-pt/SKILL.md
    ├── br_recepcionista_saude-pt/SKILL.md
    ├── br_orchestrator-pt/SKILL.md
    └── agent_forge-pt/SKILL.md

plugins/bundle/jotaduo-team/        ← plugin JotaDuo instalável
├── plugin.json
├── plugin.py
├── routers_setup.py
├── routers/{health,agents,meet}.py
├── meeting_tool.py
└── README.md

tests/unit/
├── agents/br_team/                ← 69 testes
├── agents/forge/                  ← 19 testes
└── plugins/jotaduo_team/           ← 34 testes
```

## ✅ Status & qualidade

| Métrica | Valor |
|---|---|
| Testes BR team | 69 / 69 ✅ |
| Testes plugin jotaduo-team | 34 / 34 ✅ |
| Testes AgentForge | 19 / 19 ✅ |
| Regressão em testes pré-existentes (jotaduo) | 0 |
| flake8 (br_team, forge, jotaduo-team) | limpo |
| Skills cadastradas | 10 (9 BR + 1 Forge) |
| Agentes especialistas | 8 BR + 1 meta = 9 |

## 🚀 Como usar (5 cenários)

### 1. Invocar um especialista BR via orquestrador
```python
from jotaduo.agents.br_team import JotaduoOrchestrator
orch = JotaduoOrchestrator()
await orch(Msg(name="user", role="user",
               content="Quero remarcar minha consulta de quinta"))
```

### 2. Instanciar um especialista direto
```python
from jotaduo.agents.br_team import build_specialist
agente = build_specialist("vendas")
await agente(Msg(name="user", role="user",
                 content="Tem desconto à vista no Pix?"))
```

### 3. Plugin no JotaDuo (após restart do backend)
- Endpoints: `GET /api/jotaduo-team/health`, `GET /api/jotaduo-team/agents`, `POST /api/jotaduo-team/meet`
- Tool exposta: `convene_meeting` (assembleia de agentes em grupo)

### 4. Criar um novo agente via AgentForge
```python
from jotaduo.agents.forge import build_agent_forge
forge = build_agent_forge()
await forge(Msg(name="user", role="user",
                content="Crie um agente especializado em cobrança Pix recorrente"))
```
O AgentForge sempre faz `inspect_repo` → mostra plano `dry_run=True` → aguarda OK → escreve com `dry_run=False`.

### 5. Criar um plugin novo via AgentForge
```python
await forge(Msg(name="user", role="user",
                content="Faz um plugin Telegram Notify com router HTTP"))
```
Gera bundle completo em `plugins/bundle/<kebab>/` (7 arquivos).

## 🛡️ Garantias do AgentForge

- **Path guard** — 5 ALLOWED_ROOTS, qualquer outro path → `PathGuardError`
- **Dry-run padrão** — toda tool tem `dry_run: bool = True`
- **No-overwrite default** — arquivos existentes ficam como `skipped_exists`
- **Slug derivado** — não aceita slug manual (sempre via `slugify`/`kebab`)

## 📚 Leitura recomendada

1. Comece por **[br-team-guide.md](./br-team-guide.md)** para entender os 8 agentes e o toolkit.
2. Veja **[plugins/bundle/jotaduo-team/README.md](../plugins/bundle/jotaduo-team/README.md)** para o plugin instalável.
3. Termine em **[agent-forge.md](./agent-forge.md)** para criar novos componentes sem boilerplate.

---
**Commits relevantes** (em `main`):
- `ced02568` — feat(br_team): time de 8 agentes brasileiros + toolkit BR
- `625860fb` — feat(plugin): jotaduo-team plugin com 5 agentes BR + meeting tool
- `462ad2eb` — feat(forge): AgentForge meta-agente para scaffold de agentes/times/skills/plugins
