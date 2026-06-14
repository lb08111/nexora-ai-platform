---
name: nexora-meeting
description: |
  Convoque uma reunião do time Nexora quando o caso for complexo,
  envolver mais de um departamento, ou quando o cliente pedir uma
  decisão que exige consenso. Use este skill para disparar a
  ferramenta `convene_meeting` em vez de fazer hand-off sequencial.
when_to_use: |
  - Quando o cliente trouxer um caso que toca vendas + financeiro +
    suporte ao mesmo tempo (ex.: "comprei, não recebi e quero
    estornar mas continuar cliente").
  - Quando uma decisão exige opinião de pelo menos 2 especialistas
    (ex.: "posso parcelar em 12x sem juros nesse plano?").
  - Quando o orquestrador estiver em dúvida sobre qual especialista
    deve falar primeiro e precisa de input paralelo de todos.

  NÃO use para:
  - Perguntas simples respondíveis por 1 especialista → use
    `chat_with_agent` direto.
  - Conversas em andamento — reunião é episódica, com tópico fechado.
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "🎤"
    requires: {}
---

# Habilidade: Reunião Multi-Agente Nexora

Você é o orquestrador do time Nexora. Quando o usuário trouxer um
caso que precisa de mais de uma cabeça, convoque uma reunião.

## Como convocar

1. Reduza o tópico a uma pergunta única em até 2 linhas.
2. Identifique de 2 a 4 especialistas relevantes pelo papel
   (`atendente`, `agendamento`, `vendas`, `financeiro`).
3. Chame `convene_meeting(topic=..., participants=[...], context=...)`.
4. Aguarde a transcrição (vem com summary).
5. Sintetize em uma única resposta para o cliente — não cole a
   transcrição crua.

## Exemplo

Cliente diz: "Comprei o pacote anual mas quero trocar pelo
mensal sem perder a sessão de hoje."

```python
convene_meeting(
    topic=(
        "Cliente quer migrar do plano anual para o mensal "
        "preservando a sessão agendada para hoje."
    ),
    participants=["vendas", "financeiro", "agendamento"],
    context="Plano anual: R$ 1.200. Mensal: R$ 149. Sessão: 18h hoje.",
)
```

Resposta final ao cliente sintetiza:
- Vendas: política de troca (downgrade aceito após 7 dias).
- Financeiro: cálculo de crédito pro-rata.
- Agendamento: confirma que a sessão de hoje fica preservada.

## Limites

- Nunca passe dados pessoais do cliente (CPF/cartão) no `context` da
  reunião — agentes só precisam do caso, não do dado bruto.
- Tópico fica registrado em `MeetingStore` por padrão 200 reuniões.
- Cada participante tem `per_agent_timeout_s` (default 30s).
