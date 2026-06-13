---
name: agent_forge
description: |
  Use o AgentForge sempre que o usuário pedir para criar um novo
  agente, time de agentes, skill ou plugin para o QwenPaw / Nexora.
  Ele segue as convenções do repositório (pacote, frontmatter de
  skill, manifest de plugin) e gera os arquivos prontos.
when_to_use: |
  - "Crie um agente que faça X" → scaffold_agent
  - "Monte um time para Y" → scaffold_team
  - "Quero uma skill que dispare quando Z" → scaffold_skill
  - "Faz um plugin de cobrança/CRM/etc" → scaffold_plugin
  - "O que já existe?" / "Quais agentes temos?" → inspect_repo

  NÃO use o AgentForge para editar agentes existentes em produção
  sem antes inspecionar — ele cria; quem decide se sobrescreve é
  o usuário (``dry_run=False`` por ordem explícita).
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "🔨"
    requires: {}
---

# Habilidade: AgentForge — Construtor de agentes/times/skills/plugins

## Fluxo padrão

1. **Inspeção** — chame `inspect_repo(area="all")` para mapear o
   que já existe. Não duplique nomes.
2. **Plano** — chame a tool de scaffold escolhida com `dry_run=True`
   (default). Mostre ao usuário:
   - quais arquivos serão criados,
   - quantos bytes cada um,
   - sob qual pasta.
3. **Aprovação** — espere o "pode escrever".
4. **Escrita** — repita a mesma chamada com `dry_run=False`.
5. **Próximos passos** — sugira testes em `tests/unit/<area>/...`
   e, se for plugin, recomende um restart do backend.

## Tools disponíveis

| Tool | Cria | Pasta padrão |
|---|---|---|
| `inspect_repo(area)` | (leitura) | — |
| `scaffold_skill(name, description, when_to_use, emoji, body_markdown)` | 1 SKILL.md | `src/qwenpaw/agents/skills/<kebab>/` |
| `scaffold_agent(name, role, description, system_prompt)` | 1 módulo Python | `src/qwenpaw/agents/<snake>_agent.py` |
| `scaffold_team(name, roles, default_prompt_prefix)` | pacote 5 arquivos | `src/qwenpaw/agents/<snake>/` |
| `scaffold_plugin(name, description, author)` | bundle 7 arquivos | `plugins/bundle/<kebab>/` |

## Regras invioláveis

- Sempre `dry_run=True` na primeira chamada.
- Nunca grave fora dos roots permitidos (o `safe_join` já bloqueia).
- Slug é sempre derivado do `name` — não aceite slug manual.
- Persona em pt-BR; se o usuário falar inglês, traduza o prompt.
- Se o pedido for "adicionar um papel ao time X", **estenda**
  `prompts.py` e `factory.py` do time existente em vez de criar
  um time novo.

## Exemplos

```text
Usuário: "Crie um agente de reembolso para e-commerce"
Forge:
  1. inspect_repo(area="agents")  → confirma que não existe
  2. scaffold_agent(
       name="Reembolso",
       role="reembolso",
       description="Trata pedidos de reembolso CDC art. 49",
       system_prompt="Você é o especialista em reembolso...",
       dry_run=True,
     )
  3. mostra plano (1 arquivo, ~2 KB)
  4. aguarda OK
  5. scaffold_agent(... mesmos args ..., dry_run=False)
```

```text
Usuário: "Faz um plugin de notificação Telegram"
Forge:
  1. inspect_repo(area="plugins")
  2. scaffold_plugin(
       name="Telegram Notify",
       description="Envia notificações para canais Telegram",
       dry_run=True,
     )
  3. plano (7 arquivos)
  4. usuário aprova
  5. scaffold_plugin(... dry_run=False)
  6. sugere: "preencha _on_startup com a inscrição de
     register_extra_tools e escreva tests/unit/plugins/telegram_notify/"
```
