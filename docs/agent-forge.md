# AgentForge — meta-agente scaffolder

> **Pacote:** `jotaduo.agents.forge`
> **Skill:** `agent_forge-pt`
> **Status:** estável (v1.0, 19 testes verdes, flake8 limpo)

AgentForge é um agente ReAct que **cria outros agentes, times, skills
e plugins** seguindo as convenções deste monorepo. Foi projetado para
ser invocado a partir do JotaDuo quando o usuário pede algo como:

- _"Crie um agente que faça reembolso para e-commerce"_
- _"Monte um time para clínica veterinária"_
- _"Faz um plugin que integra com Telegram"_
- _"Quero uma skill que dispare quando o cliente reclama"_

## Arquitetura

```
src/jotaduo/agents/
├── forge/
│   ├── __init__.py        # lazy load público
│   ├── _paths.py          # safe_join, ALLOWED_ROOTS, slugify, write_files
│   ├── prompts.py         # AGENT_FORGE_PROMPT (pt-BR)
│   ├── agent.py           # AgentForge(ReActAgent) + build_agent_forge()
│   └── tools/
│       ├── __init__.py    # FORGE_TOOLS = [...]
│       ├── inspect_repo.py
│       ├── scaffold_skill.py
│       ├── scaffold_agent.py
│       ├── scaffold_team.py
│       └── scaffold_plugin.py
└── skills/agent_forge-pt/
    └── SKILL.md
```

## Garantias de segurança

1. **Path guard.** Toda escrita passa por `safe_join(rel_path)`. Os
   únicos roots permitidos são:
   - `src/jotaduo/agents/`
   - `src/jotaduo/agents/skills/`
   - `plugins/bundle/`
   - `tests/unit/agents/`
   - `tests/unit/plugins/`

   Qualquer tentativa de escapar (`..`, path absoluto, outro diretório)
   levanta `PathGuardError`.

2. **Dry-run por padrão.** Todas as tools aceitam `dry_run: bool = True`.
   No primeiro chamado, o AgentForge devolve apenas o **plano** (lista
   de arquivos + bytes). Só grava quando explicitamente recebe
   `dry_run=False`.

3. **No-overwrite por default.** `write_files(plan, overwrite=False)`
   pula arquivos que já existem (marcando-os como `skipped_exists`).

## Ferramentas

### `inspect_repo(area="all")`
Lista skills, agentes, plugins e times já existentes. **Read-only.**
Sempre chame antes de scaffoldar.

### `scaffold_skill(name, description, when_to_use, emoji, body_markdown)`
Gera 1 arquivo: `src/jotaduo/agents/skills/<kebab>/SKILL.md` com
frontmatter YAML completo.

### `scaffold_agent(name, role, description, system_prompt, max_iters=12)`
Gera 1 arquivo: `src/jotaduo/agents/<snake>_agent.py` com classe
`<Camel>Agent(ReActAgent)` + factory `build_<snake>()`.

### `scaffold_team(name, roles, default_prompt_prefix)`
Gera 5 arquivos formando um pacote-time inspirado em `br_team`:
`__init__.py`, `prompts.py`, `factory.py`, `specialists/__init__.py`,
`specialists/base.py`.

### `scaffold_plugin(name, description, author, min_version="1.1.7")`
Gera 7 arquivos compondo um bundle plugin no padrão CloudPaw /
jotaduo-team: `plugin.json`, `__init__.py`, `plugin.py`,
`routers_setup.py`, `routers/__init__.py`, `routers/health.py`,
`README.md`.

## Uso programático

```python
from jotaduo.agents.forge import build_agent_forge

forge = build_agent_forge()
resposta = await forge(Msg(name="user", role="user",
                          content="Crie um agente de cobrança Pix"))
```

Ou diretamente sem o loop ReAct:

```python
import asyncio
from jotaduo.agents.forge import FORGE_TOOLS

scaffold_plugin = next(t for t in FORGE_TOOLS
                       if t.__name__ == "scaffold_plugin")
plan = asyncio.run(scaffold_plugin(
    name="Pix Receiver",
    description="Recebe webhooks Pix e cria cobranças",
    dry_run=True,
))
print(plan)
```

## Fluxo recomendado para o LLM

1. `inspect_repo(area="all")` para evitar colisão de nomes.
2. Chamar a tool de scaffold com `dry_run=True`.
3. Mostrar ao usuário o plano (arquivos + bytes).
4. Aguardar aprovação.
5. Repetir com `dry_run=False`.
6. Sugerir próximos passos:
   - Para plugin: reiniciar backend.
   - Para agente/time: rodar pytest do path equivalente.
   - Para skill: nenhuma ação extra (carregada na próxima boot).

## Testes

```bash
pytest tests/unit/agents/forge/ -q
flake8 src/jotaduo/agents/forge/ tests/unit/agents/forge/
```

19 testes cobrindo:
- `test_paths.py` — slugify, kebab, safe_join (allow/deny)
- `test_scaffolders.py` — 5 tools em dry-run
- `test_agent_smoke.py` — import + FORGE_TOOLS íntegro

## Limites conhecidos

- O `scaffold_team` não gera tests automaticamente — o usuário deve
  criar `tests/unit/agents/<team>/` manualmente.
- `scaffold_plugin` cria um plugin com apenas `/health`. Routers
  reais, agentes pré-cadastrados, e migrations precisam ser
  acrescentados manualmente após o scaffold.
- Não há reverter automatizado. Para desfazer, use git.
