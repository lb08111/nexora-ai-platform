# Discovery Agent (CopilotKit) — plugin

Wraps `jotaduo.discovery` with a CopilotKit-style surface so a React app
can render the discovery interview as **generative UI** (CoAgent shared
state + `useCoAgentStateRender`).

## Como funciona

```
React (CopilotKit)
  └─ <CopilotKit runtimeUrl="/api/discovery-copilotkit" agent="discovery">
       └─ useCoAgent<DiscoveryAgentState>("discovery")
            ├─ useCoAgentStateRender → CompanyProfileCard
            ├─ useCoAgentStateRender → OpenAreasList
            ├─ useCoAgentStateRender → IntegrationsList
            └─ useCoAgentStateRender → BlueprintPreview
                       ▲
                       │  state JSON
                       │
FastAPI router (this plugin)
  └─ /api/discovery-copilotkit/sessions          (POST: create)
  └─ /api/discovery-copilotkit/sessions/{id}/turn (POST: next turn)
  └─ /api/discovery-copilotkit/sessions/{id}      (GET: snapshot)
  └─ /api/discovery-copilotkit/components         (GET: manifest)
                       │
                       ▼
jotaduo.discovery.DiscoverySession   (Live or Scripted)
```

O Pydantic `DiscoveryAgentState` espelha o tipo TypeScript do mesmo nome,
então o componente CopilotKit recebe o mesmo shape JSON que o backend
publica a cada turno.

## Modo padrão (offline / scripted)

Sem variáveis de ambiente, o plugin usa `ScriptedDiscoverySession` — a
entrevista determinística de 3 perguntas usada nos testes. Útil para
demos, testes de UI e o eval offline.

## Modo live (LLM)

```bash
export JOTADUO_DISCOVERY_LIVE=1
```

No próximo startup do JotaDuo o plugin troca o factory para
`LiveDiscoverySession`, que dirige o agente real do `jotaduo.discovery`.

## Endpoints

| Método | Path                                                | Descrição                               |
| ------ | --------------------------------------------------- | --------------------------------------- |
| POST   | `/api/discovery-copilotkit/sessions`                | abre sessão + 1ª pergunta               |
| POST   | `/api/discovery-copilotkit/sessions/{id}/turn`      | envia resposta, retorna estado          |
| GET    | `/api/discovery-copilotkit/sessions/{id}`           | snapshot atual                          |
| GET    | `/api/discovery-copilotkit/sessions/{id}/blueprint` | blueprint final (409 se ainda em curso) |
| GET    | `/api/discovery-copilotkit/components`              | manifest de componentes                 |

## Testes

```bash
pytest tests/unit/plugins/discovery_copilotkit -q
```

Cobre o adapter (shape), o router (fluxo end-to-end com `TestClient`),
o manifest de componentes (cada entrada tem um `.tsx` que usa
`useCoAgentStateRender`), o entry do plugin (registro via mock
`PluginApi`), e o eval (thresholds).

## Eval

```bash
python plugins/bundle/discovery-copilotkit/eval_run.py
```

Roda a entrevista canned ponta a ponta pelo router e imprime um JSON com
métricas (turns, cobertura de componentes, completude do blueprint,
latência p50/p95) + lista de falhas vs `METRIC_THRESHOLDS`. Exit code 1
se algum threshold quebrar — pronto pra ser plugado em CI.
